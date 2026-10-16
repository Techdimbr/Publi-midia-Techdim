"""Radar de contas: lista de alvos, consulta à Business Discovery, classificação dos erros e relatório."""
import datetime as dt
import json
from dataclasses import dataclass

import pytest

import radar
from publishers.common import PublishError

AGORA = dt.datetime(2026, 10, 16, 12, 0, tzinfo=dt.timezone.utc)


@dataclass
class Creds:
    meta_token: str = "tok"
    fb_page_id: str = "10"
    ig_user_id: str = "20"
    has_facebook: bool = True
    has_instagram: bool = True


class Resposta:
    def __init__(self, corpo):
        self._corpo = corpo

    def json(self):
        return self._corpo


@pytest.fixture(autouse=True)
def sem_rede(monkeypatch):
    monkeypatch.setattr(radar.time, "sleep", lambda s: None)
    monkeypatch.setattr(radar.instagram, "_token", lambda creds: "tok-ig")
    monkeypatch.setattr(radar, "page_token", lambda tok, pagina: "tok-fb")


def conta(handle="acme", seguidores=1000, **extra):
    return {"username": handle, "name": handle.title(), "followers_count": seguidores, "media_count": 50,
            "biography": "linha 1\nlinha 2", "website": "https://acme.example",
            "media": {"data": [
                {"timestamp": "2026-10-15T09:00:00+0000", "like_count": 10},
                {"timestamp": "2026-10-10T09:00:00+0000", "like_count": 20},
                {"timestamp": "2026-10-01T09:00:00+0000"},   # curtidas escondidas: fica fora da média
            ]}, **extra}


# ------------------------------------------------------------------ a lista de alvos


def test_lista_de_alvos_e_valida_e_tem_folga_para_os_100():
    lista = radar.carregar_lista()
    globais = [i for i in lista if i["grupo"] == "global"]
    assert len(globais) >= 150   # a API descarta handles errados e contas pessoais: a lista precisa de folga
    assert {i["grupo"] for i in lista} <= set(radar.GRUPOS)


def test_carregar_lista_recusa_handle_invalido_repetido_e_item_incompleto(tmp_path):
    def lista(*itens):
        caminho = tmp_path / "l.json"
        caminho.write_text(json.dumps(itens), encoding="utf-8")
        return caminho

    base = {"handle": "ok.conta", "nome": "Ok", "grupo": "global", "categoria": "x"}
    assert radar.carregar_lista(lista(base)) == [base]
    with pytest.raises(ValueError, match="inválido"):
        radar.carregar_lista(lista({**base, "handle": "@Com Arroba"}))
    with pytest.raises(ValueError, match="repetido"):
        radar.carregar_lista(lista(base, base))
    with pytest.raises(ValueError, match="incompleto"):
        radar.carregar_lista(lista({**base, "grupo": "marte"}))


# ------------------------------------------------------------------ a consulta


def test_consultar_pede_a_conta_pelo_username_com_o_token_do_instagram(monkeypatch):
    chamadas = []

    def falso(metodo, url, **kw):
        chamadas.append((metodo, url, kw["params"]))
        return Resposta({"business_discovery": conta("openai")})

    monkeypatch.setattr(radar, "request", falso)
    assert radar.consultar(Creds(), "openai")["username"] == "openai"
    metodo, url, params = chamadas[0]
    assert metodo == "GET" and url.endswith("/20")
    assert params["access_token"] == "tok-ig"
    assert params["fields"].startswith("business_discovery.username(openai){username,name,")
    assert "media.limit(6){timestamp,like_count,comments_count}" in params["fields"]


def test_resumir_pega_o_ultimo_post_a_media_de_curtidas_e_diz_se_esta_ativa():
    r = radar.resumir("acme", conta("acme", 1234), AGORA)
    assert r["handle"] == "acme" and r["seguidores"] == 1234 and r["bio"] == "linha 1 linha 2"
    assert r["ultimo_post"] == "2026-10-15" and r["dias_sem_postar"] == 1 and r["ativa"] is True
    assert r["curtidas_medias"] == 15
    parada = radar.resumir("velha", {"username": "velha", "media": {"data": [{"timestamp": "2026-01-01T00:00:00+0000"}]}}, AGORA)
    assert parada["ativa"] is False and parada["curtidas_medias"] is None
    sem_posts = radar.resumir("nova", {"username": "nova"}, AGORA)
    assert sem_posts["ultimo_post"] == "" and sem_posts["dias_sem_postar"] is None and sem_posts["ativa"] is False


# ------------------------------------------------------------------ a validação


def erro(corpo: str, status=400) -> PublishError:
    return PublishError(f"GET x -> HTTP {status}: {corpo}")


def test_validar_classifica_ok_inexistente_e_erro_e_para_no_limite_de_uso(monkeypatch):
    respostas = {
        "boa": conta("boa", 500),
        "errada": erro('{"error":{"message":"Invalid user id","type":"OAuthException","code":110}}'),
        "pessoal": erro('{"error":{"message":"(#100) Unsupported get request","code":100}}'),
        "vazia": None,
        "quebrada": erro("falha", status=500),
        "limite": erro('{"error":{"message":"Application request limit reached","code":4,"error_subcode":1349193}}'),
        "depois": conta("depois"),
    }

    def falso(metodo, url, **kw):
        handle = kw["params"]["fields"].split("username(")[1].split(")")[0]
        valor = respostas[handle]
        if isinstance(valor, PublishError):
            raise valor
        return Resposta({"business_discovery": valor} if valor else {})

    monkeypatch.setattr(radar, "request", falso)
    lista = [{"handle": h, "nome": h, "grupo": "global", "categoria": "c"} for h in respostas]
    sit = {r["handle"]: r["situacao"] for r in radar.validar(Creds(), lista, agora=AGORA)}
    assert sit == {"boa": "ok", "errada": "não encontrada", "pessoal": "não encontrada", "vazia": "não encontrada",
                   "quebrada": "erro", "limite": "limite", "depois": "não consultada (limite de uso da API)"}


def test_relatorio_ordena_por_seguidores_e_lista_o_que_nao_foi_conferido():
    ok = lambda h, s, ativa=True: {"handle": h, "nome": h, "grupo": "global", "categoria": "IA", "situacao": "ok",  # noqa: E731
                                   "nome_na_conta": h.upper(), "seguidores": s, "ultimo_post": "2026-10-15", "ativa": ativa}
    resultados = [ok("pequena", 10), ok("grande", 9000, ativa=False), ok("media", 500),
                  {"handle": "sumiu", "nome": "Sumiu", "grupo": "global", "categoria": "IA", "situacao": "não encontrada"}]
    md = radar.relatorio_md(resultados, "2026-10-16")
    assert md.index("@grande") < md.index("@media") < md.index("@pequena")
    assert "3 de 4 contas conferidas" in md and "- @sumiu (Sumiu): não encontrada" in md
    assert "| @grande | GRANDE | 9000 | 2026-10-15 | não |" in md


# ------------------------------------------------------------------ o diagnóstico


def test_diagnostico_le_campo_a_campo_e_anota_o_que_a_api_recusou(monkeypatch):
    def falso(metodo, url, **kw):
        campo = kw["params"]["fields"]
        if campo == "hours":
            raise erro('{"error":{"message":"(#10) permissão","code":10}}')
        return Resposta({campo: {"about": "Texto da página", "name": "Techdim", "emails": ["a@b.c"]}.get(campo, "")})

    monkeypatch.setattr(radar, "request", falso)
    d = radar.diagnostico(Creds())
    assert d["facebook"]["campos"] == {"name": "Techdim", "about": "Texto da página", "emails": ["a@b.c"]}
    assert d["facebook"]["indisponiveis"] == ["hours"]
    assert d["instagram"]["campos"] == {"name": "Techdim"}


def test_main_grava_o_resultado_no_destino_e_falha_sem_nenhuma_conta_ok(monkeypatch, tmp_path, capsys):
    lista = tmp_path / "l.json"
    lista.write_text(json.dumps([{"handle": "acme", "nome": "Acme", "grupo": "global", "categoria": "c"}]), encoding="utf-8")
    monkeypatch.setattr(radar.config, "Credentials", Creds)
    monkeypatch.setattr(radar, "request", lambda *a, **kw: Resposta({"business_discovery": conta("acme")}))
    assert radar.main(["--dest", str(tmp_path), "--acao", "validar-lista", "--lista", str(lista)]) == 0
    arquivos = sorted(p.name for p in (tmp_path / "registros" / "radar").iterdir())
    assert len(arquivos) == 2 and arquivos[0].startswith("radar-l-") and arquivos[0].endswith(".json")
    assert "validação: 1 ok" in capsys.readouterr().out

    monkeypatch.setattr(radar, "request", lambda *a, **kw: (_ for _ in ()).throw(erro("falha", status=500)))
    assert radar.main(["--dest", str(tmp_path), "--acao", "validar-lista", "--lista", str(lista)]) == 1
