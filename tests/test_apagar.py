"""Exclusão de posts: só vale como "apagou" se o post sumiu de verdade."""
import pytest

import apagar
from publishers.common import PublishError


class Creds:
    meta_token, fb_page_id, linkedin_token = "t" * 10, "1", "l" * 10


@pytest.fixture
def api(monkeypatch):
    chamadas = []
    estado = {"get": PublishError("GET x -> HTTP 400: Object with ID does not exist", )}

    def falso(method, url, **kw):
        chamadas.append(method)
        if method == "GET":
            if isinstance(estado["get"], Exception):
                raise estado["get"]
            return estado["get"]
        return object()

    monkeypatch.setattr(apagar, "request", falso)
    monkeypatch.setattr(apagar, "page_token", lambda *a: "pagina")
    return chamadas, estado


def test_apagou_e_sumiu(api):
    apagar.apagar(Creds(), "instagram", "123")   # GET devolve "não existe" -> ok
    assert api[0] == ["DELETE", "GET"]


def test_delete_aceito_mas_post_continua_e_falha(api):
    api[1]["get"] = object()   # GET respondeu 200: o post ainda existe
    with pytest.raises(PublishError, match="continua visível"):
        apagar.apagar(Creds(), "instagram", "123")


def test_linkedin_404_conta_como_apagado(api):
    api[1]["get"] = PublishError("GET x -> HTTP 404: not found")
    apagar.apagar(Creds(), "linkedin", "urn:li:share:1")


def test_nao_deu_para_conferir_nao_derruba(api, caplog):
    api[1]["get"] = PublishError("GET x -> HTTP 500: erro")
    apagar.apagar(Creds(), "facebook", "1_2")
    assert "não consegui confirmar" in caplog.text


def test_rede_desconhecida():
    with pytest.raises(PublishError, match="desconhecida"):
        apagar.apagar(Creds(), "tiktok", "1")
