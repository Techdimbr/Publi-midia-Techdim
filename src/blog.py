"""Blog do site TECHDIM: um post por dia, montado a partir da pauta do dia.

O post "Radar TECHDIM" reaproveita o que já foi escrito e conferido em
content/diario/<data>/ (notícia, alerta, dica e serviço): nada de fato novo é
inventado aqui, só se reorganiza o texto da pauta em um artigo com fontes.

Uso (a partir da raiz deste repositório):
    python src/blog.py --site /caminho/do/repo-do-site [--data AAAA-MM-DD ...]
Sem --data, gera todos os dias que existem em content/diario/.

Saída no repositório do site: blog/index.html, blog/<AAAA-MM-DD>/index.html,
blog/blog.css, blog/feed.xml e as entradas do blog no sitemap.xml.
Só biblioteca padrão; o site é estático (GitHub Pages).
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DIARIO = RAIZ / "content" / "diario"
BASE_URL = "https://techdimbr.github.io/techdimbr"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
TEMAS = [  # arquivo, rótulo da seção
    ("noticias", "Notícia de tecnologia"),
    ("hacker", "Alerta de segurança"),
    ("dica", "Dica prática"),
]
SITEMAP_INI, SITEMAP_FIM = "<!-- blog:inicio -->", "<!-- blog:fim -->"


def e(texto: str) -> str:
    return html.escape(str(texto), quote=True)


def data_extenso(data: str) -> str:
    d = dt.date.fromisoformat(data)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def data_curta(data: str) -> str:
    return dt.date.fromisoformat(data).strftime("%d/%m/%Y")


def carregar_dia(data: str) -> dict[str, dict]:
    pasta = DIARIO / data
    pauta = {}
    for tema in ("noticias", "hacker", "dica", "servico"):
        arq = pasta / f"{tema}.json"
        if arq.exists():
            pauta[tema] = json.loads(arq.read_text(encoding="utf-8"))
    return pauta


def dias_disponiveis() -> list[str]:
    return sorted(
        p.name for p in DIARIO.iterdir()
        if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name)
        and any((p / f"{t}.json").exists() for t, _ in TEMAS)
    )


# --------------------------------------------------------------- conteúdo ---

def montar_post(data: str, pauta: dict[str, dict]) -> dict:
    """Estrutura neutra do post, usada pelo HTML, pelo índice e pelo feed."""
    secoes = []
    for tema, rotulo in TEMAS:
        p = pauta.get(tema)
        if not p:
            continue
        info = p.get("infografico", {})
        secoes.append({
            "tema": tema,
            "rotulo": rotulo,
            "titulo": p["titulo"],
            "pontos": p.get("pontos", []),
            "fecho": p.get("fecho", ""),
            "motivo": p.get("motivo", ""),
            "licoes": info.get("licoes", []),
            "fontes": p.get("fontes", []),
            "hashtags": info.get("hashtags", []),
        })
    servico = pauta.get("servico")
    destaque = None
    if servico:
        destaque = {
            "titulo": servico["titulo"],
            "pontos": servico.get("pontos", []),
            "fecho": servico.get("fecho", ""),
        }
    titulos = [s["titulo"] for s in secoes]
    return {
        "data": data,
        "titulo": f"Radar TECHDIM · {data_curta(data)}",
        "resumo": " | ".join(titulos),
        "secoes": secoes,
        "servico": destaque,
        "tags": sorted({h.lstrip("#") for s in secoes for h in s["hashtags"]
                        if h.lower() not in ("#ti", "#techdim")}),
    }


# ------------------------------------------------------------------- HTML ---

def cabecalho(prefixo: str) -> str:
    """Cabeçalho igual ao do site; links do site ficam relativos à raiz."""
    p = prefixo
    return f"""<a href="#conteudo" class="skip-link">Pular para o conteúdo principal</a>
  <div class="cyber-bg-canvas" aria-hidden="true"></div>
  <header class="site-header" id="top">
    <div class="container nav-bar">
      <a href="{p}" class="brand-wrapper" aria-label="TECHDIM Início">
        <img src="{p}assets/techdim-official-cube-icon.jpg" alt="Logo Oficial TECHDIM INOVA" class="brand-logo-img" width="50" height="50" />
        <div class="brand-meta">
          <span class="brand-title">TECHDIM<span>_</span></span>
          <span class="brand-subtitle">INOVA SIMPLES // KETHER_1</span>
        </div>
      </a>
      <nav aria-label="Navegação Principal">
        <ul class="nav-menu" id="navMenu">
          <li><a href="{p}#solucoes" class="nav-link">Serviços B2B</a></li>
          <li><a href="{p}#sobre" class="nav-link">Sobre Nós</a></li>
          <li><a href="{p}blog/" class="nav-link active">Blog</a></li>
          <li><a href="{p}#faq" class="nav-link">FAQ</a></li>
          <li><a href="{p}#contato" class="nav-link">Contato</a></li>
        </ul>
      </nav>
      <div class="nav-cta-group">
        <button class="mobile-toggle" id="mobileToggle" aria-label="Abrir Menu">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
      </div>
    </div>
  </header>"""


def rodape(prefixo: str) -> str:
    p = prefixo
    return f"""<footer class="site-footer">
    <div class="container footer-bar">
      <div>© 2026 TECHDIM INOVA SIMPLES (I.S.) - ME. Todos os direitos reservados.</div>
      <div style="display: flex; gap: 1.5rem; flex-wrap: wrap;">
        <a href="{p}blog/feed.xml" style="color: var(--cyan-neon);">Feed RSS</a>
        <a href="{p}#contato" style="color: var(--cyan-neon);">Fale com a TECHDIM</a>
        <a href="#top" style="color: var(--cyan-neon);">Voltar ao Topo ↑</a>
      </div>
    </div>
  </footer>
  <script>
    (function () {{
      var b = document.getElementById('mobileToggle'), m = document.getElementById('navMenu');
      if (!b || !m) return;
      b.addEventListener('click', function () {{ m.classList.toggle('open'); }});
    }})();
  </script>"""


def pagina(titulo: str, descricao: str, canonico: str, prefixo: str,
           corpo: str, extra_head: str = "") -> str:
    p = prefixo
    return f"""<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(titulo)} | TECHDIM</title>
  <meta name="description" content="{e(descricao)}" />
  <meta name="robots" content="index, follow" />
  <link rel="canonical" href="{e(canonico)}" />
  <meta property="og:type" content="article" />
  <meta property="og:title" content="{e(titulo)}" />
  <meta property="og:description" content="{e(descricao)}" />
  <meta property="og:url" content="{e(canonico)}" />
  <meta property="og:image" content="{BASE_URL}/assets/techdim-preview.jpg" />
  <meta property="og:locale" content="pt_BR" />
  <meta property="og:site_name" content="TECHDIM" />
  <meta name="twitter:card" content="summary_large_image" />
  <link rel="icon" type="image/svg+xml" href="{p}favicon.svg" />
  <link rel="alternate" type="application/rss+xml" title="Blog TECHDIM" href="{BASE_URL}/blog/feed.xml" />
  <meta name="theme-color" content="#030712" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{p}styles.css" />
  <link rel="stylesheet" href="{p}blog/blog.css" />
{extra_head}</head>
<body>
  {cabecalho(p)}
  <main id="conteudo">
{corpo}
  </main>
  {rodape(p)}
</body>
</html>
"""


def lista_fontes(fontes: list) -> str:
    if not fontes:
        return ""
    itens = "".join(
        f'<li><a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(dom)}</a></li>'
        for dom, url in fontes
    )
    return f'<p class="blog-fontes-titulo">Fontes consultadas</p><ul class="blog-fontes">{itens}</ul>'


def html_secao(s: dict) -> str:
    pontos = "".join(f"<li>{e(t)}</li>" for t in s["pontos"])
    licoes = "".join(
        f"<li><strong>{e(t)}.</strong> {e(x)}</li>" for t, x in s["licoes"]
    )
    por_que = f'<p class="blog-motivo"><strong>Por que importa:</strong> {e(s["motivo"])}</p>' if s["motivo"] else ""
    fecho = f'<p class="blog-fecho">{e(s["fecho"])}</p>' if s["fecho"] else ""
    acao = (f'<h3>O que fazer na prática</h3><ol class="blog-passos">{licoes}</ol>'
            if licoes else "")
    return f"""    <section class="blog-secao blog-{e(s['tema'])}">
      <span class="blog-rotulo">{e(s['rotulo'])}</span>
      <h2>{e(s['titulo'])}</h2>
      <ul class="blog-pontos">{pontos}</ul>
      {fecho}
      {por_que}
      {acao}
      {lista_fontes(s['fontes'])}
    </section>"""


def html_servico(sv: dict | None) -> str:
    if not sv:
        return ""
    pontos = "".join(f"<li>{e(t)}</li>" for t in sv["pontos"])
    return f"""    <section class="blog-secao blog-servico">
      <span class="blog-rotulo">Serviço TECHDIM em destaque</span>
      <h2>{e(sv['titulo'])}</h2>
      <ul class="blog-pontos">{pontos}</ul>
      <p class="blog-fecho">{e(sv['fecho'])}</p>
      <p><a class="blog-botao" href="../../#contato">Fale com a TECHDIM</a></p>
    </section>"""


def html_post(post: dict) -> str:
    data = post["data"]
    corpo_secoes = "\n".join(html_secao(s) for s in post["secoes"])
    sumario = "".join(
        f'<li><span>{e(s["rotulo"])}</span> {e(s["titulo"])}</li>' for s in post["secoes"]
    )
    corpo = f"""    <article class="container blog-artigo">
      <nav class="blog-migalhas" aria-label="Você está em"><a href="../">Blog</a> / {e(data_curta(data))}</nav>
      <header class="blog-topo">
        <p class="blog-data"><time datetime="{e(data)}">{e(data_extenso(data))}</time></p>
        <h1>{e(post['titulo'])}</h1>
        <p class="blog-lead">O resumo do dia da TECHDIM para donos de empresas e gestores de TI: o que aconteceu em tecnologia e segurança, e o que você pode fazer hoje.</p>
        <ul class="blog-sumario">{sumario}</ul>
      </header>
{corpo_secoes}
{html_servico(post['servico'])}
      <p class="blog-aviso">Este texto resume informações das fontes citadas na data de publicação. Confira sempre o aviso oficial do fabricante antes de agir em produção.</p>
      <p><a class="blog-voltar" href="../">← Todos os posts do blog</a></p>
    </article>"""
    descricao = post["resumo"][:300]
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": post["titulo"], "datePublished": data,
        "description": descricao, "inLanguage": "pt-BR",
        "mainEntityOfPage": f"{BASE_URL}/blog/{data}/",
        "author": {"@type": "Organization", "name": "TECHDIM INOVA SIMPLES"},
        "publisher": {"@type": "Organization", "name": "TECHDIM INOVA SIMPLES"},
    }, ensure_ascii=False).replace("</", "<\\/")
    extra = f'  <script type="application/ld+json">{ld}</script>\n'
    return pagina(post["titulo"], descricao, f"{BASE_URL}/blog/{data}/", "../../", corpo, extra)


def html_indice(posts: list[dict]) -> str:
    cartoes = []
    for post in posts:
        itens = "".join(f"<li>{e(s['titulo'])}</li>" for s in post["secoes"])
        cartoes.append(f"""      <a class="blog-cartao" href="{e(post['data'])}/">
        <p class="blog-data"><time datetime="{e(post['data'])}">{e(data_extenso(post['data']))}</time></p>
        <h2>{e(post['titulo'])}</h2>
        <ul>{itens}</ul>
        <span class="blog-mais">Ler o resumo completo →</span>
      </a>""")
    corpo = f"""    <section class="container blog-lista">
      <header class="blog-topo">
        <p class="blog-rotulo">Blog TECHDIM</p>
        <h1>Radar diário de tecnologia e segurança</h1>
        <p class="blog-lead">Todo dia, um resumo com notícia de tecnologia, alerta de segurança, uma dica prática e um serviço da TECHDIM, sempre com as fontes.</p>
      </header>
      <div class="blog-grade">
{chr(10).join(cartoes)}
      </div>
    </section>"""
    return pagina("Blog TECHDIM — radar diário de tecnologia e segurança",
                  "Resumo diário com notícia de tecnologia, alerta de segurança, dica prática e serviços de TI para empresas, com fontes.",
                  f"{BASE_URL}/blog/", "../", corpo)


CSS = """/* Blog TECHDIM — complementa styles.css do site */
.blog-artigo, .blog-lista { max-width: 860px; padding-top: 7rem; padding-bottom: 4rem; }
.blog-migalhas { font-family: var(--font-mono); font-size: .8rem; color: var(--text-muted); margin-bottom: 1.2rem; }
.blog-migalhas a { color: var(--cyan-neon); text-decoration: none; }
.blog-topo h1 { font-family: var(--font-display); font-size: clamp(1.9rem, 4vw, 2.8rem); line-height: 1.15; color: var(--text-pure); margin: .4rem 0 1rem; }
.blog-data { font-family: var(--font-mono); font-size: .82rem; color: var(--cyan-neon); }
.blog-lead { color: var(--text-muted); font-size: 1.08rem; line-height: 1.65; max-width: 62ch; }
.blog-sumario { list-style: none; margin: 1.4rem 0 0; padding: 1rem 1.2rem; border: 1px solid var(--border-cyber); border-radius: var(--radius-md); background: var(--bg-card); display: grid; gap: .6rem; }
.blog-sumario li { color: var(--text-main); line-height: 1.4; }
.blog-sumario span, .blog-rotulo { display: inline-block; font-family: var(--font-mono); font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--cyan-neon); margin-right: .5rem; }
.blog-secao { margin-top: 2.6rem; padding-top: 1.6rem; border-top: 1px solid var(--border-subtle); }
.blog-secao h2 { font-family: var(--font-display); font-size: clamp(1.4rem, 3vw, 1.9rem); line-height: 1.25; color: var(--text-pure); margin: .5rem 0 1rem; }
.blog-secao h3 { font-family: var(--font-display); font-size: 1.1rem; color: var(--text-pure); margin: 1.4rem 0 .6rem; }
.blog-hacker .blog-rotulo { color: var(--rose-crit); }
.blog-dica .blog-rotulo { color: var(--amber-warn); }
.blog-servico .blog-rotulo { color: var(--emerald-live); }
.blog-pontos, .blog-passos, .blog-fontes { margin: 0 0 1rem 1.2rem; color: var(--text-main); line-height: 1.7; }
.blog-pontos li, .blog-passos li, .blog-fontes li { margin-bottom: .55rem; }
.blog-fecho { color: var(--text-pure); font-weight: 600; line-height: 1.6; margin: 1rem 0; }
.blog-motivo { color: var(--text-muted); line-height: 1.6; margin-bottom: .6rem; }
.blog-fontes-titulo { font-family: var(--font-mono); font-size: .78rem; color: var(--text-dark); margin-top: 1.2rem; text-transform: uppercase; }
.blog-fontes a, .blog-voltar { color: var(--cyan-neon); }
.blog-botao { display: inline-block; padding: .8rem 1.4rem; border-radius: var(--radius-sm); background: var(--cyan-neon); color: #030712; font-weight: 700; text-decoration: none; }
.blog-botao:hover { box-shadow: 0 0 20px var(--cyan-glow); }
.blog-aviso { margin-top: 2.4rem; font-size: .85rem; color: var(--text-dark); line-height: 1.6; }
.blog-grade { display: grid; gap: 1.2rem; margin-top: 2rem; }
.blog-cartao { display: block; padding: 1.4rem 1.5rem; border: 1px solid var(--border-cyber); border-radius: var(--radius-md); background: var(--bg-card); text-decoration: none; transition: transform .25s var(--ease), background .25s var(--ease); }
.blog-cartao:hover, .blog-cartao:focus-visible { background: var(--bg-card-hover); transform: translateY(-2px); }
.blog-cartao h2 { font-family: var(--font-display); font-size: 1.35rem; color: var(--text-pure); margin: .3rem 0 .7rem; }
.blog-cartao ul { margin: 0 0 .9rem 1.1rem; color: var(--text-muted); line-height: 1.55; }
.blog-mais { font-family: var(--font-mono); font-size: .82rem; color: var(--cyan-neon); }
@media (max-width: 640px) { .blog-artigo, .blog-lista { padding-top: 6rem; } }
"""


# ------------------------------------------------------------- RSS/sitemap ---

def xml_feed(posts: list[dict]) -> str:
    itens = []
    for post in posts[:30]:
        link = f"{BASE_URL}/blog/{post['data']}/"
        pub = dt.datetime.fromisoformat(post["data"]).replace(tzinfo=dt.timezone.utc)
        itens.append(f"""    <item>
      <title>{e(post['titulo'])}</title>
      <link>{e(link)}</link>
      <guid isPermaLink="true">{e(link)}</guid>
      <pubDate>{pub.strftime('%a, %d %b %Y 11:00:00 +0000')}</pubDate>
      <description>{e(post['resumo'])}</description>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Blog TECHDIM</title>
    <link>{BASE_URL}/blog/</link>
    <description>Radar diário de tecnologia e segurança para empresas.</description>
    <language>pt-BR</language>
{chr(10).join(itens)}
  </channel>
</rss>
"""


def atualizar_sitemap(site: pathlib.Path, posts: list[dict]) -> None:
    arq = site / "sitemap.xml"
    if not arq.exists():
        return
    texto = arq.read_text(encoding="utf-8")
    urls = [f"{BASE_URL}/blog/"] + [f"{BASE_URL}/blog/{p['data']}/" for p in posts]
    bloco = SITEMAP_INI + "\n" + "\n".join(
        f"  <url><loc>{e(u)}</loc><changefreq>{'daily' if u.endswith('/blog/') else 'monthly'}</changefreq></url>"
        for u in urls
    ) + "\n  " + SITEMAP_FIM
    if SITEMAP_INI in texto:
        texto = re.sub(re.escape(SITEMAP_INI) + r".*?" + re.escape(SITEMAP_FIM), lambda _: bloco,
                       texto, flags=re.S)
    else:
        texto = texto.replace("</urlset>", f"  {bloco}\n</urlset>")
    arq.write_text(texto, encoding="utf-8")


def garantir_menu(site: pathlib.Path) -> bool:
    """Põe o link "Blog" no menu e no rodapé da página inicial, se ainda não houver."""
    arq = site / "index.html"
    texto = arq.read_text(encoding="utf-8")
    novo = texto
    menu = '          <li><a href="#sobre" class="nav-link">Sobre Nós</a></li>\n'
    if menu in novo and 'href="blog/" class="nav-link"' not in novo:
        novo = novo.replace(menu, menu + '          <li><a href="blog/" class="nav-link">Blog</a></li>\n', 1)
    rodape = '          <li><a href="#faq">Perguntas Frequentes</a></li>\n'
    if rodape in novo and 'href="blog/">Blog' not in novo:
        novo = novo.replace(rodape, rodape + '          <li><a href="blog/">Blog: Radar Diário</a></li>\n', 1)
    if novo != texto:
        arq.write_text(novo, encoding="utf-8")
    return novo != texto


# ------------------------------------------------------------------ geral ---

def gerar(site: pathlib.Path, datas: list[str]) -> list[str]:
    blog = site / "blog"
    blog.mkdir(exist_ok=True)
    for data in datas:
        pauta = carregar_dia(data)
        if not pauta:
            continue
        pasta = blog / data
        pasta.mkdir(exist_ok=True)
        (pasta / "index.html").write_text(html_post(montar_post(data, pauta)), encoding="utf-8")
    # índice, feed e sitemap sempre refletem todos os posts que existem no site
    existentes = sorted(p.name for p in blog.iterdir()
                        if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
    posts = [montar_post(d, carregar_dia(d)) for d in reversed(existentes) if carregar_dia(d)]
    (blog / "blog.css").write_text(CSS, encoding="utf-8")
    (blog / "index.html").write_text(html_indice(posts), encoding="utf-8")
    (blog / "feed.xml").write_text(xml_feed(posts), encoding="utf-8")
    atualizar_sitemap(site, posts)
    garantir_menu(site)
    return existentes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", required=True, help="pasta do repositório do site")
    ap.add_argument("--data", action="append", help="AAAA-MM-DD (repetível); padrão: todas")
    args = ap.parse_args()
    site = pathlib.Path(args.site)
    if not (site / "index.html").exists():
        print(f"{site} não parece ser a pasta do site (sem index.html)", file=sys.stderr)
        return 2
    datas = args.data or dias_disponiveis()
    existentes = gerar(site, datas)
    print(f"blog: {len(existentes)} post(s) no site; atualizados: {', '.join(datas) or 'nenhum'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
