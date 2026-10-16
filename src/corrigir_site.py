"""Troca o endereço do site nos posts já publicados (LinkedIn, Facebook e Instagram).

O domínio próprio (config.SITE_FORA_DO_AR) saiu do ar, mas os posts antigos ainda o divulgam na
legenda e no primeiro comentário. Este script troca esse endereço pelo do site no ar (config.SITE).
A lista de posts vem do diário (registros/*/index.json no branch assets), então só toca em posts
que a própria automação publicou.

  python src/corrigir_site.py --dest /tmp/assets                    # ensaio: só mostra o que mudaria
  python src/corrigir_site.py --dest /tmp/assets --aplicar          # edita de verdade
  python src/corrigir_site.py --dest /tmp/assets --aplicar --so "facebook:123_456,linkedin:urn:li:share:7511"
  python src/corrigir_site.py --dest /tmp/assets --desfazer registros/2026-10-16/correcao-site-0030.jsonl
  python src/corrigir_site.py --dest /tmp/assets --perfis [--aplicar]   # site/descrição do perfil do Facebook e do Instagram
  python src/corrigir_site.py ... --graph-versao v26.0                  # testa outra versão da Graph API
  python src/corrigir_site.py --dest /tmp/assets --perfis --limpar-site --aplicar   # tenta deixar só 1 site na Página

O que NÃO dá para corrigir: as imagens (o endereço está desenhado nelas) e, no Instagram, a legenda
só muda se a API aceitar; se recusar, o script avisa e a legenda é editada à mão no app.

Cada edição guarda o texto original em registros/<dia>/correcao-site-*.jsonl (o --desfazer
restaura a partir dele) e vira um movimento "editou" no diário. Rodar de novo é seguro: o que já
foi trocado aparece como "sem mudança".
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import pathlib
import re
import sys
import time
from urllib.parse import quote

import config
import movimentos
from publishers import instagram, linkedin
from publishers.common import PublishError, request
from publishers.meta_auth import page_token
from seguranca import redigir

log = logging.getLogger("corrigir_site")

REDES = ("linkedin", "facebook", "instagram")
PAUSA_ENTRE_EDICOES = 0.6  # segundos: as APIs toleram, mas não há pressa
# Redes em que a API pode recusar TODA edição (permissão que o app não tem): depois de duas recusas
# seguidas o script deixa de insistir e marca o resto como "não editável".
REDES_QUE_PODEM_RECUSAR = {"linkedin": "LinkedIn", "instagram": "Instagram"}
DESISTE_APOS = 2

# O endereço antigo, com ou sem esquema/"www." e com caminho opcional. Não casa dentro de outra
# palavra nem depois de "@" (e-mail), "." (subdomínio) ou "/" (outro endereço).
_ANTIGO = re.compile(
    r"(?<![\w@./-])(?P<esquema>https?://)?(?:www\.)?" + re.escape(config.SITE_FORA_DO_AR)
    + r"(?P<caminho>/(?:[^\s)\]}>\"'.,;:!?]|[.,;:!?](?=[^\s)\]}>\"'.,;:!?]))*)?(?![\w-])",
    re.IGNORECASE,
)
_DATA = re.compile(r"\d{4}-\d{2}-\d{2}")


def corrigir_texto(texto: str) -> str:
    """Troca o endereço antigo pelo atual; texto sem o endereço antigo sai igual (idempotente)."""
    return _ANTIGO.sub(lambda m: config.SITE_URL if m.group("esquema") else config.SITE, texto or "")


def tem_endereco_antigo(texto: str) -> bool:
    return bool(_ANTIGO.search(texto or ""))


def linhas_trocadas(antes: str, depois: str) -> list[tuple[str, str]]:
    """Pares (linha antes, linha depois) só das linhas que mudaram, para o ensaio mostrar."""
    return [(a, d) for a, d in zip(antes.splitlines(), depois.splitlines(), strict=False) if a != d]


# ---------------------------------------------------------------- o que foi publicado


@dataclasses.dataclass
class Alvo:
    dia: str
    hora: str
    tema: str
    rede: str
    ident: str
    link: str = ""
    legenda: str = ""     # texto registrado no diário; só vale se a rede não deixar ler o do ar
    comentario: str = ""  # primeiro comentário registrado ("" quando não houve)


@dataclasses.dataclass
class Resultado:
    alvo: Alvo
    campo: str     # "legenda" | "comentário"
    situacao: str  # trocar | ok | sem mudança | não existe mais | não editável | falhou
    antes: str = ""
    depois: str = ""
    detalhe: str = ""


def _blocos_do_registro(md: str) -> dict[str, tuple[str, str]]:
    """{rede: (legenda, primeiro comentário)} do registro HHhMM-tema.md (ver registro.escrever)."""
    saida: dict[str, tuple[str, str]] = {}
    for m in re.finditer(r"^## (?P<nome>[^\n]+)\n(?P<corpo>.*?)(?=^## |\Z)", md, re.S | re.M):
        blocos = re.findall(r"```text\n(.*?)\n```", m["corpo"], re.S)
        if not blocos:
            continue
        comentario = blocos[1] if "Primeiro comentário:" in m["corpo"] and len(blocos) > 1 else ""
        saida[m["nome"].strip().lower()] = (blocos[0], comentario)
    return saida


def _apagados(registros: pathlib.Path) -> set[str]:
    """Ids de posts que o diário registra como apagados (posts de teste, por exemplo)."""
    ids: set[str] = set()
    for arq in registros.glob("*/movimentos.jsonl"):
        for linha in arq.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(linha)
            except json.JSONDecodeError:
                continue
            if ev.get("tipo") == "apagou":
                ids.add(str(ev.get("detalhe", "")).split(" — ")[0].strip())
    return ids


def coletar(dest: pathlib.Path, redes=REDES) -> tuple[list[Alvo], list[str]]:
    """Posts publicados (do mais novo ao mais antigo) e avisos sobre os que ficaram de fora."""
    registros = dest / "registros"
    alvos: list[Alvo] = []
    avisos: list[str] = []
    if not registros.is_dir():
        return alvos, [f"{registros} não existe: o checkout do branch assets está vazio?"]
    apagados = _apagados(registros)
    for pasta in sorted(p for p in registros.iterdir() if p.is_dir() and _DATA.fullmatch(p.name)):
        try:
            entradas = json.loads((pasta / "index.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for e in entradas:
            registro = pasta / str(e.get("arquivo", ""))
            blocos = _blocos_do_registro(registro.read_text(encoding="utf-8")) if registro.is_file() else {}
            for rede in redes:
                if (e.get("redes") or {}).get(rede) != "publicado":
                    continue
                ident = (e.get("ids") or {}).get(rede, "")
                onde = f"{rede} {pasta.name} {e.get('hora', '')} {e.get('tema', '')}"
                if not ident:
                    avisos.append(f"{onde}: o diário não guarda o id; confira à mão")
                    continue
                if ident in apagados:
                    continue
                legenda, comentario = blocos.get(rede, ("", ""))
                alvos.append(Alvo(
                    dia=pasta.name, hora=str(e.get("hora", "")), tema=str(e.get("tema", "")), rede=rede,
                    ident=ident, link=(e.get("links") or {}).get(rede, ""), legenda=legenda,
                    comentario=comentario if rede in (e.get("comentou") or []) else "",
                ))
    alvos.sort(key=lambda a: (a.dia, a.hora), reverse=True)
    return alvos, avisos


# ---------------------------------------------------------------- redes


def _urn(urn: str) -> str:
    return quote(urn, safe="")


def linkedin_ler(creds, urn: str) -> str | None:
    resp = request(
        "GET", f"{config.LINKEDIN_API}/rest/posts/{_urn(urn)}",
        headers=linkedin._headers(creds.linkedin_token), attempts=2,
    )
    texto = resp.json().get("commentary")
    return texto if isinstance(texto, str) else None


def linkedin_editar(creds, urn: str, commentary: str) -> None:
    """Posts API, atualização parcial: só o texto muda; imagem, autor e métricas ficam."""
    request(
        "POST", f"{config.LINKEDIN_API}/rest/posts/{_urn(urn)}",
        headers={**linkedin._headers(creds.linkedin_token), "Content-Type": "application/json",
                 "X-RestLi-Method": "PARTIAL_UPDATE"},
        json={"patch": {"$set": {"commentary": commentary}}},
    )


def _token_meta(creds) -> str:
    return page_token(creds.meta_token, creds.fb_page_id)


def facebook_ler(creds, post_id: str) -> str:
    resp = request(
        "GET", f"{config.GRAPH}/{post_id}",
        params={"fields": "message", "access_token": _token_meta(creds)}, attempts=2,
    )
    return resp.json().get("message", "")


def facebook_editar(creds, post_id: str, texto: str) -> None:
    request("POST", f"{config.GRAPH}/{post_id}", data={"message": texto, "access_token": _token_meta(creds)})


def facebook_comentarios(creds, post_id: str) -> list[dict]:
    """Comentários de primeiro nível do post (até 5 páginas de 100)."""
    token = _token_meta(creds)
    url, params = f"{config.GRAPH}/{post_id}/comments", {"fields": "id,message", "limit": 100, "access_token": token}
    comentarios: list[dict] = []
    for _ in range(5):
        dados = request("GET", url, params=params, attempts=2).json()
        comentarios += dados.get("data", [])
        url = (dados.get("paging") or {}).get("next")
        if not url:
            break
        params = None  # a URL "next" já leva todos os parâmetros
    return comentarios


def facebook_editar_comentario(creds, comentario_id: str, texto: str) -> None:
    request(
        "POST", f"{config.GRAPH}/{comentario_id}",
        data={"message": texto, "access_token": _token_meta(creds)},
    )


def instagram_ler(creds, media_id: str) -> str:
    resp = request(
        "GET", f"{config.GRAPH}/{media_id}",
        params={"fields": "caption", "access_token": instagram._token(creds)}, attempts=2,
    )
    return resp.json().get("caption", "")


def instagram_editar(creds, media_id: str, texto: str) -> None:
    request("POST", f"{config.GRAPH}/{media_id}", data={"caption": texto, "access_token": instagram._token(creds)})


PERFIL_FACEBOOK = ("website", "about", "description")
PERFIL_INSTAGRAM = ("website", "biography")


def facebook_perfil(creds) -> dict:
    """Campos de texto da Página que podem citar o site."""
    resp = request(
        "GET", f"{config.GRAPH}/{creds.fb_page_id}",
        params={"fields": ",".join(PERFIL_FACEBOOK), "access_token": _token_meta(creds)}, attempts=2,
    )
    return resp.json()


def facebook_editar_perfil(creds, campo: str, valor: str) -> None:
    request("POST", f"{config.GRAPH}/{creds.fb_page_id}", data={campo: valor, "access_token": _token_meta(creds)})


def _numeros(obj_id: str, token: str, campos: tuple[str, ...]) -> dict:
    """Contadores públicos, um campo por chamada: se a API recusar um, os outros ainda saem."""
    saida: dict[str, int] = {}
    for campo in campos:
        try:
            valor = request("GET", f"{config.GRAPH}/{obj_id}", params={"fields": campo, "access_token": token},
                            attempts=2).json().get(campo)
        except PublishError:
            continue
        if isinstance(valor, int):
            saida[campo] = valor
    return saida


def facebook_audiencia(creds) -> dict:
    return _numeros(creds.fb_page_id, _token_meta(creds), ("followers_count", "fan_count"))


def instagram_audiencia(creds) -> dict:
    return _numeros(creds.ig_user_id, instagram._token(creds), ("followers_count", "follows_count", "media_count"))


def _audiencia_texto(dados: dict, nomes: dict[str, str]) -> str:
    partes = [f"{nomes[c]} {dados[c]}" for c in nomes if c in dados]
    return " · ".join(partes) if partes else "indisponível (a API recusou os contadores)"


def instagram_perfil(creds) -> dict:
    resp = request(
        "GET", f"{config.GRAPH}/{creds.ig_user_id}",
        params={"fields": ",".join(PERFIL_INSTAGRAM), "access_token": instagram._token(creds)}, attempts=2,
    )
    return resp.json()


# ---------------------------------------------------------------- correção


class Backup:
    """Guarda, antes de cada edição, o texto original e o novo (para o --desfazer)."""

    def __init__(self, caminho: pathlib.Path | None):
        self.caminho = caminho
        if caminho:
            caminho.parent.mkdir(parents=True, exist_ok=True)

    def registrar(self, **campos) -> None:
        if not self.caminho:
            return
        with self.caminho.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"quando": config.agora().isoformat(timespec="seconds"), **campos},
                                ensure_ascii=False) + "\n")


def _curto(exc: Exception) -> str:
    return redigir(re.sub(r"\s+", " ", str(exc)))[:220]


def _erro_de_leitura(a: Alvo, exc: Exception) -> Resultado:
    """Post que a Graph API diz não existir (apagado direto no app) não é falha; o resto é."""
    if "does not exist" in str(exc) or "HTTP 404" in str(exc):
        return Resultado(a, "legenda", "não existe mais", detalhe="não encontrado (apagado no app?)")
    return Resultado(a, "legenda", "falhou", detalhe=_curto(exc))


def _normalizar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def _forma_linkedin(vivo: str, registrada: str) -> str | None:
    """"escapada" se o texto no ar vem no formato do LinkedIn (com \\#), "plana" se vem sem escapes."""
    if registrada:
        if vivo == linkedin.escape_commentary(registrada):
            return "escapada"
        if vivo == registrada:
            return "plana"
    if "\\#" in vivo:
        return "escapada"
    return "plana" if "#" in vivo else None


def _aplicar(a: Alvo, campo: str, antes: str, aplicar: bool, editar, reler, backup: Backup,
             chave: dict, extra: str = "") -> Resultado:
    """Troca o endereço em `antes` e, com --aplicar, edita, confere no ar e guarda o original."""
    depois = corrigir_texto(antes)
    if depois == antes:
        return Resultado(a, campo, "sem mudança", detalhe=extra)
    if not aplicar:
        return Resultado(a, campo, "trocar", antes, depois, extra)
    backup.registrar(**chave, campo=campo, estado="tentando", antes=antes, depois=depois)
    try:
        editar(depois)
    except PublishError as exc:
        backup.registrar(**chave, campo=campo, estado="falhou", erro=_curto(exc))
        return Resultado(a, campo, "falhou", antes, depois, _curto(exc))
    detalhe = extra
    if reler:
        try:
            if tem_endereco_antigo(reler()):
                backup.registrar(**chave, campo=campo, estado="falhou", erro="o texto no ar não mudou")
                return Resultado(a, campo, "falhou", antes, depois, "a rede aceitou a edição, mas o texto no ar não mudou")
        except PublishError:
            detalhe = (extra + "; " if extra else "") + "edição aceita; não deu para reler e confirmar"
    backup.registrar(**chave, campo=campo, estado="ok")
    time.sleep(PAUSA_ENTRE_EDICOES)
    return Resultado(a, campo, "ok", antes, depois, detalhe)


def _corrigir_linkedin(creds, a: Alvo, aplicar: bool, backup: Backup) -> list[Resultado]:
    chave = {"rede": a.rede, "id": a.ident, "dia": a.dia}
    vivo, extra = None, ""
    try:
        vivo = linkedin_ler(creds, a.ident)
    except PublishError as exc:
        if "HTTP 404" in str(exc):
            return [Resultado(a, "legenda", "não existe mais", detalhe=_curto(exc))]
        extra = "texto do diário (a API não deixou ler o do ar)"
        log.warning("linkedin %s: leitura recusada (%s)", a.ident, _curto(exc))
    if vivo is None:
        if not a.legenda:
            return [Resultado(a, "legenda", "falhou", detalhe="não consegui ler o texto no ar nem achei o do diário")]
        antes, reler = linkedin.escape_commentary(a.legenda), None
    else:
        if not tem_endereco_antigo(vivo):
            return [Resultado(a, "legenda", "sem mudança")]
        forma = _forma_linkedin(vivo, a.legenda)
        if forma is None:
            return [Resultado(a, "legenda", "falhou", detalhe="não reconheci o formato do texto no ar; não mexi")]
        antes = vivo if forma == "escapada" else linkedin.escape_commentary(vivo)
        reler = lambda: linkedin_ler(creds, a.ident) or ""  # noqa: E731
    return [_aplicar(a, "legenda", antes, aplicar, lambda t: linkedin_editar(creds, a.ident, t), reler,
                     backup, chave, extra)]


def _corrigir_facebook(creds, a: Alvo, aplicar: bool, backup: Backup) -> list[Resultado]:
    chave = {"rede": a.rede, "id": a.ident, "dia": a.dia}
    resultados: list[Resultado] = []
    try:
        vivo = facebook_ler(creds, a.ident)
    except PublishError as exc:
        return [_erro_de_leitura(a, exc)]
    resultados.append(_aplicar(
        a, "legenda", vivo, aplicar, lambda t: facebook_editar(creds, a.ident, t),
        lambda: facebook_ler(creds, a.ident), backup, chave,
    ))
    if not a.comentario:
        return resultados
    try:
        comentarios = facebook_comentarios(creds, a.ident)
    except PublishError as exc:
        return resultados + [Resultado(a, "comentário", "falhou", detalhe=_curto(exc))]
    registrado = _normalizar(a.comentario)
    novo = _normalizar(corrigir_texto(a.comentario))
    nosso = [c for c in comentarios
             if _normalizar(c.get("message", "")) in (registrado, novo)
             or (c.get("message", "").startswith("🌐") and tem_endereco_antigo(c.get("message", "")))]
    if not nosso:
        return resultados + [Resultado(a, "comentário", "falhou", detalhe="não achei o primeiro comentário no post")]
    for c in nosso:
        cid = c["id"]
        resultados.append(_aplicar(
            a, "comentário", c.get("message", ""), aplicar, lambda t, cid=cid: facebook_editar_comentario(creds, cid, t),
            None, backup, {**chave, "comentario_id": cid},
        ))
    return resultados


def _corrigir_instagram(creds, a: Alvo, aplicar: bool, backup: Backup) -> list[Resultado]:
    chave = {"rede": a.rede, "id": a.ident, "dia": a.dia}
    try:
        vivo = instagram_ler(creds, a.ident)
    except PublishError as exc:
        return [_erro_de_leitura(a, exc)]
    return [_aplicar(a, "legenda", vivo, aplicar, lambda t: instagram_editar(creds, a.ident, t),
                     lambda: instagram_ler(creds, a.ident), backup, chave)]


_CORRETORES = {"linkedin": _corrigir_linkedin, "facebook": _corrigir_facebook, "instagram": _corrigir_instagram}


def corrigir(creds, alvos: list[Alvo], aplicar: bool, backup: Backup) -> list[Resultado]:
    """Corrige cada post; falha num não impede os demais. Se o LinkedIn ou o Instagram recusarem a
    edição duas vezes seguidas, o resto daquela rede é dado como não editável (e não é mais consultado)."""
    resultados: list[Resultado] = []
    recusas = dict.fromkeys(REDES_QUE_PODEM_RECUSAR, 0)
    desistiu: dict[str, str] = {}
    for a in alvos:
        if a.rede in desistiu:
            resultados.append(Resultado(a, "legenda", "não editável", detalhe=desistiu[a.rede]))
            continue
        try:
            novos = _CORRETORES[a.rede](creds, a, aplicar, backup)
        except Exception as exc:  # noqa: BLE001 — um post com erro não pode parar os outros
            novos = [Resultado(a, "legenda", "falhou", detalhe=_curto(exc))]
        resultados += novos
        if a.rede in recusas and aplicar:
            recusada = [r for r in novos if r.situacao == "falhou" and r.antes]  # leu/preparou, mas a edição foi recusada
            if recusada:
                recusas[a.rede] += 1
                if recusas[a.rede] >= DESISTE_APOS:
                    desistiu[a.rede] = f"a API do {REDES_QUE_PODEM_RECUSAR[a.rede]} recusou a edição: {recusada[0].detalhe}"
            elif any(r.situacao == "ok" for r in novos):
                recusas[a.rede] = 0
    return resultados


def corrigir_perfis(creds, aplicar: bool, backup: Backup, redes=("facebook", "instagram"),
                    limpar_site: bool = False) -> list[Resultado]:
    """Site/descrição do perfil. O "Sobre" da Página a API edita; o campo Site da Página (a API só acrescenta) e a
    bio do Instagram (a API não edita) só se trocam no app, então aqui são conferidos e, se citarem o domínio
    antigo, avisados."""
    dia = f"{config.hoje():%Y-%m-%d}"
    resultados: list[Resultado] = []
    if "facebook" in redes:
        a = Alvo(dia=dia, hora="", tema="perfil", rede="facebook", ident=creds.fb_page_id)
        try:
            dados = facebook_perfil(creds)
        except PublishError as exc:
            dados = None
            resultados.append(Resultado(a, "perfil", "falhou", detalhe=_curto(exc)))
        for campo in PERFIL_FACEBOOK if dados is not None else ():
            valor = dados.get(campo) or ""
            if campo == "website" and limpar_site and aplicar:
                resultados.append(limpar_site_da_pagina(creds, backup))
                continue
            if campo == "website":
                # a API trata o Site como lista e ACRESCENTA em vez de substituir (visto em 16/10/2026: cada POST
                # somou uma entrada e a antiga ficou), então este campo só se troca no app (ou com --limpar-site)
                resultados.append(
                    Resultado(a, f"perfil:{campo}", "não editável", valor, corrigir_texto(valor),
                              f"troque no app, deixando só {config.SITE_URL}") if tem_endereco_antigo(valor)
                    else Resultado(a, f"perfil:{campo}", "sem mudança", detalhe=f"hoje: {valor[:90]!r}" if valor else "vazio"))
                continue
            r = _aplicar(a, f"perfil:{campo}", valor, aplicar,
                         lambda t, c=campo: facebook_editar_perfil(creds, c, t),
                         lambda c=campo: facebook_perfil(creds).get(c, ""), backup,
                         {"rede": "facebook", "id": creds.fb_page_id, "dia": dia})
            if r.situacao == "sem mudança":
                r.detalhe = f"hoje: {valor[:90]!r}" if valor else "vazio"
            resultados.append(r)
        resultados.append(Resultado(a, "audiência", "sem mudança", detalhe=_audiencia_texto(
            facebook_audiencia(creds), {"followers_count": "seguidores", "fan_count": "curtidas"})))
    if "instagram" in redes:
        a = Alvo(dia=dia, hora="", tema="perfil", rede="instagram", ident=creds.ig_user_id)
        try:
            dados = instagram_perfil(creds)
        except PublishError as exc:
            return resultados + [Resultado(a, "perfil", "falhou", detalhe=_curto(exc))]
        resultados.append(Resultado(a, "audiência", "sem mudança", detalhe=_audiencia_texto(
            instagram_audiencia(creds), {"followers_count": "seguidores", "follows_count": "seguindo", "media_count": "posts"})))
        for campo in PERFIL_INSTAGRAM:
            valor = dados.get(campo) or ""
            if tem_endereco_antigo(valor):
                resultados.append(Resultado(a, f"perfil:{campo}", "não editável", valor, corrigir_texto(valor),
                                            f"o Instagram só deixa trocar no app: use {config.SITE_URL}"))
            else:
                resultados.append(Resultado(a, f"perfil:{campo}", "sem mudança",
                                            detalhe=f"hoje: {valor[:90]!r}" if valor else "vazio"))
    return resultados


PAUSA_LEITURA = 6  # segundos: o Facebook leva um instante para refletir a edição do perfil


def limpar_site_da_pagina(creds, backup: Backup) -> Resultado:
    """Tenta deixar o campo Site da Página só com o endereço novo: limpa e grava de novo. A API trata o campo
    como lista e acrescenta ao gravar; se não aceitar limpar, o resultado é "não editável" e a troca é no app."""
    dia = f"{config.hoje():%Y-%m-%d}"
    a = Alvo(dia=dia, hora="", tema="perfil", rede="facebook", ident=creds.fb_page_id)
    campo, alvo = "perfil:website", config.SITE_URL
    chave = {"rede": "facebook", "id": creds.fb_page_id, "dia": dia}
    antes = (facebook_perfil(creds).get("website") or "").strip()
    if _sem_repeticao(antes) == alvo:
        return Resultado(a, campo, "sem mudança", detalhe=f"hoje: {antes[:90]!r}")
    backup.registrar(**chave, campo=campo, estado="tentando", antes=antes, depois=alvo)
    try:
        facebook_editar_perfil(creds, "website", "")
        time.sleep(PAUSA_LEITURA)
        restou = (facebook_perfil(creds).get("website") or "").strip()
        if restou:
            backup.registrar(**chave, campo=campo, estado="falhou", erro="a API não limpou o campo")
            return Resultado(a, campo, "não editável", antes, alvo,
                             f"a API não limpa o campo (hoje: {restou[:90]!r}); troque no app, deixando só {alvo}")
        facebook_editar_perfil(creds, "website", alvo)
        time.sleep(PAUSA_LEITURA)
        final = (facebook_perfil(creds).get("website") or "").strip()
    except PublishError as exc:
        backup.registrar(**chave, campo=campo, estado="falhou", erro=_curto(exc))
        return Resultado(a, campo, "falhou", antes, alvo, _curto(exc))
    if _sem_repeticao(final) != alvo or "," in final:
        backup.registrar(**chave, campo=campo, estado="falhou", erro=f"ficou {final!r}")
        return Resultado(a, campo, "falhou", antes, alvo, f"depois de limpar e gravar, o campo ficou {final[:90]!r}")
    backup.registrar(**chave, campo=campo, estado="ok")
    return Resultado(a, campo, "ok", antes, final, "campo limpo e gravado de novo")


def _sem_repeticao(lista: str) -> str:
    """"a, a" -> "a": só para comparar o campo Site da Página, que guarda o endereço mais de uma vez."""
    return ", ".join(dict.fromkeys(x.strip() for x in lista.split(",") if x.strip()))


def desfazer(creds, arquivo: pathlib.Path) -> list[Resultado]:
    """Restaura os textos originais guardados num backup (um passo por edição que não falhou)."""
    ultimo: dict[tuple, dict] = {}
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        r = json.loads(linha)
        chave = (r["rede"], r["id"], r.get("comentario_id", ""), r["campo"])
        ultimo[chave] = {**ultimo.get(chave, {}), **r}
    resultados: list[Resultado] = []
    for (rede, ident, cid, campo), r in ultimo.items():
        a = Alvo(dia=r.get("dia", ""), hora="", tema="", rede=rede, ident=ident)
        if r.get("estado") == "falhou" or "antes" not in r:
            continue
        antes = r["antes"]
        try:
            if rede == "linkedin":
                linkedin_editar(creds, ident, antes)
            elif rede == "facebook" and campo == "comentário":
                facebook_editar_comentario(creds, cid, antes)
            elif rede == "facebook" and campo.startswith("perfil:"):
                facebook_editar_perfil(creds, campo.split(":", 1)[1], antes)
            elif rede == "facebook":
                facebook_editar(creds, ident, antes)
            else:
                instagram_editar(creds, ident, antes)
        except PublishError as exc:
            resultados.append(Resultado(a, campo, "falhou", detalhe=_curto(exc)))
        else:
            resultados.append(Resultado(a, campo, "ok", r.get("depois", ""), antes, "restaurado"))
            time.sleep(PAUSA_ENTRE_EDICOES)
    return resultados


# ---------------------------------------------------------------- linha de comando


def _linha(r: Resultado) -> str:
    a = r.alvo
    cabeca = f"{r.situacao:<16} {a.rede:<9} {a.dia} {a.hora:<5} {r.campo:<10} {a.ident}"
    return cabeca + (f"  [{r.detalhe}]" if r.detalhe else "")


def _eventos(resultados: list[Resultado], origem: str) -> list[dict]:
    """Movimentos do diário: uma linha por edição feita e por falha; a rede que recusou vira um aviso só."""
    eventos: list[dict] = []
    for r in resultados:
        a = r.alvo
        base = {"rede": a.rede, "tema": config.THEME_LABELS.get(a.tema, a.tema), "origem": origem, "link": a.link}
        if r.situacao == "ok":
            onde = "do perfil" if a.tema == "perfil" else f"do post de {a.dia}"
            eventos.append({**base, "tipo": "editou",
                            "detalhe": f"{r.campo} {onde}: {config.SITE_FORA_DO_AR} → {config.SITE}"
                                       + (f" ({r.detalhe})" if r.detalhe else "")})
        elif r.situacao == "falhou":
            onde = "do perfil" if a.tema == "perfil" else f"do post de {a.dia}"
            eventos.append({**base, "tipo": "falhou",
                            "detalhe": f"não consegui corrigir o {r.campo} {onde} ({a.ident}): {r.detalhe}"})
    for r in resultados:
        if r.situacao == "não editável" and r.alvo.tema == "perfil":
            eventos.append({"rede": r.alvo.rede, "origem": origem, "tipo": "observacao",
                            "detalhe": f"o {r.campo} da {r.alvo.rede} ainda cita {config.SITE_FORA_DO_AR}: {r.detalhe}"})
    for rede in REDES_QUE_PODEM_RECUSAR:
        nao_editaveis = [r for r in resultados
                         if r.situacao == "não editável" and r.alvo.rede == rede and r.alvo.tema != "perfil"]
        if nao_editaveis:
            eventos.append({"rede": rede, "origem": origem, "tipo": "observacao",
                            "detalhe": f"{len(nao_editaveis)} posts não puderam ser editados pela API; "
                                       f"troque o endereço à mão no app: {nao_editaveis[0].detalhe}"})
    return eventos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Troca o endereço do site nos posts já publicados")
    ap.add_argument("--dest", required=True, help="checkout do branch assets (tem registros/)")
    ap.add_argument("--aplicar", action="store_true", help="edita de verdade (sem isso: ensaio)")
    ap.add_argument("--redes", default=",".join(REDES), help="linkedin,facebook,instagram")
    ap.add_argument("--so", default="", help="só estes posts: rede:id separados por vírgula")
    ap.add_argument("--limite", type=int, default=0, help="máximo de posts a processar (0 = todos)")
    ap.add_argument("--desfazer", default="", help="restaura os textos de um arquivo correcao-site-*.jsonl")
    ap.add_argument("--perfis", action="store_true", help="em vez dos posts, confere o site/descrição do perfil do Facebook e do Instagram")
    ap.add_argument("--limpar-site", action="store_true",
                    help="com --perfis --aplicar: tenta deixar só o endereço novo no campo Site da Página (limpa e grava)")
    ap.add_argument("--graph-versao", default="", help="versão da Graph API (ex.: v26.0); padrão: a de config.py")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    if a.graph_versao:
        config.GRAPH = f"https://graph.facebook.com/{a.graph_versao}"
        print(f"Graph API: {a.graph_versao}")
    dest = pathlib.Path(a.dest)
    creds = config.Credentials()
    origem = "workflow Corrigir site"

    if a.desfazer:
        resultados = desfazer(creds, dest / a.desfazer)
        for r in resultados:
            print(_linha(r))
        movimentos.registrar(dest, [
            {"tipo": "editou" if r.situacao == "ok" else "falhou", "rede": r.alvo.rede, "origem": origem,
             "detalhe": f"{r.campo} de {r.alvo.ident} restaurado ao texto original" if r.situacao == "ok"
             else f"não consegui restaurar {r.campo} de {r.alvo.ident}: {r.detalhe}"}
            for r in resultados
        ])
        return 1 if any(r.situacao == "falhou" for r in resultados) else 0

    if a.perfis:
        caminho = dest / "registros" / f"{config.hoje():%Y-%m-%d}" / f"correcao-site-{config.agora():%H%M}.jsonl"
        backup = Backup(caminho if a.aplicar else None)
        redes_perfil = [r for r, ok in (("facebook", creds.has_facebook), ("instagram", creds.has_instagram)) if ok]
        resultados = corrigir_perfis(creds, a.aplicar, backup, redes_perfil, limpar_site=a.limpar_site)
        for r in resultados:
            print(_linha(r))
            for antes, depois in linhas_trocadas(r.antes, r.depois):
                print(f"    - {antes[:150]}\n    + {depois[:150]}")
        if a.aplicar:
            movimentos.registrar(dest, _eventos(resultados, origem))
        return 1 if any(r.situacao == "falhou" for r in resultados) else 0

    redes = [r.strip() for r in a.redes.split(",") if r.strip()]
    desconhecidas = [r for r in redes if r not in REDES]
    if desconhecidas:
        ap.error(f"rede desconhecida: {', '.join(desconhecidas)}")
    disponiveis = {"linkedin": creds.has_linkedin, "facebook": creds.has_facebook, "instagram": creds.has_instagram}
    for r in [r for r in redes if not disponiveis[r]]:
        print(f"{r}: sem credenciais neste ambiente; pulada")
    redes = [r for r in redes if disponiveis[r]]

    alvos, avisos = coletar(dest, redes)
    if a.so:
        escolhidos = {tuple(x.strip().split(":", 1)) for x in a.so.split(",") if x.strip()}
        alvos = [x for x in alvos if (x.rede, x.ident) in escolhidos]
    if a.limite > 0:
        alvos = alvos[: a.limite]
    for aviso in avisos:
        print(f"aviso: {aviso}")
    print(f"{len(alvos)} post(s) a conferir ({'EDITANDO' if a.aplicar else 'ensaio, nada será editado'})")

    caminho = dest / "registros" / f"{config.hoje():%Y-%m-%d}" / f"correcao-site-{config.agora():%H%M}.jsonl"
    backup = Backup(caminho if a.aplicar else None)
    resultados = corrigir(creds, alvos, a.aplicar, backup)

    for r in resultados:
        if r.situacao != "sem mudança":
            print(_linha(r))
            for antes, depois in linhas_trocadas(r.antes, r.depois):
                print(f"    - {antes[:150]}\n    + {depois[:150]}")
    contagem: dict[tuple[str, str], int] = {}
    for r in resultados:
        contagem[(r.alvo.rede, r.situacao)] = contagem.get((r.alvo.rede, r.situacao), 0) + 1
    print("\nResumo:")
    for (rede, situacao), n in sorted(contagem.items()):
        print(f"  {rede:<9} {situacao:<16} {n}")
    if a.aplicar:
        print(f"Originais guardados em {caminho.relative_to(dest)}")
        movimentos.registrar(dest, _eventos(resultados, origem))
    return 1 if any(r.situacao == "falhou" for r in resultados) else 0


if __name__ == "__main__":
    sys.exit(main())
