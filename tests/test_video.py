"""Vídeo: leitura do MP4, limites por rede, pauta, legendas, manifesto e a integração com main.publish."""
import datetime as dt
import json
import pathlib
import struct

import pytest

import config
import main
import registro
import video
from conftest import DIA

# ------------------------------------------------------------------ MP4 de mentira (só os cabeçalhos que o módulo lê)


def caixa(tipo: bytes, conteudo: bytes = b"") -> bytes:
    return struct.pack(">I4s", 8 + len(conteudo), tipo) + conteudo


def mvhd(segundos: float, escala: int = 1000, versao: int = 0) -> bytes:
    if versao == 1:
        corpo = bytes([1, 0, 0, 0]) + bytes(16) + struct.pack(">IQ", escala, int(segundos * escala))
    else:
        corpo = bytes(4) + bytes(8) + struct.pack(">II", escala, int(segundos * escala))
    return caixa(b"mvhd", corpo + bytes(80))


def tkhd(largura: int, altura: int, giro: bool = False, versao: int = 0) -> bytes:
    inicio = bytes([versao, 0, 0, 0]) + bytes(8 if versao == 0 else 16) + bytes(4) + bytes(4) + bytes(4 if versao == 0 else 8)
    inicio += bytes(8) + bytes(8)                      # reservado, camada/grupo/volume/reservado
    matriz = [0, 0x10000 if giro else 0, 0, -0x10000 if giro else 0, 0, 0, 0, 0, 0x40000000]
    if not giro:
        matriz[0], matriz[4] = 0x10000, 0x10000
    corpo = inicio + struct.pack(">9i", *matriz) + struct.pack(">II", largura << 16, altura << 16)
    return caixa(b"tkhd", corpo)


def trilha(tipo: bytes, codec: bytes, largura: int = 0, altura: int = 0, edit_list: bool = False, giro: bool = False,
           versao_tkhd: int = 0) -> bytes:
    hdlr = caixa(b"hdlr", bytes(4) + bytes(4) + tipo + bytes(12) + b"x\0")
    stsd = caixa(b"stsd", bytes(4) + struct.pack(">I", 1) + struct.pack(">I4s", 86, codec) + bytes(78))
    minf = caixa(b"minf", caixa(b"stbl", stsd))
    mdia = caixa(b"mdia", hdlr + minf)
    edts = caixa(b"edts", caixa(b"elst", bytes(4) + struct.pack(">I", 0))) if edit_list else b""
    return caixa(b"trak", tkhd(largura, altura, giro, versao_tkhd) + edts + mdia)


def mp4(*, segundos=10.0, largura=1080, altura=1920, faststart=True, edit_list=False, audio=True, giro=False,
        codec=b"avc1", tamanho_mdat=80_000, versao_mvhd=0, versao_tkhd=0) -> bytes:
    ftyp = caixa(b"ftyp", b"isom" + bytes(4) + b"isomavc1")
    trilhas = trilha(b"vide", codec, largura, altura, edit_list, giro, versao_tkhd)
    if audio:
        trilhas += trilha(b"soun", b"mp4a")
    moov = caixa(b"moov", mvhd(segundos, versao=versao_mvhd) + trilhas)
    mdat = caixa(b"mdat", bytes(tamanho_mdat))
    return ftyp + (moov + mdat if faststart else mdat + moov)


@pytest.fixture
def arquivo(tmp_path):
    def criar(nome="v.mp4", **kw) -> pathlib.Path:
        caminho = tmp_path / nome
        caminho.write_bytes(mp4(**kw))
        return caminho
    return criar


# ------------------------------------------------------------------ inspecionar


def test_inspecionar_le_duracao_dimensoes_codecs_e_estrutura(arquivo):
    info = video.inspecionar(arquivo())
    assert (info.largura, info.altura, round(info.duracao, 2)) == (1080, 1920, 10.0)
    assert info.codec_video == "avc1" and info.codec_audio == "mp4a"
    assert info.faststart is True and info.edit_list is False
    assert info.proporcao == pytest.approx(9 / 16)


def test_inspecionar_percebe_moov_no_fim_e_lista_de_edicao(arquivo):
    info = video.inspecionar(arquivo(faststart=False, edit_list=True))
    assert info.faststart is False and info.edit_list is True


def test_inspecionar_entende_versao_1_do_mvhd_e_do_tkhd(arquivo):
    info = video.inspecionar(arquivo(segundos=95.5, versao_mvhd=1, versao_tkhd=1))
    assert round(info.duracao, 1) == 95.5 and (info.largura, info.altura) == (1080, 1920)


def test_inspecionar_desfaz_o_giro_de_90_graus_do_celular(arquivo):
    info = video.inspecionar(arquivo(largura=1920, altura=1080, giro=True))   # gravado em paisagem + giro
    assert (info.largura, info.altura) == (1080, 1920)


def test_inspecionar_video_sem_audio(arquivo):
    assert video.inspecionar(arquivo(audio=False)).codec_audio == ""


@pytest.mark.parametrize("conteudo, trecho", [
    (b"isto nao e um mp4 de jeito nenhum", "ftyp"),
    (mp4()[:60], "truncado"),
    (caixa(b"ftyp", b"isom" + bytes(8)), "moov"),
])
def test_inspecionar_recusa_arquivo_que_nao_serve(tmp_path, conteudo, trecho):
    caminho = tmp_path / "ruim.mp4"
    caminho.write_bytes(conteudo)
    with pytest.raises(video.VideoInvalido, match=trecho):
        video.inspecionar(caminho)


def test_inspecionar_sem_trilha_de_video_e_arquivo_inexistente(tmp_path):
    so_audio = tmp_path / "audio.mp4"
    so_audio.write_bytes(caixa(b"ftyp", b"isom" + bytes(8)) + caixa(b"moov", mvhd(5) + trilha(b"soun", b"mp4a")))
    with pytest.raises(video.VideoInvalido, match="trilha de vídeo"):
        video.inspecionar(so_audio)
    with pytest.raises(video.VideoInvalido, match="abrir"):
        video.inspecionar(tmp_path / "nao-existe.mp4")


# ------------------------------------------------------------------ limites por rede


def test_video_vertical_de_10_segundos_serve_para_as_tres_redes(arquivo):
    assert video.conferir(video.inspecionar(arquivo())) == {"linkedin": [], "facebook": [], "instagram": []}


def test_instagram_exige_moov_na_frente_e_sem_lista_de_edicao(arquivo):
    ruim = video.conferir(video.inspecionar(arquivo(faststart=False, edit_list=True)), ["instagram"])["instagram"]
    assert any("moov" in p for p in ruim) and any("lista de edição" in p for p in ruim)
    assert video.conferir(video.inspecionar(arquivo(faststart=False, edit_list=True)), ["linkedin"])["linkedin"] == []


def test_reel_do_facebook_e_9_por_16_de_3_a_90_segundos(arquivo):
    horizontal = video.conferir(video.inspecionar(arquivo(largura=1920, altura=1080)), ["facebook"])["facebook"]
    assert any("9:16" in p for p in horizontal)
    longo = video.conferir(video.inspecionar(arquivo(segundos=120)), ["facebook"])["facebook"]
    assert any("máximo é 90" in p for p in longo)
    curto = video.conferir(video.inspecionar(arquivo(segundos=2)), ["facebook", "instagram", "linkedin"])
    assert all(any("mínimo é 3" in p for p in ps) for ps in curto.values())
    pequeno = video.conferir(video.inspecionar(arquivo(largura=360, altura=640)), ["facebook"])["facebook"]
    assert any("540x960" in p for p in pequeno)


def test_limites_de_tamanho_e_de_duracao_do_instagram_e_do_linkedin(arquivo):
    info = video.inspecionar(arquivo(segundos=1000))
    assert video.conferir(info, ["instagram"])["instagram"] and video.conferir(info, ["linkedin"])["linkedin"] == []
    grande = video.InfoMP4(tamanho=301 * 2**20, duracao=10, largura=1080, altura=1920, faststart=True,
                           edit_list=False, codec_video="avc1", codec_audio="mp4a")
    assert any("300 MB" in p for p in video.conferir(grande, ["instagram"])["instagram"])
    assert video.conferir(grande, ["linkedin"])["linkedin"] == []   # o LinkedIn aceita até 500 MB
    minimo = video.InfoMP4(tamanho=1000, duracao=10, largura=1080, altura=1920, faststart=True,
                           edit_list=False, codec_video="avc1", codec_audio="")
    assert video.conferir(minimo, ["linkedin"])["linkedin"] == ["arquivo pequeno demais"]


def test_codec_de_video_fora_da_lista_do_instagram(arquivo):
    ps = video.conferir(video.inspecionar(arquivo(codec=b"vp09")), ["instagram"])["instagram"]
    assert any("H.264" in p for p in ps)


def test_rede_sem_suporte_a_video_e_avisos(arquivo):
    assert video.conferir(video.inspecionar(arquivo()), ["twitter"])["twitter"]
    avisos = video.avisos(video.inspecionar(arquivo(largura=1080, altura=1080, audio=False)))
    assert any("não é 9:16" in a for a in avisos) and any("sem áudio" in a for a in avisos)
    assert video.avisos(video.inspecionar(arquivo())) == []


# ------------------------------------------------------------------ pauta e legendas

PAUTA = {
    "titulo": "Acompanhe a TECHDIM",
    "arquivo": "videos/2026-10-16/apresentacao.mp4",
    "legenda": "Análises técnicas todos os dias.\n\nSiga a TECHDIM.",
    "hashtags": ["#TECHDIM", "#InfraestruturaDeTI", "#Ciberseguranca", "#IA", "#TI", "#Campinas"],
    "ia": True,
    "capa_ms": 2500,
}


@pytest.fixture
def pautas(tmp_path):
    pasta = tmp_path / "content"
    (pasta / "videos").mkdir(parents=True)

    def escrever(nome="v", dados=None):
        texto = dados if isinstance(dados, str) else json.dumps(PAUTA if dados is None else dados)
        (pasta / "videos" / f"{nome}.json").write_text(texto, encoding="utf-8")
        return pasta
    return escrever


def test_pauta_valida_e_normalizada(pautas):
    p = video.carregar_pauta("v", pautas("v", {**PAUTA, "titulo": "  Com espaços  ", "ia": 1}))
    assert p["titulo"] == "Com espaços" and p["ia"] is True
    sem_ia = {k: v for k, v in PAUTA.items() if k != "ia"}
    assert video.carregar_pauta("v", pautas("v", sem_ia))["ia"] is False


@pytest.mark.parametrize("nome", ["", "../segredo", "A-maiusculo", "com espaco", "-comeca-com-hifen", "a/b"])
def test_nome_da_pauta_nao_aceita_caminho(pautas, nome):
    with pytest.raises(video.VideoInvalido, match="nome do vídeo"):
        video.carregar_pauta(nome, pautas())


@pytest.mark.parametrize("campo, valor, trecho", [
    ("titulo", "", "titulo"),
    ("titulo", "t" * 101, "titulo"),
    ("legenda", "   ", "legenda"),
    ("arquivo", "../videos/x.mp4", "arquivo"),
    ("arquivo", "posts/x.mp4", "arquivo"),
    ("arquivo", "videos/x.mov", "arquivo"),
    ("arquivo", "videos/../../x.mp4", "arquivo"),
    ("hashtags", "#TECHDIM", "hashtags"),
    ("capa_ms", -1, "capa_ms"),
    ("capa_ms", True, "capa_ms"),
    ("capa_ms", "2500", "capa_ms"),
])
def test_pauta_com_campo_ruim_e_recusada(pautas, campo, valor, trecho):
    with pytest.raises(video.VideoInvalido, match=trecho):
        video.carregar_pauta("v", pautas("v", {**PAUTA, campo: valor}))


def test_pauta_ausente_ou_quebrada(pautas, tmp_path):
    with pytest.raises(video.VideoInvalido, match="não encontrada"):
        video.carregar_pauta("nao-existe", pautas())
    with pytest.raises(video.VideoInvalido, match="JSON"):
        video.carregar_pauta("v", pautas("v", "{isto não é json"))
    with pytest.raises(video.VideoInvalido, match="objeto"):
        video.carregar_pauta("v", pautas("v", "[1, 2]"))


def test_pauta_nao_pode_citar_o_dominio_fora_do_ar_nem_telefone(pautas):
    antigo = f"Veja www.{config.SITE_FORA_DO_AR}"
    with pytest.raises(video.VideoInvalido, match="fora do ar"):
        video.carregar_pauta("v", pautas("v", {**PAUTA, "legenda": antigo}))
    with pytest.raises(video.VideoInvalido, match="fora do ar"):
        video.carregar_pauta("v", pautas("v", {**PAUTA, "hashtags": [f"#{config.SITE_FORA_DO_AR}"]}))
    with pytest.raises(video.VideoInvalido, match="telefone"):
        video.carregar_pauta("v", pautas("v", {**PAUTA, "legenda": "Ligue (19) 99615-3276"}))


@pytest.mark.parametrize("rede", video.REDES_DE_VIDEO)
def test_legenda_traz_aviso_de_ia_hashtags_no_limite_e_nunca_o_dominio_antigo(rede):
    texto = video.legenda({**PAUTA}, rede)
    assert texto.startswith(PAUTA["titulo"]) and "inteligência artificial" in texto
    assert config.SITE_FORA_DO_AR not in texto and len(texto) <= 2200
    tags = [p for p in texto.split() if p.startswith("#")]
    assert 1 <= len(tags) <= {"linkedin": 5, "facebook": 4, "instagram": 8}[rede]
    assert any(t.lower() == "#techdim" for t in tags)           # a marca sempre entra
    assert "inteligência artificial" not in video.legenda({**PAUTA, "ia": False}, rede)


def test_legenda_de_cada_rede_tem_o_endereco_do_jeito_dela():
    assert config.SITE_URL in video.legenda(PAUTA, "linkedin")
    assert "Link na bio" in video.legenda(PAUTA, "instagram") and config.SITE in video.legenda(PAUTA, "instagram")
    assert "primeiro comentário" in video.legenda(PAUTA, "facebook")
    assert config.SITE_URL in video.comentario("facebook")
    assert video.comentario("linkedin") == video.comentario("instagram") == ""
    assert "#techdim" in video.legenda(PAUTA, "instagram") and "#TECHDIM" in video.legenda(PAUTA, "linkedin")


def test_legenda_longa_e_cortada_no_limite_da_rede():
    longa = {**PAUTA, "legenda": "palavra " * 600}
    cortada = video.legenda(longa, "instagram")
    assert len(cortada) <= 2200 and cortada.endswith("…")


# ------------------------------------------------------------------ gerar (manifesto)


@pytest.fixture
def pronto(tmp_path, pautas, arquivo):
    """pasta de pautas + out/ com o MP4 no lugar onde o workflow o deixa."""
    pasta = pautas()
    out = tmp_path / "out"
    destino = out / PAUTA["arquivo"]
    destino.parent.mkdir(parents=True)
    destino.write_bytes(mp4())
    return pasta, out


def test_gerar_monta_o_manifesto_que_o_publicador_le(pronto):
    pasta, out = pronto
    m = video.gerar("v", ["linkedin", "facebook", "instagram"], DIA, out, pasta)
    assert m["theme"] == "video" and m["date"] == DIA.isoformat() and m["fontes"] == []
    assert "gerado por IA" in m["curadoria"]
    assert m["video"]["arquivo"] == PAUTA["arquivo"] and m["video"]["ia"] is True and m["video"]["capa_ms"] == 2500
    assert (m["video"]["largura"], m["video"]["altura"], m["video"]["duracao"]) == (1080, 1920, 10.0)
    assert set(m["networks"]) == {"linkedin", "facebook", "instagram"}
    assert all(d["files"] == [PAUTA["arquivo"]] for d in m["networks"].values())
    assert m["networks"]["facebook"]["comentario"] and not m["networks"]["instagram"]["comentario"]


def test_gerar_so_para_as_redes_pedidas(pronto):
    pasta, out = pronto
    assert list(video.gerar("v", ["linkedin"], DIA, out, pasta)["networks"]) == ["linkedin"]


def test_gerar_recusa_stories_arquivo_ausente_e_video_que_nao_serve(pronto, tmp_path):
    pasta, out = pronto
    with pytest.raises(video.VideoInvalido, match="instagram_stories"):
        video.gerar("v", ["instagram", "instagram_stories"], DIA, out, pasta)
    (out / PAUTA["arquivo"]).unlink()
    with pytest.raises(video.VideoInvalido, match="não encontrado"):
        video.gerar("v", ["linkedin"], DIA, out, pasta)
    (out / PAUTA["arquivo"]).write_bytes(mp4(faststart=False, segundos=120))
    with pytest.raises(video.VideoInvalido) as exc:
        video.gerar("v", ["linkedin", "facebook", "instagram"], DIA, out, pasta)
    texto = str(exc.value)
    assert "facebook" in texto and "instagram" in texto and "linkedin" not in texto   # só quem tem problema aparece


def test_gerar_recusa_capa_depois_do_fim_do_video(pronto, pautas):
    pasta, out = pronto
    pautas("v", {**PAUTA, "capa_ms": 20000})
    with pytest.raises(video.VideoInvalido, match="capa_ms"):
        video.gerar("v", ["linkedin"], DIA, out, pasta)


def test_gerar_sem_ia_nao_marca_o_manifesto(pronto, pautas):
    pasta, out = pronto
    pautas("v", {k: v for k, v in PAUTA.items() if k != "ia"})
    m = video.gerar("v", ["instagram"], DIA, out, pasta)
    assert m["video"]["ia"] is False and "IA" not in m["curadoria"]


# ------------------------------------------------------------------ linha de comando


def test_cli_conferir_mostra_o_veredito_e_o_codigo_de_saida(arquivo, capsys):
    assert video.main(["conferir", str(arquivo())]) == 0
    saida = capsys.readouterr().out
    assert "✓ instagram" in saida and "✓ facebook" in saida and "✓ linkedin" in saida
    assert video.main(["conferir", str(arquivo(faststart=False)), "--redes", "instagram,linkedin"]) == 1
    saida = capsys.readouterr().out
    assert "✗ instagram" in saida and "✓ linkedin" in saida


def test_cli_arquivo_e_erro(monkeypatch, pautas, tmp_path, capsys):
    pasta = pautas()
    monkeypatch.setattr(video.content, "CONTENT_DIR", pasta)
    assert video.main(["arquivo", "v"]) == 0 and capsys.readouterr().out.strip() == PAUTA["arquivo"]
    assert video.main(["arquivo", "nao-existe"]) == 1 and "não encontrada" in capsys.readouterr().err
    ruim = tmp_path / "x.mp4"
    ruim.write_bytes(b"nada")
    assert video.main(["conferir", str(ruim)]) == 1


# ------------------------------------------------------------------ main: generate e publish com vídeo


class Faixa:
    """Substitui os publicadores e guarda o que cada rede recebeu."""

    def __init__(self, monkeypatch):
        self.chamadas = []
        for modulo, nome, ident in (
            (main.linkedin, "publish_video", "urn:li:share:1"),
            (main.facebook, "publish_reel", "fb-video-7"),
            (main.instagram, "publish_reel", "ig-media-9"),
        ):
            monkeypatch.setattr(modulo, nome, self._registra(f"{modulo.__name__.split('.')[-1]}.{nome}", ident))
        for modulo, nome in ((main.linkedin, "publish"), (main.facebook, "publish"), (main.instagram, "publish"),
                             (main.instagram, "publish_story")):
            monkeypatch.setattr(modulo, nome, lambda *a, **k: pytest.fail("vídeo não usa o caminho de imagem"))
        monkeypatch.setattr(main.facebook, "comment", self._registra("facebook.comment", "c1"))
        monkeypatch.setattr(main.facebook, "permalink", lambda c, i: f"https://fb/{i}")
        monkeypatch.setattr(main.instagram, "permalink", lambda c, i: f"https://ig/{i}")

    def _registra(self, nome, ident):
        def f(creds, *args, **kw):
            self.chamadas.append((nome, args, kw))
            return ident
        return f


@pytest.fixture
def execucao(tmp_path, monkeypatch, pronto):
    pasta, out = pronto
    monkeypatch.setattr(main, "OUT", out)
    monkeypatch.setattr(main, "MANIFEST", out / "manifest.json")
    monkeypatch.setattr(main, "RESULTADO", out / "resultado.json")
    monkeypatch.setattr(main.config, "hoje", lambda: DIA)
    monkeypatch.setattr(video.content, "CONTENT_DIR", pasta)
    monkeypatch.setenv("VIDEO", "v")
    return out


def credenciais():
    c = config.Credentials()
    c.meta_token, c.fb_page_id, c.ig_user_id = "tok" * 5, "111", "222"
    c.linkedin_token, c.linkedin_urn = "li" * 20, "urn:li:person:abc"
    return c


def test_generate_de_video_grava_o_manifesto(execucao):
    m = main.generate("video", ["linkedin", "facebook", "instagram"])
    assert json.loads((execucao / "manifest.json").read_text(encoding="utf-8")) == m
    assert m["theme"] == "video" and m["video"]["avisos"] == []


def test_generate_de_video_sem_o_nome_da_pauta_avisa(execucao, monkeypatch):
    monkeypatch.delenv("VIDEO")
    with pytest.raises(video.VideoInvalido, match="nome do vídeo"):
        main.generate("video", ["linkedin"])


def test_publish_de_video_manda_o_mp4_para_cada_rede_sem_precisar_de_url_publica(execucao, monkeypatch):
    faixa = Faixa(monkeypatch)
    main.generate("video", ["linkedin", "facebook", "instagram"])
    assert main.publish(credenciais()) == 0           # ASSET_BASE_URL vazio: vídeo sobe os bytes direto
    por_nome = {nome: (args, kw) for nome, args, kw in faixa.chamadas}
    esperado = execucao / PAUTA["arquivo"]
    args, kw = por_nome["linkedin.publish_video"]
    assert args[1] == esperado and kw["title"] == PAUTA["titulo"] and "inteligência artificial" in args[0]
    args, kw = por_nome["facebook.publish_reel"]
    assert args[1] == esperado and kw["title"] == PAUTA["titulo"]
    args, kw = por_nome["instagram.publish_reel"]
    assert args[1] == esperado and kw == {"ai_generated": True, "thumb_offset_ms": 2500}
    assert por_nome["facebook.comment"][0][1].startswith("🌐")          # primeiro comentário só no Facebook
    resultado = json.loads((execucao / "resultado.json").read_text(encoding="utf-8"))["redes"]
    assert resultado["facebook"] == {"status": "publicado", "id": "fb-video-7", "link": "https://fb/fb-video-7", "comentario": "ok"}
    assert resultado["instagram"]["link"] == "https://ig/ig-media-9" and resultado["linkedin"]["id"] == "urn:li:share:1"


def test_publish_de_video_uma_rede_falhar_nao_derruba_as_outras(execucao, monkeypatch):
    faixa = Faixa(monkeypatch)

    def quebra(*a, **k):
        raise main.PublishError("(#4) Application request limit reached")

    monkeypatch.setattr(main.instagram, "publish_reel", quebra)
    main.generate("video", ["linkedin", "facebook", "instagram"])
    assert main.publish(credenciais()) == 1
    resultado = json.loads((execucao / "resultado.json").read_text(encoding="utf-8"))["redes"]
    assert resultado["instagram"]["status"] == "falhou" and "limit" in resultado["instagram"]["erro"]
    assert resultado["linkedin"]["status"] == resultado["facebook"]["status"] == "publicado"
    assert {n for n, *_ in faixa.chamadas} >= {"linkedin.publish_video", "facebook.publish_reel"}


def test_publish_de_video_rede_sem_credencial_e_pulada(execucao, monkeypatch):
    Faixa(monkeypatch)
    c = credenciais()
    c.meta_token = ""
    main.generate("video", ["linkedin", "facebook", "instagram"])
    assert main.publish(c) == 0
    resultado = json.loads((execucao / "resultado.json").read_text(encoding="utf-8"))["redes"]
    assert resultado["facebook"]["status"] == resultado["instagram"]["status"] == "não configurado"


def test_stories_com_video_e_recusado_no_publicador(execucao, monkeypatch):
    Faixa(monkeypatch)
    main.generate("video", ["linkedin"])
    manifesto = json.loads((execucao / "manifest.json").read_text(encoding="utf-8"))
    manifesto["networks"]["instagram_stories"] = {"caption": "", "comentario": "", "files": [PAUTA["arquivo"]]}
    (execucao / "manifest.json").write_text(json.dumps(manifesto), encoding="utf-8")
    assert main.publish(credenciais()) == 1
    resultado = json.loads((execucao / "resultado.json").read_text(encoding="utf-8"))["redes"]
    assert "ainda não é suportado" in resultado["instagram_stories"]["erro"]


# ------------------------------------------------------------------ diário


def test_diario_mostra_o_video_como_link_e_nao_como_imagem(execucao, tmp_path, monkeypatch):
    Faixa(monkeypatch)
    manifesto = main.generate("video", ["linkedin", "facebook"])
    main.publish(credenciais())
    resultado = json.loads((execucao / "resultado.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(registro.config, "agora", lambda: dt.datetime(2026, 10, 2, 4, 30))
    arquivo = registro.escrever(manifesto, resultado, tmp_path / "assets", run_url="https://exemplo/run/1")
    texto = arquivo.read_text(encoding="utf-8")
    assert "# TECHDIM · Vídeo — Acompanhe a TECHDIM" in texto and "vídeo 1" in texto
    assert f"[vídeo 1](../../{PAUTA['arquivo']})" in texto and "![" not in texto
    assert "gerado por IA" in texto
    indice = json.loads((arquivo.parent / "index.json").read_text(encoding="utf-8"))
    assert indice[0]["tema"] == "video" and indice[0]["redes"]["linkedin"] == "publicado"
    assert registro.redes_publicadas(indice, "video") == {"linkedin", "facebook"}


def test_movimentos_do_diario_descrevem_o_video_e_nao_imagens(execucao, monkeypatch):
    Faixa(monkeypatch)
    manifesto = main.generate("video", ["linkedin"])
    ensaio = main._eventos("video", manifesto, {"redes": {}}, True, "https://exemplo/run/1")
    assert any(e["tipo"] == "ensaio" and e["detalhe"].startswith("vídeo de 10 s (") and "imagem" not in e["detalhe"]
               for e in ensaio)
    main.publish(credenciais())
    resultado = json.loads((execucao / "resultado.json").read_text(encoding="utf-8"))
    eventos = main._eventos("video", manifesto, resultado, False, "https://exemplo/run/1")
    assert {"gerado", "publicado"} <= {e["tipo"] for e in eventos}
    assert next(e for e in eventos if e["tipo"] == "gerado")["detalhe"].startswith("vídeo de 10 s (")
    assert next(e for e in eventos if e["tipo"] == "planejado")["detalhe"].startswith("pauta: Acompanhe a TECHDIM")
