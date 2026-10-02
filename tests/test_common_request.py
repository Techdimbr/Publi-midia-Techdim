"""Retry de rede: repetir o que é seguro, nunca o que pode duplicar uma publicação."""
import pytest
import requests

from publishers import common
from publishers.common import PublishError, request


class Resp:
    def __init__(self, status, texto="", headers=None):
        self.status_code, self.text, self.headers = status, texto, headers or {}


@pytest.fixture
def rede(monkeypatch):
    """Roteiro de respostas/erros; registra chamadas e pausas, sem rede nem espera."""
    class Roteiro:
        passos: list = []
        chamadas = 0
        pausas: list = []

    r = Roteiro()
    r.passos, r.pausas = [], []

    def falso(method, url, **kw):
        r.chamadas += 1
        item = r.passos.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(common.requests, "request", falso)
    monkeypatch.setattr(common.time, "sleep", lambda s: r.pausas.append(s))
    return r


def test_sucesso_direto(rede):
    rede.passos = [Resp(200)]
    assert request("GET", "http://x").status_code == 200
    assert rede.chamadas == 1


def test_leitura_repete_em_erro_de_servidor_e_depois_funciona(rede):
    rede.passos = [Resp(502), Resp(500), Resp(200)]
    assert request("GET", "http://x").status_code == 200
    assert rede.chamadas == 3
    assert rede.pausas == [1, 2]


def test_erro_do_cliente_nao_repete(rede):
    rede.passos = [Resp(400, "ruim")]
    with pytest.raises(PublishError, match="HTTP 400"):
        request("GET", "http://x")
    assert rede.chamadas == 1


def test_publicacao_nao_repete_em_500_para_nao_duplicar(rede):
    rede.passos = [Resp(500, "?"), Resp(200)]
    with pytest.raises(PublishError, match="HTTP 500"):
        request("POST", "http://x", idempotent=False)
    assert rede.chamadas == 1


def test_publicacao_nao_repete_em_timeout_de_leitura(rede):
    rede.passos = [requests.ReadTimeout("lento"), Resp(200)]
    with pytest.raises(PublishError, match="não repeti"):
        request("POST", "http://x", idempotent=False)
    assert rede.chamadas == 1


def test_publicacao_repete_quando_o_servidor_garante_que_nao_processou(rede):
    rede.passos = [Resp(503), Resp(429, headers={"Retry-After": "7"}), Resp(200)]
    assert request("POST", "http://x", idempotent=False).status_code == 200
    assert rede.chamadas == 3
    assert rede.pausas == [1, 7.0]  # respeita o Retry-After


def test_publicacao_repete_quando_nem_conectou(rede):
    rede.passos = [requests.ConnectTimeout("sem rota"), Resp(200)]
    assert request("POST", "http://x", idempotent=False).status_code == 200


def test_esgota_tentativas_com_mensagem_clara(rede):
    rede.passos = [Resp(503)] * 3
    with pytest.raises(PublishError, match="HTTP 503"):
        request("GET", "http://x", attempts=3)
    assert rede.chamadas == 3
    assert len(rede.pausas) == 2  # não dorme depois da última tentativa


def test_retry_after_tem_teto():
    assert common._espera(Resp(429, headers={"Retry-After": "9999"}), 0) == common.ESPERA_MAXIMA
    assert common._espera(Resp(429, headers={"Retry-After": "abc"}), 2) == 4
    assert common._espera(None, 3) == 8


def test_redact_esconde_segredo():
    assert "SEGREDO123456" not in common.redact("erro com SEGREDO123456 no meio", "SEGREDO123456")
    assert common.redact("sem segredo", "curto") == "sem segredo"
