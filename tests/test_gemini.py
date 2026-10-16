"""Cliente do Gemini: pedido, troca de modelo, erros transitórios e a chave que nunca vaza."""
import copy
import json

import pytest

import gemini

CHAVE = "AQ.chave-secreta-de-teste"
RESPOSTA_OK = {"titulo": "ok"}


class Resp:
    def __init__(self, status=200, corpo=None, texto=""):
        self.status_code = status
        self._corpo = corpo if corpo is not None else {}
        self.text = texto or json.dumps(self._corpo)

    def json(self):
        return self._corpo


def candidato(texto, fim="STOP"):
    return {"candidates": [{"finishReason": fim, "content": {"parts": [{"text": texto}]}}]}


@pytest.fixture
def api(monkeypatch):
    """Troca requests.post: cada chamada consome a próxima resposta da fila e fica registrada."""
    monkeypatch.setenv("GEMINI_API_KEY", CHAVE)
    monkeypatch.setattr(gemini.time, "sleep", lambda s: None)

    class Falso:
        fila: list = []
        chamadas: list = []

    def post(url, headers=None, json=None, timeout=None):
        Falso.chamadas.append({"url": url, "headers": headers, "corpo": copy.deepcopy(json)})
        r = Falso.fila.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    Falso.fila, Falso.chamadas = [], []
    monkeypatch.setattr(gemini.requests, "post", post)
    return Falso


def test_sem_chave_nao_ha_gemini():
    assert gemini.disponivel() is False
    with pytest.raises(gemini.GeminiIndisponivel, match="GEMINI_API_KEY"):
        gemini.gerar_json("oi", {"type": "object"})


def test_pedido_leva_chave_no_cabecalho_esquema_limpo_e_raciocinio_limitado(api):
    api.fila = [Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))]
    esquema = {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "object", "additionalProperties": False}}}
    assert gemini.gerar_json("escreva", esquema, sistema="regras") == RESPOSTA_OK
    c = api.chamadas[0]
    assert c["url"].endswith("/models/gemini-2.5-flash:generateContent")
    assert c["headers"]["x-goog-api-key"] == CHAVE and CHAVE not in c["url"]
    cfg = c["corpo"]["generationConfig"]
    assert cfg["responseMimeType"] == "application/json" and "additionalProperties" not in json.dumps(cfg["responseSchema"])
    assert cfg["thinkingConfig"] == {"thinkingBudget": gemini.PENSAMENTO}
    assert c["corpo"]["systemInstruction"]["parts"][0]["text"] == "regras"
    assert gemini.ultimo_modelo() == "gemini-2.5-flash" and gemini.chamadas_usadas() == 1


def test_modelo_sem_raciocinio_configuravel_nao_recebe_o_campo(api, monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    api.fila = [Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))]
    gemini.gerar_json("x", {"type": "object"})
    assert "thinkingConfig" not in api.chamadas[0]["corpo"]["generationConfig"]


def test_sobrecarga_503_repete_e_depois_troca_de_modelo_sem_gastar_cota(api):
    api.fila = [Resp(503, texto="alta demanda"), Resp(503, texto="alta demanda"),
                Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))]
    assert gemini.gerar_json("x", {"type": "object"}) == RESPOSTA_OK
    modelos = [c["url"].split("/models/")[1].split(":")[0] for c in api.chamadas]
    assert modelos == ["gemini-2.5-flash", "gemini-2.5-flash", "gemini-flash-lite-latest"]
    assert gemini.chamadas_usadas() == 1   # os 503 não contam como chamada com cota


def test_cota_esgotada_429_vai_direto_ao_proximo_modelo(api):
    api.fila = [Resp(429, texto="quota"), Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))]
    gemini.gerar_json("x", {"type": "object"})
    assert [c["url"].split("/models/")[1].split(":")[0] for c in api.chamadas] == ["gemini-2.5-flash", "gemini-flash-lite-latest"]


def test_resposta_cortada_repete_o_mesmo_modelo_sem_raciocinio(api):
    api.fila = [Resp(corpo=candidato("{", fim="MAX_TOKENS")), Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))]
    assert gemini.gerar_json("x", {"type": "object"}) == RESPOSTA_OK
    assert [c["corpo"]["generationConfig"]["thinkingConfig"]["thinkingBudget"] for c in api.chamadas] == [gemini.PENSAMENTO, 0]
    assert {c["url"] for c in api.chamadas} == {api.chamadas[0]["url"]}


def test_chave_recusada_para_na_hora_e_nunca_aparece_na_mensagem(api):
    api.fila = [Resp(403, corpo={"error": {"message": f"API key {CHAVE} not valid"}})]
    with pytest.raises(gemini.GeminiIndisponivel) as exc:
        gemini.gerar_json("x", {"type": "object"})
    assert CHAVE not in str(exc.value) and "***" in str(exc.value) and len(api.chamadas) == 1


def test_pedido_invalido_400_nao_insiste(api):
    api.fila = [Resp(400, corpo={"error": {"message": "schema inválido"}})]
    with pytest.raises(gemini.GeminiIndisponivel, match="recusado"):
        gemini.gerar_json("x", {"type": "object"})
    assert len(api.chamadas) == 1


def test_json_dentro_de_bloco_de_codigo_e_aceito_e_lixo_nao(api):
    api.fila = [Resp(corpo=candidato("```json\n{\"a\": 1}\n```"))]
    assert gemini.gerar_json("x", {"type": "object"}) == {"a": 1}
    api.fila = [Resp(corpo=candidato("isto não é json"))] * 8
    with pytest.raises(gemini.GeminiIndisponivel, match="nenhum modelo respondeu"):
        gemini.gerar_json("x", {"type": "object"})


def test_resposta_sem_candidato_ou_bloqueada_passa_ao_proximo_modelo(api):
    api.fila = [Resp(corpo={"promptFeedback": {"blockReason": "SAFETY"}}), Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))]
    assert gemini.gerar_json("x", {"type": "object"}) == RESPOSTA_OK


def test_teto_de_chamadas_por_execucao(api, monkeypatch):
    monkeypatch.setenv("GEMINI_MAX_CHAMADAS", "2")
    api.fila = [Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))] * 3
    gemini.gerar_json("x", {"type": "object"})
    gemini.gerar_json("x", {"type": "object"})
    with pytest.raises(gemini.GeminiIndisponivel, match="limite de chamadas"):
        gemini.gerar_json("y", {"type": "object"})


def test_modelo_sem_cota_nao_e_tentado_de_novo_na_mesma_execucao(api):
    api.fila = [Resp(429, texto="quota"), Resp(corpo=candidato(json.dumps(RESPOSTA_OK))), Resp(corpo=candidato(json.dumps(RESPOSTA_OK)))]
    gemini.gerar_json("x", {"type": "object"})
    gemini.gerar_json("y", {"type": "object"})
    modelos = [c["url"].split("/models/")[1].split(":")[0] for c in api.chamadas]
    assert modelos == ["gemini-2.5-flash", "gemini-flash-lite-latest", "gemini-flash-lite-latest"]
