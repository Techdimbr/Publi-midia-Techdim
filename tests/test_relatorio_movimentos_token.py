"""Relatório semanal, diário de movimentos e checagem de token."""
import datetime as dt
import json
import logging

import pytest

import config
import movimentos
import relatorio
import token_check
from publishers.common import PublishError


def indice_do_dia(pasta, entradas):
    pasta.mkdir(parents=True)
    (pasta / "index.json").write_text(json.dumps(entradas), encoding="utf-8")


def entrada(hora, tema, **extra):
    base = {"hora": hora, "tema": tema, "titulo": f"Título {tema}", "curadoria": "-", "arquivo": "x.md",
            "redes": {"facebook": "publicado", "instagram": "publicado", "instagram_stories": "-", "linkedin": "publicado"},
            "links": {"facebook": "https://fb/1", "instagram": "https://ig/1"},
            "ids": {"facebook": "1_2", "instagram": "99"}, "comentou": ["facebook", "instagram"]}
    base.update(extra)
    return base


@pytest.fixture
def api_falsa(monkeypatch):
    def get(path, token, **params):
        if path.endswith("/insights"):
            valores = {"post_total_media_view_unique": 100, "post_media_view": 150, "post_clicks": 7,
                       "reach": 80, "views": 120, "total_interactions": 20, "likes": 12, "comments": 4, "shares": 2, "saved": 3}
            nomes = params["metric"].split(",")
            return {"data": [{"name": n, "values": [{"value": valores[n]}]} for n in nomes]}
        return {"reactions": {"summary": {"total_count": 10}}, "comments": {"summary": {"total_count": 3}}, "shares": {"count": 1}}

    monkeypatch.setattr(relatorio, "_get", get)
    monkeypatch.setattr(relatorio, "page_token", lambda *a: "pagina")


def test_relatorio_coleta_descontando_o_primeiro_comentario(tmp_path, api_falsa):
    indice_do_dia(tmp_path / "registros" / "2026-10-02", [entrada("08:00", "noticias")])
    c = config.Credentials()
    c.meta_token, c.fb_page_id, c.ig_user_id = "t" * 10, "1", "2"
    linhas = relatorio.coletar(tmp_path, dt.date(2026, 10, 1), dt.date(2026, 10, 3), c)
    fb = next(x for x in linhas if x["rede"] == "facebook")
    ig = next(x for x in linhas if x["rede"] == "instagram")
    assert fb["comentarios"] == 2 and fb["curtidas"] == 10 and fb["alcance"] == 100   # 3 comentários - o da automação
    assert ig["comentarios"] == 3 and ig["interacoes"] == 19                          # 4 - 1 / 20 - 1
    assert len(linhas) == 2                                                           # LinkedIn e Stories não entram


def test_relatorio_escreve_markdown_json_e_indice(tmp_path, api_falsa):
    indice_do_dia(tmp_path / "registros" / "2026-10-02", [entrada("08:00", "noticias"), entrada("11:07", "hacker")])
    c = config.Credentials()
    c.meta_token, c.fb_page_id, c.ig_user_id = "t" * 10, "1", "2"
    inicio, fim = dt.date(2026, 9, 26), dt.date(2026, 10, 2)
    linhas = relatorio.coletar(tmp_path, inicio, fim, c)
    arq = relatorio.escrever(linhas, tmp_path, inicio, fim)
    md = arq.read_text(encoding="utf-8")
    assert "Qual tema traz mais retorno" in md and "Notícias de Tecnologia" in md and "Melhores posts" in md
    dados = json.loads(arq.with_suffix(".json").read_text(encoding="utf-8"))
    assert len(dados["posts"]) == 4
    assert arq.name in (arq.parent / "README.md").read_text(encoding="utf-8")


def test_relatorio_sem_posts_diz_isso(tmp_path):
    inicio, fim = dt.date(2026, 9, 26), dt.date(2026, 10, 2)
    md = relatorio.escrever([], tmp_path, inicio, fim).read_text(encoding="utf-8")
    assert "Nenhum post registrado" in md


def test_taxa_de_engajamento():
    assert relatorio._taxa(5, 100) == "5.0%"
    assert relatorio._taxa(5, 0) == "—"


# ------------------------------------------------------------------ movimentos


def test_movimentos_registra_ordena_e_redige(tmp_path):
    token = "EAAGm0PX4ZCpsBO" + "A" * 40
    movimentos.registrar(tmp_path, [
        {"tipo": "publicado", "detalhe": f"post ok {token}", "tema": "hacker", "rede": "facebook", "link": "https://fb/1"},
        {"tipo": "falhou", "detalhe": "a | b", "teste": True},
    ], dia="2026-10-02")
    pasta = tmp_path / "registros" / "2026-10-02"
    linhas = [json.loads(x) for x in (pasta / "movimentos.jsonl").read_text().splitlines()]
    assert len(linhas) == 2 and token not in json.dumps(linhas) and "[REDIGIDO]" in linhas[0]["detalhe"]
    md = (pasta / "movimentos.md").read_text(encoding="utf-8")
    assert "✅ publicado" in md and "❌ falhou" in md and "🧪" in md
    assert "a / b" in md   # a barra vertical não quebra a tabela


def test_movimentos_acumula_entre_execucoes(tmp_path):
    for i in range(3):
        movimentos.registrar(tmp_path, [{"tipo": "observacao", "detalhe": f"nota {i}"}], dia="2026-10-02")
    md = (tmp_path / "registros" / "2026-10-02" / "movimentos.md").read_text(encoding="utf-8")
    assert md.count("nota ") == 3


def test_movimentos_cli(tmp_path):
    assert movimentos.main(["--dest", str(tmp_path), "--tipo", "comentou", "--detalhe", "respondi um comentário", "--teste"]) == 0
    dia = config.hoje().isoformat()
    assert "respondi" in (tmp_path / "registros" / dia / "movimentos.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ token da Meta


class Resp:
    def __init__(self, dados):
        self._d = dados

    def json(self):
        return {"data": self._d}


def checar(monkeypatch, dados, caplog):
    monkeypatch.setattr(token_check, "request", lambda *a, **k: Resp(dados))
    c = config.Credentials()
    c.meta_token = "t" * 20
    with caplog.at_level(logging.INFO):
        return token_check.check(c)


def test_token_sem_validade_passa(monkeypatch, caplog):
    dados = {"is_valid": True, "type": "USER", "scopes": ["pages_manage_posts", "pages_read_engagement", "instagram_content_publish"]}
    assert checar(monkeypatch, dados, caplog) == 0


def test_token_perto_de_expirar_falha_de_proposito(monkeypatch, caplog):
    expira = int((dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=5)).timestamp())
    assert checar(monkeypatch, {"is_valid": True, "type": "USER", "expires_at": expira, "scopes": []}, caplog) == 3


def test_token_invalido_e_codigo_2(monkeypatch, caplog):
    assert checar(monkeypatch, {"is_valid": False, "error": {"message": "expirou"}}, caplog) == 2


def test_token_ausente(monkeypatch):
    monkeypatch.delenv("META_ACCESS_TOKEN", raising=False)
    assert token_check.check(config.Credentials()) == 1


def test_erro_de_rede_na_checagem_sobe_como_publisherror(monkeypatch):
    def quebra(*a, **k):
        raise PublishError("sem rede")

    monkeypatch.setattr(token_check, "request", quebra)
    c = config.Credentials()
    c.meta_token = "t" * 20
    with pytest.raises(PublishError):
        token_check.check(c)
