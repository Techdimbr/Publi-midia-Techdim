"""Aviso aos buscadores (IndexNow): chave, páginas do commit, envio e espera."""
import json
import subprocess

import indexnow

CHAVE = "0123456789abcdef0123456789abcdef"


def site_com_git(tmp_path):
    site = tmp_path / "site"
    (site / "blog" / "2026-10-07" / "artigo").mkdir(parents=True)
    (site / "blog" / "2026-10-07" / "artigo" / "capa.jpg").write_bytes(b"x")
    (site / "blog" / "2026-10-07" / "artigo" / "index.html").write_text("a", encoding="utf-8")
    (site / "blog" / "index.html").write_text("i", encoding="utf-8")
    (site / "index.html").write_text("home", encoding="utf-8")
    (site / "blog" / "feed.xml").write_text("<rss/>", encoding="utf-8")
    (site / "styles.css").write_text("", encoding="utf-8")

    def git(*args):
        subprocess.run(["git", "-C", str(site), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                       check=True, capture_output=True)

    git("init", "-q")
    git("add", ".")
    git("commit", "-q", "-m", "um")
    (site / "blog" / "2026-10-08").mkdir()
    (site / "blog" / "2026-10-08" / "index.html").write_text("novo", encoding="utf-8")
    (site / "index.html").write_text("home v2", encoding="utf-8")
    (site / "styles.css").write_text("a{}", encoding="utf-8")
    (site / "blog" / "feed.xml").write_text("<rss>2</rss>", encoding="utf-8")
    git("add", ".")
    git("commit", "-q", "-m", "dois")
    return site


def test_url_da_pagina_so_para_html_do_site():
    base = indexnow.BASE_URL
    assert indexnow.url_da_pagina("index.html") == f"{base}/"
    assert indexnow.url_da_pagina("blog/index.html") == f"{base}/blog/"
    assert indexnow.url_da_pagina("blog/2026-10-07/x/index.html") == f"{base}/blog/2026-10-07/x/"
    for ignorado in ("blog/feed.xml", "blog/2026-10-07/x/capa.jpg", "styles.css", "docs/index.html"):
        assert indexnow.url_da_pagina(ignorado) is None


def test_urls_do_commit_trazem_so_paginas_novas_ou_alteradas(tmp_path):
    site = site_com_git(tmp_path)
    assert indexnow.urls_do_commit(site) == [
        f"{indexnow.BASE_URL}/",
        f"{indexnow.BASE_URL}/blog/2026-10-08/",
    ]
    assert f"{indexnow.BASE_URL}/blog/2026-10-07/artigo/" in indexnow.urls_do_commit(site, "HEAD~1")


def test_chave_vem_do_seo_json_ou_de_um_arquivo_com_o_mesmo_texto(tmp_path):
    site = tmp_path / "s"
    site.mkdir()
    assert indexnow.achar_chave(site) is None
    (site / "robots.txt").write_text("User-agent: *", encoding="utf-8")  # nome curto: nunca é chave
    (site / f"{CHAVE}.txt").write_text(CHAVE + "\n", encoding="utf-8")
    assert indexnow.achar_chave(site) == CHAVE
    (site / f"{CHAVE}.txt").write_text("outra coisa", encoding="utf-8")
    assert indexnow.achar_chave(site) is None
    (site / "seo.json").write_text(json.dumps({"indexnow_key": CHAVE}), encoding="utf-8")
    assert indexnow.achar_chave(site) == CHAVE


def test_urls_do_sitemap_ignoram_outros_dominios(tmp_path):
    site = tmp_path / "s"
    site.mkdir()
    (site / "sitemap.xml").write_text(
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{indexnow.BASE_URL}/blog/</loc></url>"
        "<url><loc>https://www.techdim.com.br/</loc></url></urlset>", encoding="utf-8")
    assert indexnow.urls_do_sitemap(site) == [f"{indexnow.BASE_URL}/blog/"]


def test_corpo_do_envio_segue_o_protocolo():
    corpo = indexnow.corpo_do_envio([f"{indexnow.BASE_URL}/blog/"], CHAVE)
    assert corpo == {
        "host": "techdimbr.github.io", "key": CHAVE,
        "keyLocation": f"https://techdimbr.github.io/techdimbr/{CHAVE}.txt",
        "urlList": [f"{indexnow.BASE_URL}/blog/"],
    }


class Resposta:
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_enviar_em_lotes_e_aceita_200_e_202(monkeypatch):
    pedidos = []

    def falso(pedido, timeout):
        pedidos.append(json.loads(pedido.data))
        return Resposta(202)

    monkeypatch.setattr(indexnow.urllib.request, "urlopen", falso)
    monkeypatch.setattr(indexnow, "LIMITE_POR_ENVIO", 2)
    urls = [f"{indexnow.BASE_URL}/blog/{i}/" for i in range(5)]
    assert indexnow.enviar(urls, CHAVE) == 200
    assert [len(p["urlList"]) for p in pedidos] == [2, 2, 1]


def test_enviar_devolve_o_codigo_de_erro(monkeypatch):
    def falso(pedido, timeout):
        raise indexnow.urllib.error.HTTPError(pedido.full_url, 403, "key", {}, None)

    monkeypatch.setattr(indexnow.urllib.request, "urlopen", falso)
    assert indexnow.enviar([f"{indexnow.BASE_URL}/"], CHAVE) == 403


def test_esperar_no_ar_tenta_de_novo_ate_publicar(monkeypatch):
    respostas = iter([False, False, True])
    monkeypatch.setattr(indexnow, "esta_no_ar", lambda url, timeout=15: next(respostas))
    monkeypatch.setattr(indexnow.time, "sleep", lambda s: None)
    assert indexnow.esperar_no_ar(["https://x/"], tentativas=5, intervalo=1) is True
    monkeypatch.setattr(indexnow, "esta_no_ar", lambda url, timeout=15: False)
    assert indexnow.esperar_no_ar(["https://x/"], tentativas=3, intervalo=1) is False


def test_cli_simular_nao_envia_nada(tmp_path, monkeypatch, capsys):
    site = site_com_git(tmp_path)
    (site / f"{CHAVE}.txt").write_text(CHAVE, encoding="utf-8")
    monkeypatch.setattr(indexnow.sys, "argv", ["indexnow", "--site", str(site), "--simular"])
    monkeypatch.setattr(indexnow, "enviar", lambda *a, **k: (_ for _ in ()).throw(AssertionError("não deveria enviar")))
    assert indexnow.main() == 0
    assert CHAVE in capsys.readouterr().out
