"""Os ajustes feitos para crescer: janela de horário, links rastreáveis e coleta diária."""
from __future__ import annotations

import datetime as dt
import json

import pytest

import config
import links
import main
import metricas_dia

# ------------------------------------------------------------------ janela de horário


@pytest.mark.parametrize("hora,dentro", [(0, False), (6, False), (7, True), (12, True), (21, True), (22, False), (23, False)])
def test_janela_de_publicacao(monkeypatch, hora, dentro):
    quando = dt.datetime(2026, 10, 4, hora, 30)
    assert config.dentro_da_janela(quando) is dentro


def test_publicacao_de_madrugada_e_barrada(monkeypatch, tmp_path):
    """02/10/2026: quatro posts entre 00h22 e 01h11, alcance zero. Não de novo."""
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
    assert metricas_dia.contas(creds)["instagram"]["seguidores"] == 0
    assert metricas_dia.stories(creds, dt.date(2026, 10, 4)) == []


# ------------------------------------------------------------------ grade


def test_todos_os_temas_publicam_story():
    """Story alcança quem já segue e é o único lugar do IG com link clicável."""
    for tema, redes in config.THEME_TARGETS.items():
        assert "instagram_stories" in redes, tema
