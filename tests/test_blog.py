"""Blog do site: a pauta do dia vira um post estático, índice, feed e sitemap."""
import json
import pathlib
import xml.dom.minidom

import blog

PAUTA = {
    "titulo": "Título <b>do dia</b>",
    "pontos": ["um", "dois", "três"],
    "fecho": "fecho",
    "motivo": "porque sim",
    "fontes": [["exemplo.com", "https://exemplo.com/a?x=1&y=2"]],
    "infografico": {
        "licoes": [["Passo A", "faça A"], ["Passo B", "faça B"], ["Passo C", "faça C"]],
        "hashtags": ["#Tema", "#TI", "#TECHDIM"],
    },
}


def monta_site(tmp_path: pathlib.Path, monkeypatch, data="2026-10-07"):
    diario = tmp_path / "diario"
    (diario / data).mkdir(parents=True)
    for tema in ("noticias", "hacker", "dica", "servico"):
        corpo = dict(PAUTA, fontes=[] if tema == "servico" else PAUTA["fontes"])
        (diario / data / f"{tema}.json").write_text(json.dumps(corpo), encoding="utf-8")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text("<html></html>", encoding="utf-8")
    (site / "sitemap.xml").write_text(
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
        encoding="utf-8")
    monkeypatch.setattr(blog, "DIARIO", diario)
    return site


def test_gera_post_indice_feed_e_sitemap(tmp_path, monkeypatch):
    site = monta_site(tmp_path, monkeypatch)
    assert blog.gerar(site, ["2026-10-07"]) == ["2026-10-07"]
    post = (site / "blog" / "2026-10-07" / "index.html").read_text(encoding="utf-8")
    assert "Radar TECHDIM · 07/10/2026" in post
    assert "Título &lt;b&gt;do dia&lt;/b&gt;" in post and "<b>do dia</b>" not in post  # escapa HTML
    assert "https://exemplo.com/a?x=1&amp;y=2" in post
    assert "Fale com a TECHDIM" in post  # serviço do dia presente
    assert "blog/2026-10-07/" in (site / "blog" / "feed.xml").read_text(encoding="utf-8")
    assert 'href="2026-10-07/"' in (site / "blog" / "index.html").read_text(encoding="utf-8")
    xml.dom.minidom.parse(str(site / "blog" / "feed.xml"))
    xml.dom.minidom.parse(str(site / "sitemap.xml"))


def test_rodar_de_novo_nao_duplica_sitemap_nem_posts(tmp_path, monkeypatch):
    site = monta_site(tmp_path, monkeypatch)
    blog.gerar(site, ["2026-10-07"])
    primeiro = (site / "sitemap.xml").read_text(encoding="utf-8")
    blog.gerar(site, ["2026-10-07"])
    assert (site / "sitemap.xml").read_text(encoding="utf-8") == primeiro
    assert primeiro.count("/blog/2026-10-07/") == 1


def test_dias_disponiveis_ignora_pastas_sem_pauta(tmp_path, monkeypatch):
    monta_site(tmp_path, monkeypatch)
    (blog.DIARIO / "2026-10-08").mkdir()
    (blog.DIARIO / "rascunho").mkdir()
    assert blog.dias_disponiveis() == ["2026-10-07"]


def test_garante_link_do_blog_no_menu_uma_vez(tmp_path, monkeypatch):
    site = monta_site(tmp_path, monkeypatch)
    (site / "index.html").write_text(
        '          <li><a href="#sobre" class="nav-link">Sobre Nós</a></li>\n'
        '          <li><a href="#faq">Perguntas Frequentes</a></li>\n', encoding="utf-8")
    assert blog.garantir_menu(site) is True
    assert blog.garantir_menu(site) is False
    html = (site / "index.html").read_text(encoding="utf-8")
    assert html.count('href="blog/" class="nav-link"') == 1
    assert html.count('href="blog/">Blog') == 1
