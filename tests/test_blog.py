"""Blog do site: a pauta do dia vira artigos estáticos com SEO, índice, arquivo, feed e sitemap."""
import hashlib
import json
import pathlib
import xml.dom.minidom
from html.parser import HTMLParser

import pytest

import blog

PAUTA = {
    "titulo": "Título <b>do dia</b> com CVE-2026-1 e mais palavras para passar de cinquenta e dois",
    "pontos": ["um ponto importante", "dois", "três"],
    "fecho": "fecho do dia",
    "motivo": "porque sim",
    "fontes": [["exemplo.com", "https://exemplo.com/a?x=1&y=2"]],
    "infografico": {
        "titulo_branco": "Branco", "titulo_destaque": "destaque",
        "historia": "A história do dia em uma frase.",
        "licoes": [["Passo A", "faça A"], ["Passo B", "faça B"], ["Passo C", "faça C"]],
        "hashtags": ["#Tema", "#TI", "#TECHDIM"],
    },
}

INDEX_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>Site</title>
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="https://techdimbr.github.io/" />
  <meta property="og:url" content="https://techdimbr.github.io/" />
  <meta property="og:image" content="assets/techdim-preview.jpg" />
  <meta property="twitter:url" content="https://techdimbr.github.io/" />
  <meta property="twitter:image" content="assets/techdim-preview.jpg" />
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "ProfessionalService",
    "name": "Empresa",
    "founder": {"@type": "Person", "name": "Fulano"}
  }
  </script>
</head>
<body>
  <main>
    <!-- ==========================================================================
         Contact & Conversion Section
         ========================================================================== -->
    <section class="contact-section" id="contato"></section>
  </main>
</body>
</html>
"""

SITEMAP_ANTIGO = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://www.techdim.com.br/</loc><lastmod>2026-07-31</lastmod></url>
  <url><loc>https://www.techdim.com.br/servicos</loc></url>
  <url><loc>https://techdimbr.github.io/techdimbr/sobre/</loc><lastmod>2026-08-01</lastmod></url>
  <url><loc>https://techdimbr.github.io/techdimbr/blog/velho/</loc></url>
</urlset>
"""


def capa_falsa(data, tema, destino):
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(b"jpg")
    return True


def monta(tmp_path, monkeypatch, dias=("2026-10-06", "2026-10-07"), capa=True):
    diario = tmp_path / "diario"
    for i, data in enumerate(dias):
        (diario / data).mkdir(parents=True)
        for tema in ("noticias", "hacker", "dica", "servico"):
            corpo = json.loads(json.dumps(PAUTA))
            corpo["titulo"] = f"{PAUTA['titulo']} {tema} {i}"
            corpo["infografico"]["hashtags"] = ["#Tema", "#TI", "#TECHDIM"] if tema != "dica" else ["#Outro"]
            if tema == "servico":
                corpo["fontes"], corpo["motivo"] = [], ""
            (diario / data / f"{tema}.json").write_text(json.dumps(corpo), encoding="utf-8")
    site = tmp_path / "site"
    site.mkdir()
    (site / "index.html").write_text(INDEX_HTML, encoding="utf-8")
    (site / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (site / "styles.css").write_text("", encoding="utf-8")
    (site / "assets").mkdir()
    (site / "assets" / "techdim-official-cube-icon.jpg").write_bytes(b"jpg")
    (site / "sitemap.xml").write_text(SITEMAP_ANTIGO, encoding="utf-8")
    (site / "robots.txt").write_text("User-agent: *\nAllow: /\n\nSitemap: https://www.techdim.com.br/sitemap.xml\n", encoding="utf-8")
    monkeypatch.setattr(blog, "DIARIO", diario)
    monkeypatch.setattr(blog, "renderizar_capa", capa_falsa if capa else (lambda *a: False))
    return site


def impressao(site: pathlib.Path) -> dict:
    return {str(p.relative_to(site)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(site.rglob("*")) if p.is_file()}


class Pagina(HTMLParser):
    """Lê o que importa para buscadores: título, metas, h1, canonical, JSON-LD, imagens e links."""

    def __init__(self, html):
        super().__init__()
        self.title, self.h1, self.meta, self.props = "", 0, {}, {}
        self.canonical, self.ld, self.imgs, self.links, self.ids = None, [], [], [], []
        self._titulo = self._ld = False
        self._buf = ""
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.append(a["id"])
        if tag == "title":
            self._titulo = True
        elif tag == "h1":
            self.h1 += 1
        elif tag == "meta":
            if a.get("name"):
                self.meta[a["name"]] = a.get("content", "")
            if a.get("property"):
                self.props.setdefault(a["property"], []).append(a.get("content", ""))
        elif tag == "link":
            if a.get("rel") == "canonical":
                self.canonical = a.get("href")
            if a.get("href"):
                self.links.append(a["href"])
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
        elif tag == "img":
            self.imgs.append(a)
            if a.get("src"):
                self.links.append(a["src"])
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._ld, self._buf = True, ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._titulo = False
        elif tag == "script" and self._ld:
            self._ld = False
            self.ld.append(json.loads(self._buf))

    def handle_data(self, data):
        if self._titulo:
            self.title += data
        if self._ld:
            self._buf += data


def links_quebrados(site: pathlib.Path, pagina: pathlib.Path, p: Pagina) -> list[str]:
    ruins = []
    for href in p.links:
        if href.startswith(("mailto:", "tel:", "#", "https://fonts.", "http")) and not href.startswith(blog.BASE_URL):
            continue
        if href.startswith(blog.BASE_URL):
            rel = href[len(blog.BASE_URL):].lstrip("/").split("#")[0]
            alvo = site / rel
        else:
            alvo = (pagina.parent / href.split("#")[0].split("?")[0]).resolve()
        if alvo.is_dir():
            alvo = alvo / "index.html"
        if not alvo.exists():
            ruins.append(href)
    return ruins


# ---------------------------------------------------------------- utilidades ---

def test_slugify_sem_acento_e_sem_terminar_em_palavra_fraca():
    assert blog.slugify("Atualização já é defesa!") == "atualizacao-ja-e-defesa"
    longo = blog.slugify("Notebook perdido sem BitLocker é dado exposto: como ligar a criptografia agora")
    assert len(longo) <= 60 and not longo.endswith(("-a", "-de", "-o", "-e")) and longo.startswith("notebook-perdido")
    assert blog.slugify("A e o") == "a-e-o"  # curto demais para podar


def test_truncar_corta_em_palavra_inteira():
    assert blog.truncar("um dois três quatro cinco", 14) == "um dois três…"
    assert blog.truncar("curto", 50) == "curto"


# --------------------------------------------------------------------- páginas ---

def test_gera_dia_e_artigos_com_seo_completo(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    dias = blog.gerar(site)
    assert [d.data for d in dias] == ["2026-10-06", "2026-10-07"]
    a = dias[-1].artigos[0]
    pagina = site / a.caminho / "index.html"
    html = pagina.read_text(encoding="utf-8")
    p = Pagina(html)

    assert p.h1 == 1 and len(set(p.ids)) == len(p.ids)
    assert p.canonical == a.url and a.url.startswith("https://techdimbr.github.io/techdimbr/blog/2026-10-07/")
    assert 0 < len(p.meta["description"]) <= 160
    assert "index" in p.meta["robots"] and "max-image-preview:large" in p.meta["robots"]
    assert p.props["og:type"] == ["article"] and p.props["og:image"] == [a.capa_url]
    assert p.props["article:published_time"] == ["2026-10-07T06:00:00-03:00"]
    assert p.props["og:locale"] == ["pt_BR"]
    assert all("alt" in i and i.get("width") and i.get("height") for i in p.imgs)
    assert "&lt;b&gt;" in html and "<b>do dia</b>" not in html  # texto da pauta vai escapado
    assert "https://exemplo.com/a?x=1&amp;y=2" in html
    assert links_quebrados(site, pagina, p) == []

    tipos = {bloco["@type"]: bloco for bloco in p.ld}
    post = tipos["BlogPosting"]
    assert post["headline"] and post["datePublished"] == post["dateModified"] == "2026-10-07T06:00:00-03:00"
    assert post["author"]["name"] and post["publisher"]["logo"]["url"].startswith("https://")
    assert post["image"]["url"] == a.capa_url and post["mainEntityOfPage"]["@id"] == a.url
    assert post["citation"][0]["url"] == "https://exemplo.com/a?x=1&y=2"
    nomes = [i["name"] for i in tipos["BreadcrumbList"]["itemListElement"]]
    assert nomes[:2] == ["Início", "Blog"] and nomes[-1] == a.titulo


def test_titulo_curto_leva_a_marca_e_longo_nao(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    dias = blog.gerar(site)
    longo = dias[-1].artigos[0]
    assert Pagina((site / longo.caminho / "index.html").read_text(encoding="utf-8")).title == longo.titulo
    curto = blog.Artigo("2026-10-07", "dica", "Curto", "curto", ["a"], "", "", [], [], [], "", "alt")
    assert blog.html_artigo(curto, dias[-1], [curto], None, None).count("<title>Curto | TECHDIM</title>") == 1


def test_resumo_do_dia_lista_os_artigos_e_liga_aos_dias_vizinhos(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    dias = blog.gerar(site)
    dia_html = (site / "blog/2026-10-07/index.html").read_text(encoding="utf-8")
    p = Pagina(dia_html)
    assert p.h1 == 1 and links_quebrados(site, site / "blog/2026-10-07/index.html", p) == []
    for a in dias[-1].artigos:
        assert f'href="{a.slug}/"' in dia_html
    assert 'href="../2026-10-06/" rel="prev"' in dia_html and 'rel="next"' not in dia_html
    assert 'rel="next"' in (site / "blog/2026-10-06/index.html").read_text(encoding="utf-8")
    colecao = next(b for b in p.ld if b["@type"] == "CollectionPage")
    assert len(colecao["mainEntity"]["itemListElement"]) == 4


def test_artigo_sem_capa_usa_imagem_padrao_do_site(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch, capa=False)
    dias = blog.gerar(site)
    a = dias[-1].artigos[0]
    p = Pagina((site / a.caminho / "index.html").read_text(encoding="utf-8"))
    assert all("capa.jpg" not in i.get("src", "") for i in p.imgs)
    assert p.props["og:image"] == [blog.PREVIEW_URL]


def test_servico_nao_mostra_o_motivo_interno(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    dias = blog.gerar(site)
    servico = next(a for a in dias[-1].artigos if a.tema == "servico")
    html = (site / servico.caminho / "index.html").read_text(encoding="utf-8")
    assert "Por que importa" not in html and "Como funciona" in html and "Fontes consultadas" not in html
    assert "Quer esse serviço na sua empresa?" in html


def test_leia_tambem_liga_artigos_com_assunto_em_comum(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    dias = blog.gerar(site)
    novo = next(a for a in dias[-1].artigos if a.tema == "noticias")
    html = (site / novo.caminho / "index.html").read_text(encoding="utf-8")
    antigo = next(a for a in dias[0].artigos if a.tema == "noticias")
    assert "Leia também" in html and antigo.caminho in html
    primeiro = next(a for a in dias[0].artigos if a.tema == "noticias")
    assert "Leia também" not in (site / primeiro.caminho / "index.html").read_text(encoding="utf-8")


def test_indice_e_arquivo_mensal(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch, dias=("2026-09-30", "2026-10-01", "2026-10-02"))
    blog.gerar(site)
    indice = (site / "blog/index.html").read_text(encoding="utf-8")
    p = Pagina(indice)
    assert p.h1 == 1 and links_quebrados(site, site / "blog/index.html", p) == []
    assert "arquivo/2026-09/" in indice and "arquivo/2026-10/" in indice
    mes = (site / "blog/arquivo/2026-10/index.html").read_text(encoding="utf-8")
    assert "Radar TECHDIM · 02/10/2026" in mes and "Radar TECHDIM · 30/09/2026" not in mes
    assert links_quebrados(site, site / "blog/arquivo/2026-10/index.html", Pagina(mes)) == []
    blog_ld = next(b for b in p.ld if b["@type"] == "Blog")
    assert blog_ld["blogPost"][0]["datePublished"].startswith("2026-10-02")


def test_artigo_que_mudou_de_titulo_nao_deixa_pagina_orfa(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch, dias=("2026-10-07",))
    blog.gerar(site)
    antigo = site / "blog/2026-10-07"
    nomes_antes = {p.name for p in antigo.iterdir() if p.is_dir()}
    arq = blog.DIARIO / "2026-10-07" / "dica.json"
    corpo = json.loads(arq.read_text(encoding="utf-8"))
    corpo["titulo"] = "Título totalmente novo da dica"
    arq.write_text(json.dumps(corpo), encoding="utf-8")
    blog.gerar(site)
    nomes_depois = {p.name for p in antigo.iterdir() if p.is_dir()}
    assert "titulo-totalmente-novo-da-dica" in nomes_depois
    assert len(nomes_depois) == len(nomes_antes) == 4


def test_rodar_de_novo_nao_muda_nenhum_arquivo(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    blog.gerar(site)
    antes = impressao(site)
    blog.gerar(site)
    assert impressao(site) == antes


# ----------------------------------------------------------- sitemap, feed, robots ---

def test_sitemap_so_com_enderecos_validos_do_site(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    dias = blog.gerar(site)
    texto = (site / "sitemap.xml").read_text(encoding="utf-8")
    xml.dom.minidom.parseString(texto)
    assert "techdim.com.br" not in texto  # outro domínio não pode constar neste sitemap
    assert "techdimbr/sobre/" in texto and "<lastmod>2026-08-01</lastmod>" in texto  # entrada válida preservada
    assert "blog/velho/" not in texto  # o que é do blog é sempre regenerado
    # home, blog, a página "sobre" que já existia, o arquivo do mês e 2 dias x (resumo + 4 artigos)
    assert texto.count("<loc>") == 4 + len(dias) * 5
    assert texto.count("<image:loc>") == 8 and "capa.jpg" in texto
    assert f"<loc>{blog.BASE_URL}/</loc>" in texto and "<lastmod>2026-10-07</lastmod>" in texto


def test_sitemap_sem_imagem_quando_nao_ha_capa(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch, capa=False)
    blog.gerar(site)
    assert "<image:loc>" not in (site / "sitemap.xml").read_text(encoding="utf-8")


def test_feed_rss_valido_com_os_artigos_mais_novos_primeiro(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    blog.gerar(site)
    texto = (site / "blog/feed.xml").read_text(encoding="utf-8")
    xml.dom.minidom.parseString(texto)
    assert texto.count("<item>") == 8
    assert texto.index("blog/2026-10-07/") < texto.index("blog/2026-10-06/")
    assert "Wed, 07 Oct 2026" in texto and "-0300" in texto


def test_robots_aponta_para_o_sitemap_certo_e_cria_se_faltar(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    blog.gerar(site)
    assert (site / "robots.txt").read_text(encoding="utf-8").count("Sitemap:") == 1
    assert f"Sitemap: {blog.BASE_URL}/sitemap.xml" in (site / "robots.txt").read_text(encoding="utf-8")
    (site / "robots.txt").unlink()
    blog.atualizar_robots(site)
    assert "User-agent: *" in (site / "robots.txt").read_text(encoding="utf-8")


# ------------------------------------------------------------------ página inicial ---

def test_home_ganha_seo_correto_e_bloco_do_blog(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    blog.gerar(site)
    html = (site / "index.html").read_text(encoding="utf-8")
    p = Pagina(html)
    assert p.canonical == f"{blog.BASE_URL}/"  # antes apontava para uma página que não existe
    assert p.props["og:url"] == [f"{blog.BASE_URL}/"] and p.props["og:image"][0] == blog.PREVIEW_URL
    assert p.props["twitter:image"] == [blog.PREVIEW_URL] and "max-snippet:-1" in p.meta["robots"]
    org = next(b for b in p.ld if b.get("@type") == "ProfessionalService")
    assert org["@id"] == f"{blog.BASE_URL}/#organization" and org["name"] == "Empresa"
    assert org["founder"]["name"] == "Fulano" and org["sameAs"] and org["logo"].startswith("https://")
    grafo = next(b for b in p.ld if "@graph" in b)["@graph"]
    assert {g["@type"] for g in grafo} == {"WebSite", "Blog"}
    assert 'rel="alternate" type="application/rss+xml"' in html and 'href="blog/blog.css"' in html
    # bloco com os posts novos, antes da seção de contato
    assert html.index("blog-recentes:inicio") < html.index("Contact & Conversion Section")
    recentes = html[html.index("blog-recentes:inicio"):html.index("blog-recentes:fim")]
    assert recentes.count('class="blog-home-card"') == 6 and "Serviço TECHDIM" not in recentes
    assert 'href="blog/2026-10-07/' in recentes


def test_home_idempotente_e_atualiza_o_bloco_quando_chega_post_novo(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch, dias=("2026-10-06",))
    blog.gerar(site)
    primeiro = (site / "index.html").read_text(encoding="utf-8")
    blog.gerar(site)
    assert (site / "index.html").read_text(encoding="utf-8") == primeiro
    assert primeiro.count("seo:inicio") == 1 and primeiro.count("blog-recentes:inicio") == 1
    nova = blog.DIARIO / "2026-10-07"
    nova.mkdir()
    for tema in ("noticias", "hacker", "dica", "servico"):
        (nova / f"{tema}.json").write_text(json.dumps(dict(PAUTA, titulo=f"Novidade de hoje {tema}")), encoding="utf-8")
    blog.gerar(site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert html.count("blog-recentes:inicio") == 1 and "novidade-de-hoje-noticias" in html


def test_codigos_de_verificacao_dos_buscadores_vem_do_seo_json(tmp_path, monkeypatch):
    site = monta(tmp_path, monkeypatch)
    blog.gerar(site)
    assert "google-site-verification" not in (site / "index.html").read_text(encoding="utf-8")
    (site / "seo.json").write_text(json.dumps({"google_site_verification": "abc123", "bing_site_verification": "xyz"}))
    blog.gerar(site)
    html = (site / "index.html").read_text(encoding="utf-8")
    assert '<meta name="google-site-verification" content="abc123" />' in html
    assert '<meta name="msvalidate.01" content="xyz" />' in html
    (site / "seo.json").write_text("{}")
    blog.gerar(site)
    assert "google-site-verification" not in (site / "index.html").read_text(encoding="utf-8")


# ------------------------------------------------------------------------- capa ---

def test_capa_real_vira_jpeg_pequeno_no_tamanho_certo(tmp_path, monkeypatch):
    pillow = pytest.importorskip("PIL.Image")
    import content

    pasta = tmp_path / "conteudo"
    (pasta / "diario" / "2026-10-07").mkdir(parents=True)
    corpo = json.loads(json.dumps(PAUTA))
    corpo["titulo"] = "Título curto"
    corpo["infografico"]["cena_composta"] = {"fundo": "escritorio", "elementos": ["notebook"], "legenda": "TESTE"}
    corpo["infografico"]["pergunta"] = "Pergunta?"
    (pasta / "diario" / "2026-10-07" / "dica.json").write_text(json.dumps(corpo), encoding="utf-8")
    monkeypatch.setattr(content, "CONTENT_DIR", pasta)
    destino = tmp_path / "capa.jpg"
    assert blog.renderizar_capa("2026-10-07", "dica", destino) is True
    with pillow.open(destino) as img:
        assert img.size == blog.CAPA_TAMANHO and img.format == "JPEG"
    assert destino.stat().st_size < 150_000
    assert blog.renderizar_capa("2026-10-08", "dica", tmp_path / "x.jpg") is False  # sem pauta, sem capa
