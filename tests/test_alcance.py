"""Os ajustes feitos para crescer: janela de horário, links rastreáveis e coleta diária."""
from __future__ import annotations

import csv
import datetime as dt
import json

import pytest
from PIL import Image

import config
import content
import links
import main
import metricas_dia
import render
from texto import cortar

# ------------------------------------------------------------------ janela de horário


@pytest.mark.parametrize("hora,dentro", [(0, False), (6, False), (7, True), (12, True), (21, True), (22, False), (23, False)])
def test_janela_de_publicacao(monkeypatch, hora, dentro):
    quando = dt.datetime(2026, 10, 4, hora, 30)
    assert config.dentro_da_janela(quando) is dentro


def test_publicacao_de_madrugada_e_barrada(monkeypatch, tmp_path):
    """02/10/2026: quatro posts entre 00h22 e 01h11, sem público na rede. Não de novo."""
    monkeypatch.setattr(config, "agora", lambda: dt.datetime(2026, 10, 4, 1, 11))
    monkeypatch.delenv("FORCAR_FORA_DE_HORA", raising=False)
    monkeypatch.setattr(main, "OUT", tmp_path)
    monkeypatch.setattr(main, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(main, "RESULTADO", tmp_path / "resultado.json")
    (tmp_path / "manifest.json").write_text(json.dumps({"theme": "dica", "networks": {}}), "utf-8")

    assert main.publish(config.Credentials()) == 1
    assert "fora da janela" in json.loads((tmp_path / "resultado.json").read_text("utf-8"))["pulado"]


def test_janela_pode_ser_forcada_para_um_teste(monkeypatch):
    monkeypatch.setattr(config, "agora", lambda: dt.datetime(2026, 10, 4, 3, 0))
    monkeypatch.setenv("FORCAR_FORA_DE_HORA", "true")
    assert main._fora_de_hora() == ""


# ------------------------------------------------------------------ links


def test_utm_identifica_rede_tema_e_dia():
    url = links.site("hacker", "facebook", dt.date(2026, 10, 4))
    assert "utm_source=facebook" in url
    assert "utm_content=hacker-2026-10-04" in url


def test_site_sem_tema_nem_rede_fica_limpo():
    assert links.site() == config.SITE_URL


def test_whatsapp_so_existe_com_numero(monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP", "")
    assert links.whatsapp("assunto") == ""
    assert links.contato("facebook", "assunto", "dica").startswith(config.SITE_URL)
    monkeypatch.setattr(config, "WHATSAPP", "5519999998888")
    assert links.contato("facebook", "assunto", "dica").startswith("https://wa.me/")


def test_assunto_gigante_nao_estoura_o_link(monkeypatch):
    monkeypatch.setattr(config, "WHATSAPP", "5519999998888")
    assert len(links.whatsapp("t " * 500)) < 400


# ------------------------------------------------------------------ coleta diária


def test_csv_de_seguidores_acumula_e_nao_duplica_o_dia(tmp_path):
    def foto(seguidores):
        return {"contas": {"instagram": {"seguidores": seguidores, "visitas_ao_perfil": 3,
                                         "cliques_no_site": 1},
                           "facebook": {"seguidores": 10}},
                "stories": [{"id": "1", "alcance": 7, "visualizacoes": 9, "respostas": 1}]}

    metricas_dia.gravar(tmp_path, dt.date(2026, 10, 3), foto(100))
    metricas_dia.gravar(tmp_path, dt.date(2026, 10, 4), foto(104))
    metricas_dia.gravar(tmp_path, dt.date(2026, 10, 4), foto(106))   # recoleta do mesmo dia

    linhas = (tmp_path / "registros" / "seguidores.csv").read_text("utf-8").strip().splitlines()
    assert len(linhas) == 3                      # cabeçalho + dois dias
    assert linhas[-1].split(",")[1] == "106"     # a recoleta substitui, não duplica
    assert (tmp_path / "registros" / "2026-10-04" / "metricas.json").exists()


def test_metricas_sem_credencial_nao_derrubam_o_job(monkeypatch, tmp_path):
    monkeypatch.setattr(metricas_dia, "_get", lambda *a, **k: {})
    creds = config.Credentials()
    object.__setattr__(creds, "ig_user_id", "123")
    object.__setattr__(creds, "fb_page_id", "")
    # API sem resposta = "sem dado" (None), nunca zero: zero falso estraga a curva
    assert metricas_dia.contas(creds)["instagram"]["seguidores"] is None
    assert metricas_dia.stories(creds, dt.date(2026, 10, 4)) == []


def test_dado_ausente_vai_em_branco_no_csv_e_zero_verdadeiro_continua_zero(tmp_path):
    foto = {"contas": {"instagram": {"seguidores": 0, "alcance": None, "visitas_ao_perfil": None,
                                     "cliques_no_site": 0},
                       "facebook": {"seguidores": None}},
            "stories": [{"id": "1", "alcance": None, "seguidores_novos": None},
                        {"id": "2", "alcance": 12, "seguidores_novos": None}]}
    metricas_dia.gravar(tmp_path, dt.date(2026, 10, 4), foto)
    with (tmp_path / "registros" / "seguidores.csv").open(encoding="utf-8", newline="") as fh:
        linha = next(csv.DictReader(fh))
    assert linha["ig_seguidores"] == "0"          # zero verdadeiro
    assert linha["ig_cliques_site"] == "0"
    assert linha["ig_alcance"] == ""              # sem dado
    assert linha["ig_visitas_perfil"] == ""
    assert linha["fb_seguidores"] == ""
    assert linha["stories_alcance"] == "12"       # soma só o que existe
    assert linha["stories_seguidores_novos"] == ""   # nenhum Story trouxe o dado: vazio, não 0


def test_coleta_sem_numero_de_seguidores_falha_de_proposito(monkeypatch, tmp_path):
    """Falha visível (o GitHub avisa) em vez de um buraco silencioso na curva."""
    monkeypatch.setenv("META_ACCESS_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "123")
    monkeypatch.setenv("FB_PAGE_ID", "")
    monkeypatch.setattr(metricas_dia, "_get", lambda *a, **k: {})
    assert metricas_dia.main(["--dest", str(tmp_path)]) == 1
    # o que deu para coletar foi gravado mesmo assim
    assert (tmp_path / "registros" / config.hoje().isoformat() / "metricas.json").exists()


def test_coleta_com_seguidores_termina_bem(monkeypatch, tmp_path):
    monkeypatch.setenv("META_ACCESS_TOKEN", "t")
    monkeypatch.setenv("IG_USER_ID", "123")
    monkeypatch.setenv("FB_PAGE_ID", "")

    def resposta(caminho, token, **params):
        return {"followers_count": 42, "follows_count": 10, "media_count": 5} if "fields" in params else {}

    monkeypatch.setattr(metricas_dia, "_get", resposta)
    assert metricas_dia.main(["--dest", str(tmp_path)]) == 0


def test_relatorio_tolera_metrica_ausente_e_nao_inventa_zero():
    import relatorio
    diarias = [
        {"data": "2026-10-03", "contas": {"instagram": {"seguidores": 10, "alcance": None, "visitas_ao_perfil": None}},
         "stories": [{"alcance": None, "respostas": None, "seguidores_novos": None}]},
        {"data": "2026-10-04", "contas": {"instagram": {"seguidores": 14, "alcance": 50, "visitas_ao_perfil": None}},
         "stories": []},
    ]
    texto = "\n".join(relatorio._bloco_crescimento(diarias))
    assert "| Instagram | 10 | 14 | +4 |" in texto
    assert "alcance da conta **50**" in texto
    assert "visitas ao perfil" not in texto          # nenhuma coleta trouxe: não aparece como 0
    assert "alcance somado: sem dado" in texto


# ------------------------------------------------------------------ grade


def test_todos_os_temas_publicam_story():
    """Story alcança quem já segue e é o único lugar do IG com link clicável."""
    for tema, redes in config.THEME_TARGETS.items():
        assert "instagram_stories" in redes, tema


# ------------------------------------------------------------------ Story

TEXTO_LONGO = ("Cadastros, orçamentos, agendas, painéis e controles sob medida para o seu processo, "
               "sem planilha espalhada e sem retrabalho na equipe, com acesso por perfil ") * 3
PERGUNTA_LONGA = "Qual é o maior problema de TI que a sua empresa enfrenta hoje e que ninguém resolve de verdade?"
RODAPE_DO_STORY = 1640   # a linha do rodapé fica em 1654; daí para baixo só há marca e site


def _rodape(caminho) -> bytes:
    img = Image.open(caminho).convert("RGB")
    return img.crop((0, RODAPE_DO_STORY, img.width, img.height)).tobytes()


@pytest.mark.parametrize("tema", list(config.THEME_LABELS))
def test_story_com_texto_no_limite_nao_invade_a_marca_do_rodape(tmp_path, tema):
    """Regressão: com uma pauta real de serviço o bloco "responde aqui embaixo"
    era desenhado por cima da marca TECHDIM do rodapé.

    O fundo é determinístico por tema e semente, então o rodapé de um Story com
    texto curto e o de um Story com texto no limite têm que ser idênticos pixel a
    pixel. Qualquer texto que invada a faixa, por menor que seja ou por mais
    longe que transborde, faz os dois diferirem.
    """
    curto = content.Post(
        theme=tema, titulo="Título curto", pontos=["a", "b", "c curto"],
        infografico={"pergunta": "Pergunta curta?"},
    )
    longo = content.Post(
        theme=tema,
        titulo=cortar(TEXTO_LONGO, 160),
        pontos=[cortar(TEXTO_LONGO, 260)] * 3,
        fontes=[("fonte-longa.com.br", "https://a.com/x"), ("outra.com", "https://b.com/y")],
        infografico={"pergunta": cortar(PERGUNTA_LONGA, 100)},
    )
    assert _rodape(render.render_story(curto, tmp_path / "curto", seed=7)) == \
           _rodape(render.render_story(longo, tmp_path / "longo", seed=7)), "texto invadiu o rodapé do Story"
