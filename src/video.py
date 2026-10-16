"""Vídeo: pauta em content/videos/<nome>.json, conferência do MP4 e legenda de cada rede.

O arquivo de vídeo fica no branch assets (videos/AAAA-MM-DD/<nome>.mp4): binário grande não entra no
histórico do código. O workflow Publicar (tema=video) busca o arquivo de lá; este módulo confere se ele
cabe nos limites de cada rede (antes de publicar em qualquer uma) e monta o manifesto que main.publish lê.

Pauta, content/videos/<nome>.json:
    titulo     título do vídeo (diário, primeira linha da legenda, título no LinkedIn e no Facebook)
    arquivo    caminho no branch assets, ex.: videos/2026-10-16/apresentacao-techdim.mp4
    legenda    texto principal; vai em todas as redes
    hashtags   hashtags do assunto (opcional; a marca entra sempre)
    ia         true quando o vídeo foi gerado por IA: liga a sinalização do Instagram e põe o aviso na legenda
    capa_ms    instante do quadro de capa do Reels, em milissegundos (opcional)
    motivo     por que este vídeo (diário)

Sem ffprobe: a conferência lê direto os "átomos" do MP4 (ordem, tamanho, duração, dimensões, codecs).

Uso:
    python src/video.py conferir arquivo.mp4 [--redes linkedin,facebook,instagram]
    python src/video.py arquivo <nome-da-pauta>        # imprime o caminho do vídeo no branch assets
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import struct
import sys
from dataclasses import asdict, dataclass

import config
import content
import validar_pauta
from pauta_reserva import TELEFONE

REDES_DE_VIDEO = ("linkedin", "facebook", "instagram")

# Limites de cada rede para vídeo de feed/Reels, conforme a documentação oficial (conferida em 16/10/2026):
#   Instagram: developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media
#   Facebook:  developers.facebook.com/docs/video-api/guides/reels-publishing
#   LinkedIn:  learn.microsoft.com/linkedin/marketing/community-management/shares/videos-api
LIMITES = {
    "instagram": {"min_s": 3, "max_s": 900, "max_bytes": 300 * 2**20},
    "facebook": {"min_s": 3, "max_s": 90, "max_bytes": 1000 * 2**20, "min_largura": 540, "min_altura": 960},
    "linkedin": {"min_s": 3, "max_s": 1800, "min_bytes": 75 * 1024, "max_bytes": 500 * 2**20},
}
PROPORCAO_VERTICAL = 9 / 16

AVISO_IA = {
    "linkedin": "Vídeo criado com inteligência artificial.",
    "facebook": "🤖 Vídeo criado com inteligência artificial.",
    "instagram": "🤖 Vídeo criado com inteligência artificial.",
}

ROOT = pathlib.Path(__file__).resolve().parent.parent
PASTA_PAUTAS = "videos"


class VideoInvalido(ValueError):
    """O vídeo ou a pauta não servem; nada é publicado."""


# ---------------------------------------------------------------- leitura do MP4


@dataclass
class InfoMP4:
    tamanho: int
    duracao: float
    largura: int
    altura: int
    faststart: bool      # moov antes do mdat: o Instagram exige
    edit_list: bool      # edts/elst em alguma trilha: o Instagram pede que não haja
    codec_video: str
    codec_audio: str

    @property
    def proporcao(self) -> float:
        return self.largura / self.altura if self.altura else 0.0


def _filhos(dados: bytes, ini: int = 0, fim: int | None = None):
    """(tipo, início do conteúdo, fim) de cada caixa entre ini e fim."""
    fim = len(dados) if fim is None else fim
    pos = ini
    while pos + 8 <= fim:
        tam, tipo = struct.unpack(">I4s", dados[pos:pos + 8])
        cab = 8
        if tam == 1:
            if pos + 16 > fim:
                return
            tam, cab = struct.unpack(">Q", dados[pos + 8:pos + 16])[0], 16
        elif tam == 0:
            tam = fim - pos
        if tam < cab or pos + tam > fim:
            return
        yield tipo, pos + cab, pos + tam
        pos += tam


def _caixa(dados: bytes, ini: int, fim: int, tipo: bytes):
    return next(((i, f) for t, i, f in _filhos(dados, ini, fim) if t == tipo), None)


def _trilha(dados: bytes, ini: int, fim: int) -> dict:
    """Dimensões, tipo (vide/soun), codec e se há lista de edição de uma trilha (trak)."""
    saida = {"largura": 0, "altura": 0, "tipo": "", "codec": "", "edit_list": False}
    for tipo, i, f in _filhos(dados, ini, fim):
        if tipo == b"edts" and _caixa(dados, i, f, b"elst"):
            saida["edit_list"] = True
        elif tipo == b"tkhd":
            versao = dados[i]
            cont = dados[i:f]
            larg, alt = struct.unpack(">II", cont[-8:])
            saida["largura"], saida["altura"] = larg >> 16, alt >> 16
            # matriz de rotação: celular em pé costuma gravar paisagem + giro de 90°
            matriz = i + (52 if versao == 1 else 40)
            if matriz + 8 <= f:
                a, b = struct.unpack(">ii", dados[matriz:matriz + 8])
                if a == 0 and abs(b) == 0x10000:
                    saida["largura"], saida["altura"] = saida["altura"], saida["largura"]
        elif tipo == b"mdia":
            hdlr = _caixa(dados, i, f, b"hdlr")
            if hdlr:
                saida["tipo"] = dados[hdlr[0] + 8:hdlr[0] + 12].decode("latin1")
            minf = _caixa(dados, i, f, b"minf")
            stbl = _caixa(dados, *minf, b"stbl") if minf else None
            stsd = _caixa(dados, *stbl, b"stsd") if stbl else None
            if stsd:
                saida["codec"] = dados[stsd[0] + 12:stsd[0] + 16].decode("latin1")
    return saida


def inspecionar(caminho: str | pathlib.Path) -> InfoMP4:
    """Lê o cabeçalho do MP4. Levanta VideoInvalido se não for um MP4 legível."""
    caminho = pathlib.Path(caminho)
    try:
        tamanho = caminho.stat().st_size
    except OSError as exc:
        raise VideoInvalido(f"não consegui abrir {caminho}: {exc}") from exc

    ordem: list[bytes] = []
    moov = b""
    with caminho.open("rb") as fh:
        pos = 0
        while pos + 8 <= tamanho:
            fh.seek(pos)
            cab = fh.read(16)
            tam, tipo = struct.unpack(">I4s", cab[:8])
            if not ordem and tipo != b"ftyp":
                raise VideoInvalido("não é um arquivo MP4 (falta o cabeçalho ftyp)")
            tcab = 8
            if tam == 1 and len(cab) == 16:
                tam, tcab = struct.unpack(">Q", cab[8:16])[0], 16
            elif tam == 0:
                tam = tamanho - pos
            if tam < tcab or pos + tam > tamanho:
                raise VideoInvalido("arquivo MP4 truncado ou corrompido")
            ordem.append(tipo)
            if tipo == b"moov":
                fh.seek(pos + tcab)
                moov = fh.read(tam - tcab)
            pos += tam

    if not moov:
        raise VideoInvalido("MP4 sem a caixa moov (arquivo incompleto)")

    duracao, trilhas = 0.0, []
    for tipo, i, f in _filhos(moov):
        if tipo == b"mvhd":
            if moov[i] == 1:
                escala, dur = struct.unpack(">IQ", moov[i + 20:i + 32])
            else:
                escala, dur = struct.unpack(">II", moov[i + 12:i + 20])
            duracao = dur / escala if escala else 0.0
        elif tipo == b"trak":
            trilhas.append(_trilha(moov, i, f))

    video = next((t for t in trilhas if t["tipo"] == "vide"), None)
    if not video:
        raise VideoInvalido("o arquivo não tem trilha de vídeo")
    audio = next((t for t in trilhas if t["tipo"] == "soun"), {"codec": ""})
    return InfoMP4(
        tamanho=tamanho,
        duracao=duracao,
        largura=video["largura"],
        altura=video["altura"],
        faststart=b"moov" in ordem and b"mdat" in ordem and ordem.index(b"moov") < ordem.index(b"mdat"),
        edit_list=any(t["edit_list"] for t in trilhas),
        codec_video=video["codec"],
        codec_audio=audio["codec"],
    )


# ---------------------------------------------------------------- limites por rede


def conferir(info: InfoMP4, redes: list[str] | tuple[str, ...] = REDES_DE_VIDEO) -> dict[str, list[str]]:
    """Problemas que impedem a publicação, por rede (lista vazia = pode publicar)."""
    problemas: dict[str, list[str]] = {}
    for rede in redes:
        lim = LIMITES.get(rede)
        if lim is None:
            problemas[rede] = [f"{rede} não recebe vídeo por este fluxo"]
            continue
        p: list[str] = []
        if info.duracao < lim["min_s"]:
            p.append(f"duração de {info.duracao:.1f} s: o mínimo é {lim['min_s']} s")
        if info.duracao > lim["max_s"]:
            p.append(f"duração de {info.duracao:.0f} s: o máximo é {lim['max_s']} s")
        if info.tamanho > lim["max_bytes"]:
            p.append(f"arquivo de {info.tamanho / 2**20:.0f} MB: o máximo é {lim['max_bytes'] // 2**20} MB")
        if info.tamanho < lim.get("min_bytes", 0):
            p.append("arquivo pequeno demais")
        if rede == "instagram":
            if not info.faststart:
                p.append("o moov precisa vir antes do mdat (refaça com -movflags +faststart)")
            if info.edit_list:
                p.append("o Instagram pede MP4 sem lista de edição (refaça com -use_editlist 0 -bf 0)")
            if info.codec_video not in ("avc1", "avc3", "hvc1", "hev1"):
                p.append(f"codec de vídeo {info.codec_video or '?'}: use H.264 ou HEVC")
            if not 0.01 <= info.proporcao <= 10:
                p.append("proporção fora do aceito (de 0,01:1 a 10:1)")
        if rede == "facebook":
            if abs(info.proporcao - PROPORCAO_VERTICAL) > 0.03:
                p.append(f"Reels do Facebook são 9:16; este vídeo é {info.largura}x{info.altura}")
            if info.largura < lim["min_largura"] or info.altura < lim["min_altura"]:
                p.append(f"mínimo de {lim['min_largura']}x{lim['min_altura']}; este vídeo é {info.largura}x{info.altura}")
        problemas[rede] = p
    return problemas


def avisos(info: InfoMP4) -> list[str]:
    """O que não impede publicar, mas vale saber."""
    out = []
    if abs(info.proporcao - PROPORCAO_VERTICAL) > 0.05:
        out.append(f"{info.largura}x{info.altura} não é 9:16: Reels e Stories cortam ou deixam faixas")
    if not info.codec_audio:
        out.append("vídeo sem áudio")
    return out


# ---------------------------------------------------------------- pauta e legendas

_NOME = re.compile(r"[a-z0-9][a-z0-9._-]{0,60}")
_ARQUIVO = re.compile(r"videos/[A-Za-z0-9._/-]{1,150}\.mp4")


def pasta_de_pautas(pasta: pathlib.Path | None = None) -> pathlib.Path:
    return (pasta or content.CONTENT_DIR) / PASTA_PAUTAS


def carregar_pauta(nome: str, pasta: pathlib.Path | None = None) -> dict:
    """content/videos/<nome>.json já validado. Levanta VideoInvalido com o motivo."""
    if not _NOME.fullmatch(nome or ""):
        raise VideoInvalido(
            "informe o nome do vídeo (content/videos/<nome>.json): minúsculas, números, ponto, hífen ou _"
        )
    caminho = pasta_de_pautas(pasta) / f"{nome}.json"
    try:
        pauta = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VideoInvalido(f"pauta de vídeo não encontrada: content/videos/{nome}.json") from exc
    except json.JSONDecodeError as exc:
        raise VideoInvalido(f"content/videos/{nome}.json não é um JSON válido: {exc}") from exc
    if not isinstance(pauta, dict):
        raise VideoInvalido("a pauta de vídeo precisa ser um objeto JSON")

    titulo, legenda = pauta.get("titulo"), pauta.get("legenda")
    arquivo = pauta.get("arquivo")
    if not isinstance(titulo, str) or not titulo.strip() or len(titulo) > 100:
        raise VideoInvalido("'titulo' é obrigatório (até 100 caracteres)")
    if not isinstance(legenda, str) or not legenda.strip():
        raise VideoInvalido("'legenda' é obrigatória")
    if not isinstance(arquivo, str) or not _ARQUIVO.fullmatch(arquivo) or ".." in arquivo:
        raise VideoInvalido("'arquivo' precisa ser um caminho videos/.../nome.mp4 do branch assets")
    hashtags = pauta.get("hashtags", [])
    if not isinstance(hashtags, list) or not all(isinstance(t, str) for t in hashtags):
        raise VideoInvalido("'hashtags' precisa ser uma lista de textos")
    capa = pauta.get("capa_ms")
    if capa is not None and (not isinstance(capa, int) or isinstance(capa, bool) or capa < 0):
        raise VideoInvalido("'capa_ms' precisa ser um número inteiro de milissegundos")

    # as mesmas regras do restante do projeto: sem o domínio fora do ar e sem telefone
    if validar_pauta.cita_dominio_fora_do_ar({"titulo": titulo, "legenda": legenda, "hashtags": hashtags}):
        raise VideoInvalido(f"a pauta cita {config.SITE_FORA_DO_AR}, que está fora do ar; use {config.SITE}")
    if TELEFONE.search(f"{titulo}\n{legenda}"):
        raise VideoInvalido("a legenda cita telefone; o único contato divulgado é o site")
    return {**pauta, "ia": bool(pauta.get("ia")), "titulo": titulo.strip(), "legenda": legenda.strip()}


def _post_de_apoio(pauta: dict) -> content.Post:
    """Post só para reaproveitar as regras de hashtag (forma, limite por rede e marca no fim)."""
    return content.Post(
        theme="video", titulo=pauta["titulo"], pontos=[], infografico={"hashtags": pauta.get("hashtags", [])}
    )


def legenda(pauta: dict, rede: str) -> str:
    """Legenda da rede: título, texto, aviso de IA (se houver), site e hashtags, dentro do limite dela."""
    tags = _post_de_apoio(pauta).hashtags(rede)
    aviso = AVISO_IA[rede] if pauta.get("ia") else ""
    partes = [pauta["titulo"], "", pauta["legenda"]]
    if aviso:
        partes += ["", aviso]
    if rede == "linkedin":
        partes += ["", f"TECHDIM — {config.TAGLINE}", config.SITE_URL]
    elif rede == "facebook":
        partes += ["", "Site no primeiro comentário 👇"]
    else:  # instagram: link só clicável no perfil
        partes += ["", f"🔗 Link na bio: {config.SITE}"]
    partes += ["", tags]
    texto = "\n".join(partes)
    limite = content.LIMITE_LEGENDA.get(rede, 2000)
    return texto if len(texto) <= limite else texto[: limite - 1].rstrip() + "…"


def comentario(rede: str) -> str:
    """Primeiro comentário: o site, no Facebook (no LinkedIn ele já está na legenda; no Instagram, na bio)."""
    if rede == "facebook":
        return f"🌐 TECHDIM — {config.TAGLINE}: {config.SITE_URL}"
    return ""


# ---------------------------------------------------------------- manifesto


def gerar(
    nome: str,
    redes: list[str],
    hoje: dt.date,
    out: pathlib.Path,
    pasta: pathlib.Path | None = None,
) -> dict:
    """Manifesto do vídeo para main.publish. O MP4 já precisa estar em out/<arquivo>."""
    pauta = carregar_pauta(nome, pasta)
    fora = [r for r in redes if r not in REDES_DE_VIDEO]
    if fora:
        raise VideoInvalido(f"vídeo não vai para: {', '.join(fora)} (redes de vídeo: {', '.join(REDES_DE_VIDEO)})")
    local = out / pauta["arquivo"]
    if not local.exists():
        raise VideoInvalido(f"vídeo não encontrado em {local}: o workflow busca no branch assets")
    info = inspecionar(local)
    if pauta.get("capa_ms") is not None and pauta["capa_ms"] > info.duracao * 1000:
        raise VideoInvalido("'capa_ms' passa da duração do vídeo")

    problemas = {r: p for r, p in conferir(info, redes).items() if p}
    if problemas:
        detalhe = "; ".join(f"{r}: {' / '.join(p)}" for r, p in problemas.items())
        raise VideoInvalido(f"o vídeo não serve para: {detalhe}")

    return {
        "theme": "video",
        "date": hoje.isoformat(),
        "titulo": pauta["titulo"],
        "curadoria": "vídeo da TECHDIM" + (" (gerado por IA, declarado na legenda)" if pauta["ia"] else ""),
        "motivo": pauta.get("motivo", ""),
        "fontes": [],
        "video": {
            "nome": nome,
            "arquivo": pauta["arquivo"],
            "titulo": pauta["titulo"],
            "ia": pauta["ia"],
            "capa_ms": pauta.get("capa_ms"),
            "avisos": avisos(info),
            **{k: v for k, v in asdict(info).items() if k in ("duracao", "tamanho", "largura", "altura")},
        },
        "networks": {
            r: {"caption": legenda(pauta, r), "comentario": comentario(r), "files": [pauta["arquivo"]]}
            for r in redes
        },
    }


# ---------------------------------------------------------------- linha de comando


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Conferência de vídeos da TECHDIM")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("conferir", help="mostra o que o MP4 tem e o que cada rede pensa dele")
    c.add_argument("arquivo")
    c.add_argument("--redes", default=",".join(REDES_DE_VIDEO))
    a = sub.add_parser("arquivo", help="caminho do vídeo (no branch assets) citado pela pauta")
    a.add_argument("nome")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "arquivo":
            print(carregar_pauta(args.nome)["arquivo"])
            return 0
        info = inspecionar(args.arquivo)
    except VideoInvalido as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    redes = [r.strip() for r in args.redes.split(",") if r.strip()]
    print(json.dumps(asdict(info), ensure_ascii=False, indent=2))
    ruins = {r: p for r, p in conferir(info, redes).items() if p}
    for r, p in ruins.items():
        print(f"✗ {r}: {' / '.join(p)}")
    for r in redes:
        if r not in ruins:
            print(f"✓ {r}")
    for aviso in avisos(info):
        print(f"⚠ {aviso}")
    return 1 if ruins else 0


if __name__ == "__main__":
    sys.exit(main())
