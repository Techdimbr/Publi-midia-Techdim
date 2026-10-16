"""Curadoria por IA: caminho feliz e todos os modos de falha viram CuradoriaIndisponivel."""
import json
from types import SimpleNamespace

import anthropic
import pytest

import curator

CANDIDATOS = [
    {"title": "Falha crítica no roteador X", "link": "https://exemplo.com/a", "source": "exemplo.com", "summary": "resumo", "lang": "pt"},
    {"title": "Promoção de celular", "link": "https://exemplo.com/b", "source": "exemplo.com", "summary": "oferta", "lang": "pt"},
]


def resposta(obj, stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=json.dumps(obj))])


class ClienteFalso:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kw):
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def com_chave(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-teste")
    monkeypatch.setattr(curator, "_texto_da_materia", lambda url, limite=0: "texto da matéria")


def usar(monkeypatch, *respostas):
    monkeypatch.setattr(curator.anthropic, "Anthropic", lambda: ClienteFalso(respostas))


def test_sem_chave_nao_ha_curadoria(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert curator.disponivel() is False
    with pytest.raises(curator.CuradoriaIndisponivel, match="ANTHROPIC_API_KEY"):
        curator.curar("hacker", CANDIDATOS)


def test_caminho_feliz(com_chave, monkeypatch):
    usar(monkeypatch,
         resposta({"indice": 0, "motivo": "afeta empresas"}),
         resposta({"titulo": " Título ", "fatos": ["fato 1", "fato 2", "fato 3"], "recomendacao": "faça X", "fecho": "A TECHDIM ajuda."}))
    post = curator.curar("hacker", CANDIDATOS)
    assert post["titulo"] == "Título" and post["pontos"] == ["fato 1", "fato 2", "faça X"]
    assert post["fonte"] == ("exemplo.com", "https://exemplo.com/a")


def test_nenhuma_manchete_serve(com_chave, monkeypatch):
    usar(monkeypatch, resposta({"indice": -1, "motivo": "só promoção"}))
    with pytest.raises(curator.CuradoriaIndisponivel, match="nenhuma manchete relevante"):
        curator.curar("hacker", CANDIDATOS)


@pytest.mark.parametrize("ruim", [
    resposta({"indice": 0, "motivo": "ok"}, stop="refusal"),
    resposta({"indice": 0, "motivo": "ok"}, stop="max_tokens"),
    SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="isto não é json")]),
])
def test_resposta_ruim_vira_indisponivel(com_chave, monkeypatch, ruim):
    usar(monkeypatch, ruim)
    with pytest.raises(curator.CuradoriaIndisponivel):
        curator.curar("hacker", CANDIDATOS)


def test_post_incompleto_e_recusado(com_chave, monkeypatch):
    usar(monkeypatch, resposta({"indice": 0, "motivo": "ok"}),
         resposta({"titulo": "T", "fatos": ["só um"], "recomendacao": "r", "fecho": "f"}))
    with pytest.raises(curator.CuradoriaIndisponivel, match="incompleto"):
        curator.curar("hacker", CANDIDATOS)


def test_erro_da_api_vira_indisponivel(com_chave, monkeypatch):
    erro = anthropic.APIConnectionError(request=SimpleNamespace(url="x"))
    usar(monkeypatch, erro)
    with pytest.raises(curator.CuradoriaIndisponivel, match="API"):
        curator.curar("hacker", CANDIDATOS)


# ------------------------------------------------------------------ Gemini como segundo provedor


def com_gemini(monkeypatch, *respostas):
    fila = list(respostas)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")
    monkeypatch.setattr(curator, "_texto_da_materia", lambda url, limite=0: "texto da matéria")
    monkeypatch.setattr(curator.gemini, "gerar_json", lambda prompt, esquema, **kw: fila.pop(0))


GEMINI_OK = [{"indice": 0, "motivo": "afeta empresas"},
             {"titulo": " Título ", "fatos": ["fato 1", "fato 2"], "recomendacao": "faça X", "fecho": "A TECHDIM ajuda."}]


def test_sem_chave_da_anthropic_o_gemini_assume(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    com_gemini(monkeypatch, *GEMINI_OK)
    assert curator.disponivel() is True
    post = curator.curar("hacker", CANDIDATOS)
    assert post["provedor"] == "Gemini" and post["titulo"] == "Título" and post["pontos"][-1] == "faça X"


def test_claude_falha_e_o_gemini_assume(com_chave, monkeypatch):
    usar(monkeypatch, anthropic.APIConnectionError(request=SimpleNamespace(url="x")))
    com_gemini(monkeypatch, *GEMINI_OK)
    assert curator.curar("hacker", CANDIDATOS)["provedor"] == "Gemini"


def test_os_dois_provedores_falham_e_a_mensagem_diz_por_que(com_chave, monkeypatch):
    usar(monkeypatch, resposta({"indice": -1, "motivo": "só promoção"}))
    com_gemini(monkeypatch, {"indice": -1, "motivo": "nada serve"})
    with pytest.raises(curator.CuradoriaIndisponivel) as exc:
        curator.curar("hacker", CANDIDATOS)
    assert "Claude:" in str(exc.value) and "Gemini:" in str(exc.value)


def test_erro_do_gemini_vira_indisponivel(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "chave-de-teste")

    def quebra(prompt, esquema, **kw):
        raise curator.gemini.GeminiIndisponivel("sem cota")

    monkeypatch.setattr(curator.gemini, "gerar_json", quebra)
    with pytest.raises(curator.CuradoriaIndisponivel, match="API do Gemini"):
        curator.curar("hacker", CANDIDATOS)
