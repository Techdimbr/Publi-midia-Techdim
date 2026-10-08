"""Blog do site TECHDIM: um artigo por assunto, montado a partir da pauta do dia.

Cada dia do blog tem 1 página-resumo ("Radar TECHDIM") e 1 artigo por post da pauta
(notícia, alerta de segurança, dica e serviço), cada um com título, descrição, imagem
e dados estruturados próprios para aparecer nos buscadores. O texto vem de
content/diario/<data>/ (já conferido na pauta): nada de fato novo é inventado aqui.

Uso (a partir da raiz deste repositório):
    python src/blog.py --site /caminho/do/repo-do-site            # todos os dias, só o que falta de imagem
    python src/blog.py --site /caminho/do/repo-do-site --forcar-imagens

Saída no repositório do site:
    blog/index.html, blog/arquivo/AAAA-MM/, blog/AAAA-MM-DD/ (resumo do dia),
    blog/AAAA-MM-DD/<assunto>/ (artigo + capa.jpg), blog/feed.xml, blog/blog.css,
    sitemap.xml, robots.txt, e, na página inicial, os blocos marcados com
    <!-- seo:inicio --> e <!-- blog-recentes:inicio -->.
Tudo é idempotente: rodar de novo reescreve os mesmos arquivos com o mesmo conteúdo.
Só biblioteca padrão (Pillow só para a capa; sem ele os artigos saem sem imagem).
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import email.utils
import html
import json
import logging
import pathlib
import re
import shutil
import sys
import tempfile
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET

log = logging.getLogger("techdim.blog")

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DIARIO = RAIZ / "content" / "diario"

BASE_URL = "https://techdimbr.github.io/techdimbr"
HOST = urllib.parse.urlparse(BASE_URL).netloc
CAMINHO_BASE = urllib.parse.urlparse(BASE_URL).path  # "/techdimbr"
LOGO_URL = f"{BASE_URL}/assets/techdim-official-logo.png"
PREVIEW_URL = f"{BASE_URL}/assets/techdim-preview.jpg"
PREVIEW_TAMANHO = (1376, 768)
MARCA = "TECHDIM"
EMPRESA = "TECHDIM INOVA SIMPLES"
REDES = [  # perfis oficiais já usados nas publicações
    "https://github.com/Techdimbr",
    "https://www.instagram.com/techdimbr/",
    "https://www.facebook.com/122132402349390486",
]
FUNDADOR_LINKEDIN = "https://linkedin.com/in/deivismayer"

CAPA_TAMANHO = (720, 900)
CAPA_QUALIDADE = 72
ROBOTS = "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"

MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
ROTULOS = {
    "noticias": "Notícia de tecnologia",
    "hacker": "Alerta de segurança",
    "dica": "Dica prática",
    "servico": "Serviço TECHDIM",
}
ORDEM = ["noticias", "hacker", "dica", "servico"]
# (resumo, por que importa, passo a passo) por tema
SECOES = {
    "noticias": ("Em resumo", "Por que importa", "O que fazer na prática"),
    "hacker": ("O que aconteceu", "Por que importa", "Como se proteger"),
    "dica": ("Resumo da dica", "Por que vale a pena", "Passo a passo"),
    "servico": ("O que a TECHDIM faz", None, "Como funciona"),
}
TAGS_GENERICAS = {"ti", "techdim"}
POR_PAGINA_INDICE = 10  # dias no índice; o resto vai para o arquivo mensal
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"


# ----------------------------------------------------------------- utilidades ---

def e(texto: object) -> str:
    return html.escape(str(texto), quote=True)


def data_extenso(data: str) -> str:
    d = dt.date.fromisoformat(data)
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def data_curta(data: str) -> str:
    return dt.date.fromisoformat(data).strftime("%d/%m/%Y")


def mes_extenso(mes: str) -> str:
    ano, m = mes.split("-")
    return f"{MESES[int(m) - 1]} de {ano}"


PALAVRAS_FRACAS = {"a", "o", "as", "os", "e", "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
                   "para", "por", "com", "que", "um", "uma", "ao", "ou", "se", "sem", "ja", "mas"}


def slugify(texto: str, limite: int = 60) -> str:
    """Endereço do artigo: sem acento, minúsculo, palavras inteiras, sem terminar em "de", "a"…"""
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > limite:
        corte = s[:limite]
        if "-" in corte and s[limite] != "-":
            corte = corte.rsplit("-", 1)[0]
        s = corte.strip("-")
    partes = s.split("-")
    while len(partes) > 3 and partes[-1] in PALAVRAS_FRACAS:
        partes.pop()
    return "-".join(partes)


def truncar(texto: str, limite: int) -> str:
    """Corta em palavra inteira, com reticências, sem passar de `limite` caracteres."""
    texto = " ".join(str(texto).split())
    if len(texto) <= limite:
        return texto
    corte = texto[: limite - 1].rsplit(" ", 1)[0].rstrip(" ,;:.-—")
    return corte + "…"


def jsonld(obj: dict) -> str:
    """Bloco application/ld+json seguro para ficar dentro de uma página HTML."""
    corpo = json.dumps(obj, ensure_ascii=False, indent=2)
    corpo = corpo.replace("</", "<\\/").replace("<!--", "<\\!--")
    return f'<script type="application/ld+json">\n{corpo}\n</script>'


def recuar(texto: str, espacos: int = 2) -> str:
    return "\n".join(" " * espacos + linha if linha else linha for linha in texto.splitlines())


def organizacao_curta() -> dict:
    return {"@type": "Organization", "name": EMPRESA, "url": f"{BASE_URL}/",
            "logo": {"@type": "ImageObject", "url": LOGO_URL, "width": 1024, "height": 1024}}


# ------------------------------------------------------------------ conteúdo ---

@dataclasses.dataclass
class Artigo:
    data: str
    tema: str
    titulo: str
    slug: str
    pontos: list[str]
    fecho: str
    motivo: str
    licoes: list[tuple[str, str]]
    fontes: list[tuple[str, str]]
    tags: list[str]
    historia: str
    alt_capa: str
    indice: int = 0  # posição do tema no dia (ordena a publicação)
    tem_capa: bool = False

    @property
    def rotulo(self) -> str:
        return ROTULOS[self.tema]

    @property
    def caminho(self) -> str:
        return f"blog/{self.data}/{self.slug}/"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.caminho}"

    @property
    def capa_url(self) -> str:
        return f"{self.url}capa.jpg"

    @property
    def publicado_em(self) -> str:
        # horário de Brasília; sempre antes de a página existir, e distinto por tema
        return f"{self.data}T06:{self.indice:02d}:00-03:00"

    @property
    def descricao(self) -> str:
        base = self.pontos[0] if self.pontos else self.titulo
        return truncar(base, 155)

    @property
    def lead(self) -> str:
        return self.historia or (self.pontos[0] if self.pontos else self.titulo)


@dataclasses.dataclass
class Dia:
    data: str
    artigos: list[Artigo]

    @property
    def caminho(self) -> str:
        return f"blog/{self.data}/"

    @property
    def url(self) -> str:
        return f"{BASE_URL}/{self.caminho}"

    @property
    def titulo(self) -> str:
        return f"Radar TECHDIM {data_curta(self.data)}: resumo diário de tecnologia e segurança"

    @property
    def descricao(self) -> str:
        return truncar("Hoje no Radar TECHDIM: " + "; ".join(a.titulo for a in self.artigos), 300)


def _tags(bloco: dict) -> list[str]:
    tags = []
    for h in bloco.get("hashtags", []):
        t = str(h).lstrip("#")
        if t and t.lower() not in TAGS_GENERICAS and t not in tags:
            tags.append(t)
    return tags


def _artigo_da_pauta(data: str, tema: str, p: dict, indice: int) -> Artigo:
    info = p.get("infografico") or {}
    alt = " ".join(x for x in (info.get("titulo_branco"), info.get("titulo_destaque")) if x)
    return Artigo(
        data=data, tema=tema, titulo=p["titulo"], slug=slugify(p["titulo"]),
        pontos=[str(x) for x in p.get("pontos", [])],
        fecho=str(p.get("fecho", "")), motivo=str(p.get("motivo", "")),
        licoes=[(str(t), str(x)) for t, x in info.get("licoes", [])],
        fontes=[(str(d), str(u)) for d, u in p.get("fontes", [])],
        tags=_tags(info), historia=str(info.get("historia", "")),
        alt_capa=f"Infográfico TECHDIM: {alt}" if alt else f"Infográfico TECHDIM: {p['titulo']}",
        indice=indice,
    )


def carregar_dia(data: str) -> Dia | None:
    pasta = DIARIO / data
    artigos: list[Artigo] = []
    for i, tema in enumerate(ORDEM):
        arq = pasta / f"{tema}.json"
        if not arq.exists():
            continue
        try:
            artigos.append(_artigo_da_pauta(data, tema, json.loads(arq.read_text(encoding="utf-8")), i))
        except (ValueError, KeyError, TypeError) as exc:
            log.warning("pauta %s/%s ignorada: %s", data, tema, exc)
    if not artigos:
        return None
    usados: set[str] = set()
    for a in artigos:  # dois títulos iguais no mesmo dia não podem dividir o endereço
        if a.slug in usados or not a.slug:
            a.slug = f"{a.slug or 'artigo'}-{a.tema}"
        usados.add(a.slug)
    return Dia(data, artigos)


def carregar_dias() -> list[Dia]:
    if not DIARIO.exists():
        return []
    nomes = sorted(p.name for p in DIARIO.iterdir()
                   if p.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.name))
    return [d for d in (carregar_dia(n) for n in nomes) if d]


# ---------------------------------------------------------------------- capa ---

def renderizar_capa(data: str, tema: str, destino: pathlib.Path) -> bool:
    """Infográfico do post reduzido a JPEG para o artigo. False se não foi possível."""
    try:
        from PIL import Image

        import content
        import render
    except Exception:  # noqa: BLE001 — sem Pillow/render o artigo só sai sem imagem
        log.warning("sem Pillow/render: artigo %s/%s ficará sem capa", data, tema)
        return False
    try:
        post = content._da_pauta(tema, dt.date.fromisoformat(data))  # noqa: SLF001
        if not post:
            return False
        with tempfile.TemporaryDirectory() as tmp:
            png = render.render_infografico(post, pathlib.Path(tmp) / f"{tema}.png", slug=f"{tema}-{data}")
            if not png:
                return False
            with Image.open(png) as img:
                img = img.convert("RGB").resize(CAPA_TAMANHO, Image.LANCZOS)
                destino.parent.mkdir(parents=True, exist_ok=True)
                img.save(destino, "JPEG", quality=CAPA_QUALIDADE, optimize=True, progressive=True)
        return True
    except Exception:  # noqa: BLE001 — uma imagem ruim não pode impedir o texto de sair
        log.exception("capa de %s/%s falhou", data, tema)
        return False


# ------------------------------------------------------------------- páginas ---

@dataclasses.dataclass
class Meta:
    titulo: str
    descricao: str
    canonico: str
    og_tipo: str = "website"
    imagem: str = PREVIEW_URL
    imagem_tamanho: tuple[int, int] = PREVIEW_TAMANHO
    imagem_alt: str = "TECHDIM — cibersegurança, nuvem e IA para empresas"
    publicado: str = ""
    secao: str = ""
    tags: tuple[str, ...] = ()
    ld: tuple[dict, ...] = ()


def cabeca(m: Meta, p: str) -> str:
    og_extra = ""
    if m.publicado:
        og_extra += (f'  <meta property="article:published_time" content="{e(m.publicado)}" />\n'
                     f'  <meta property="article:modified_time" content="{e(m.publicado)}" />\n')
    if m.secao:
        og_extra += f'  <meta property="article:section" content="{e(m.secao)}" />\n'
    for t in m.tags:
        og_extra += f'  <meta property="article:tag" content="{e(t)}" />\n'
    ld = "\n".join(jsonld(o) for o in m.ld)
    return f"""<meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{e(m.titulo)}</title>
  <meta name="description" content="{e(m.descricao)}" />
  <meta name="robots" content="{ROBOTS}" />
  <meta name="author" content="{e(EMPRESA)}" />
  <link rel="canonical" href="{e(m.canonico)}" />
  <link rel="alternate" hreflang="pt-BR" href="{e(m.canonico)}" />
  <link rel="alternate" hreflang="x-default" href="{e(m.canonico)}" />
  <link rel="alternate" type="application/rss+xml" title="Blog {MARCA}" href="{BASE_URL}/blog/feed.xml" />
  <meta property="og:type" content="{e(m.og_tipo)}" />
  <meta property="og:site_name" content="{MARCA}" />
  <meta property="og:locale" content="pt_BR" />
  <meta property="og:title" content="{e(m.titulo)}" />
  <meta property="og:description" content="{e(m.descricao)}" />
  <meta property="og:url" content="{e(m.canonico)}" />
  <meta property="og:image" content="{e(m.imagem)}" />
  <meta property="og:image:width" content="{m.imagem_tamanho[0]}" />
  <meta property="og:image:height" content="{m.imagem_tamanho[1]}" />
  <meta property="og:image:alt" content="{e(m.imagem_alt)}" />
{og_extra}  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="{e(m.titulo)}" />
  <meta name="twitter:description" content="{e(m.descricao)}" />
  <meta name="twitter:image" content="{e(m.imagem)}" />
  <meta name="twitter:image:alt" content="{e(m.imagem_alt)}" />
  <link rel="icon" type="image/svg+xml" href="{p}favicon.svg" />
  <meta name="theme-color" content="#030712" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Space+Grotesk:wght@500;600;700;800&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="{p}styles.css" />
  <link rel="stylesheet" href="{p}blog/blog.css" />
  {ld}"""


def topo_site(p: str) -> str:
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
        <button class="mobile-toggle" id="mobileToggle" aria-label="Abrir Menu" aria-expanded="false">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
      </div>
    </div>
  </header>"""


def rodape_site(p: str) -> str:
    return f"""<footer class="site-footer">
    <div class="container footer-bar">
      <div>© 2026 TECHDIM INOVA SIMPLES (I.S.) - ME. Todos os direitos reservados.</div>
      <nav class="blog-rodape-nav" aria-label="Blog">
        <a href="{p}blog/">Blog</a>
        <a href="{p}blog/feed.xml">Feed RSS</a>
        <a href="{p}#contato">Fale com a TECHDIM</a>
        <a href="#top">Voltar ao topo ↑</a>
      </nav>
    </div>
  </footer>
  <script>
    (function () {{
      var b = document.getElementById('mobileToggle'), m = document.getElementById('navMenu');
      if (!b || !m) return;
      b.addEventListener('click', function () {{
        var aberto = m.classList.toggle('open');
        b.setAttribute('aria-expanded', aberto ? 'true' : 'false');
      }});
    }})();
  </script>"""


def pagina(m: Meta, p: str, corpo: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="pt-BR" class="dark">
<head>
  {cabeca(m, p)}
</head>
<body>
  {topo_site(p)}
  <main id="conteudo">
{corpo}
  </main>
  {rodape_site(p)}
</body>
</html>
"""


def migalhas_html(itens: list[tuple[str, str | None]]) -> str:
    """Trilha de navegação visível (o mesmo caminho vai para o JSON-LD)."""
    partes = []
    for nome, href in itens:
        partes.append(f'<a href="{e(href)}">{e(nome)}</a>' if href
                      else f'<span aria-current="page">{e(nome)}</span>')
    return f'<nav class="blog-migalhas" aria-label="Trilha de navegação">{" / ".join(partes)}</nav>'


def migalhas_ld(itens: list[tuple[str, str]]) -> dict:
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i, "name": n, "item": u}
                                for i, (n, u) in enumerate(itens, start=1)]}


def cartao_artigo(a: Artigo, p: str, dentro_do_dia: bool = False) -> str:
    href = f"{p}{a.caminho}" if not dentro_do_dia else f"{a.slug}/"
    return f"""<article class="blog-cartao">
        <p class="blog-rotulo-linha"><span class="blog-rotulo blog-{e(a.tema)}">{e(a.rotulo)}</span> <time datetime="{e(a.data)}">{e(data_curta(a.data))}</time></p>
        <h3><a href="{e(href)}">{e(a.titulo)}</a></h3>
        <p>{e(a.descricao)}</p>
        <a class="blog-mais" href="{e(href)}" aria-label="Ler o artigo: {e(a.titulo)}">Ler o artigo →</a>
      </article>"""


def lista_fontes(fontes: list[tuple[str, str]]) -> str:
    if not fontes:
        return ""
    itens = "".join(f'<li><a href="{e(u)}" target="_blank" rel="noopener noreferrer">{e(d)}</a></li>'
                    for d, u in fontes)
    return f'<section class="blog-bloco"><h2>Fontes consultadas</h2><ul class="blog-fontes">{itens}</ul></section>'


def relacionados(a: Artigo, todos: list[Artigo], limite: int = 3) -> list[Artigo]:
    """Artigos de dias anteriores com assunto em comum (mesma tag), os mais recentes primeiro.

    Só dias anteriores: assim um artigo antigo nunca muda quando chega post novo.
    """
    meus = {t.lower() for t in a.tags}
    achados = [b for b in todos if b.data < a.data and meus & {t.lower() for t in b.tags}]
    achados.sort(key=lambda b: (b.data, -b.indice), reverse=True)
    return achados[:limite]


def html_artigo(a: Artigo, dia: Dia, todos: list[Artigo], anterior: Dia | None, seguinte: Dia | None) -> str:
    p = "../../../"
    resumo_t, motivo_t, passos_t = SECOES[a.tema]
    pontos = "".join(f"<li>{e(t)}</li>" for t in a.pontos)
    fecho = f'<p class="blog-fecho">{e(a.fecho)}</p>' if a.fecho else ""
    motivo = (f'<section class="blog-bloco"><h2>{e(motivo_t)}</h2><p>{e(a.motivo)}</p></section>'
              if a.motivo and motivo_t else "")
    passos = ""
    if a.licoes:
        li = "".join(f"<li><strong>{e(t)}.</strong> {e(x)}</li>" for t, x in a.licoes)
        passos = f'<section class="blog-bloco"><h2>{e(passos_t)}</h2><ol class="blog-passos">{li}</ol></section>'
    capa = ""
    if a.tem_capa:
        capa = (f'<figure class="blog-capa"><img src="capa.jpg" width="{CAPA_TAMANHO[0]}" '
                f'height="{CAPA_TAMANHO[1]}" alt="{e(a.alt_capa)}" decoding="async" />'
                f'<figcaption>Infográfico do dia, no padrão TECHDIM.</figcaption></figure>')
    cta = ("Quer esse serviço na sua empresa?" if a.tema == "servico"
           else "Precisa de ajuda com isso na sua empresa?")
    mais_hoje = [x for x in dia.artigos if x is not a]
    hoje = "".join(
        f'<li><span class="blog-rotulo blog-{e(x.tema)}">{e(x.rotulo)}</span> '
        f'<a href="../{e(x.slug)}/">{e(x.titulo)}</a></li>' for x in mais_hoje)
    hoje_html = (f'<section class="blog-bloco"><h2>Mais do Radar de hoje</h2><ul class="blog-lista-links">{hoje}</ul>'
                 f'<p><a href="../">Ver o Radar TECHDIM de {e(data_curta(a.data))} completo →</a></p></section>'
                 if mais_hoje else "")
    rel = relacionados(a, todos)
    rel_html = ""
    if rel:
        itens = "".join(f'<li><a href="{p}{e(b.caminho)}">{e(b.titulo)}</a> '
                        f'<time datetime="{e(b.data)}">({e(data_curta(b.data))})</time></li>' for b in rel)
        rel_html = f'<section class="blog-bloco"><h2>Leia também</h2><ul class="blog-lista-links">{itens}</ul></section>'
    navdias = _nav_dias(anterior, seguinte, "../../")
    tags = ""
    if a.tags:
        tags = '<p class="blog-tags">' + " ".join(f'<span>#{e(t)}</span>' for t in a.tags) + "</p>"
    corpo = f"""    <article class="container blog-artigo">
      {migalhas_html([("Início", p), ("Blog", f"{p}blog/"), (f"Radar {data_curta(a.data)}", "../"), (a.rotulo, None)])}
      <header class="blog-topo">
        <p class="blog-rotulo-linha"><span class="blog-rotulo blog-{e(a.tema)}">{e(a.rotulo)}</span> <time datetime="{e(a.data)}">{e(data_extenso(a.data))}</time></p>
        <h1>{e(a.titulo)}</h1>
        <p class="blog-lead">{e(a.lead)}</p>
      </header>
      {capa}
      <section class="blog-bloco">
        <h2>{e(resumo_t)}</h2>
        <ul class="blog-pontos">{pontos}</ul>
        {fecho}
      </section>
      {motivo}
      {passos}
      {lista_fontes(a.fontes)}
      <aside class="blog-cta" aria-label="Fale com a TECHDIM">
        <p><strong>{e(cta)}</strong> A TECHDIM cuida de infraestrutura, segurança da informação, automação com IA e software sob medida, em Campinas e para todo o Brasil.</p>
        <p><a class="blog-botao" href="{p}#contato">Fale com a TECHDIM</a></p>
      </aside>
      {hoje_html}
      {rel_html}
      {navdias}
      {tags}
      <p class="blog-aviso">Este texto resume as fontes citadas na data de publicação. Confira sempre o aviso oficial do fabricante antes de agir em produção.</p>
    </article>"""
    imagem = a.capa_url if a.tem_capa else PREVIEW_URL
    m = Meta(
        titulo=a.titulo if len(a.titulo) > 52 else f"{a.titulo} | {MARCA}",
        descricao=a.descricao, canonico=a.url, og_tipo="article", imagem=imagem,
        imagem_tamanho=CAPA_TAMANHO if a.tem_capa else PREVIEW_TAMANHO, imagem_alt=a.alt_capa,
        publicado=a.publicado_em, secao=a.rotulo, tags=tuple(a.tags),
        ld=(artigo_ld(a, imagem), migalhas_ld([
            ("Início", f"{BASE_URL}/"), ("Blog", f"{BASE_URL}/blog/"),
            (f"Radar {data_curta(a.data)}", dia.url), (a.titulo, a.url)])),
    )
    return pagina(m, p, corpo)


def artigo_ld(a: Artigo, imagem: str) -> dict:
    ld = {
        "@context": "https://schema.org", "@type": "BlogPosting",
        "headline": truncar(a.titulo, 110), "description": a.descricao, "inLanguage": "pt-BR",
        "datePublished": a.publicado_em, "dateModified": a.publicado_em,
        "mainEntityOfPage": {"@type": "WebPage", "@id": a.url},
        "url": a.url, "articleSection": a.rotulo,
        "image": {"@type": "ImageObject", "url": imagem,
                  "width": CAPA_TAMANHO[0] if a.tem_capa else PREVIEW_TAMANHO[0],
                  "height": CAPA_TAMANHO[1] if a.tem_capa else PREVIEW_TAMANHO[1]},
        "author": {"@type": "Organization", "name": EMPRESA, "url": f"{BASE_URL}/"},
        "publisher": organizacao_curta(),
        "isPartOf": {"@type": "Blog", "@id": f"{BASE_URL}/blog/#blog", "name": f"Blog {MARCA}", "url": f"{BASE_URL}/blog/"},
    }
    if a.tags:
        ld["keywords"] = ", ".join(a.tags)
    if a.fontes:
        ld["citation"] = [{"@type": "CreativeWork", "name": d, "url": u} for d, u in a.fontes]
    return ld


def _nav_dias(anterior: Dia | None, seguinte: Dia | None, p: str) -> str:
    """Links para o Radar do dia anterior e do seguinte; `p` é o caminho relativo até blog/."""
    ant = (f'<a class="blog-dia-ant" href="{p}{anterior.data}/" rel="prev">'
           f'← Radar de {e(data_curta(anterior.data))}</a>') if anterior else ""
    seg = (f'<a class="blog-dia-seg" href="{p}{seguinte.data}/" rel="next">'
           f'Radar de {e(data_curta(seguinte.data))} →</a>') if seguinte else ""
    if not (ant or seg):
        return ""
    return f'<nav class="blog-nav-dias" aria-label="Outros dias">{ant}{seg}</nav>'


def html_dia(dia: Dia, anterior: Dia | None, seguinte: Dia | None) -> str:
    p = "../../"
    cartoes = "\n      ".join(cartao_artigo(a, p, dentro_do_dia=True) for a in dia.artigos)
    corpo = f"""    <section class="container blog-lista">
      {migalhas_html([("Início", p), ("Blog", f"{p}blog/"), (f"Radar {data_curta(dia.data)}", None)])}
      <header class="blog-topo">
        <p class="blog-rotulo-linha"><span class="blog-rotulo">Radar {MARCA}</span> <time datetime="{e(dia.data)}">{e(data_extenso(dia.data))}</time></p>
        <h1>Radar {MARCA} · {e(data_curta(dia.data))}</h1>
        <p class="blog-lead">O resumo do dia para donos de empresas e gestores de TI: notícia de tecnologia, alerta de segurança, dica prática e um serviço da {MARCA}, cada um com artigo completo e fontes.</p>
      </header>
      <div class="blog-grade">
      {cartoes}
      </div>
      {_nav_dias(anterior, seguinte, "../")}
    </section>"""
    m = Meta(
        titulo=dia.titulo, descricao=dia.descricao, canonico=dia.url,
        ld=({"@context": "https://schema.org", "@type": "CollectionPage", "name": dia.titulo,
             "url": dia.url, "description": dia.descricao, "inLanguage": "pt-BR",
             "datePublished": f"{dia.data}T06:00:00-03:00",
             "isPartOf": {"@type": "Blog", "@id": f"{BASE_URL}/blog/#blog", "url": f"{BASE_URL}/blog/"},
             "mainEntity": {"@type": "ItemList", "itemListElement": [
                 {"@type": "ListItem", "position": i, "url": a.url, "name": a.titulo}
                 for i, a in enumerate(dia.artigos, start=1)]}},
            migalhas_ld([("Início", f"{BASE_URL}/"), ("Blog", f"{BASE_URL}/blog/"),
                         (f"Radar {data_curta(dia.data)}", dia.url)])),
    )
    return pagina(m, p, corpo)


def cartao_dia(d: Dia, p: str) -> str:
    itens = "".join(f'<li><a href="{p}{e(a.caminho)}">{e(a.titulo)}</a></li>' for a in d.artigos)
    return f"""<article class="blog-cartao">
        <p class="blog-rotulo-linha"><time datetime="{e(d.data)}">{e(data_extenso(d.data))}</time></p>
        <h3><a href="{p}{e(d.caminho)}">Radar {MARCA} · {e(data_curta(d.data))}</a></h3>
        <ul>{itens}</ul>
        <a class="blog-mais" href="{p}{e(d.caminho)}">Ver o resumo do dia →</a>
      </article>"""


def html_indice(dias: list[Dia]) -> str:
    """Índice do blog: os dias mais recentes e os links dos arquivos mensais."""
    p = "../"
    recentes = list(reversed(dias))[:POR_PAGINA_INDICE]
    meses = sorted({d.data[:7] for d in dias}, reverse=True)
    cartoes = "\n      ".join(cartao_dia(d, p) for d in recentes)
    arquivo = "".join(f'<li><a href="{p}blog/arquivo/{m}/">{e(mes_extenso(m))}</a></li>' for m in meses)
    titulo = f"Blog {MARCA}: radar diário de tecnologia, segurança e IA para empresas"
    desc = ("Todo dia, notícia de tecnologia, alerta de segurança, dica prática e serviços de TI "
            "para pequenas e médias empresas, sempre com as fontes. Campinas e todo o Brasil.")
    corpo = f"""    <section class="container blog-lista">
      {migalhas_html([("Início", p), ("Blog", None)])}
      <header class="blog-topo">
        <p class="blog-rotulo">Blog {MARCA}</p>
        <h1>Radar diário de tecnologia e segurança</h1>
        <p class="blog-lead">{e(desc)}</p>
      </header>
      <div class="blog-grade">
      {cartoes}
      </div>
      <section class="blog-bloco" aria-labelledby="arq"><h2 id="arq">Arquivo por mês</h2><ul class="blog-lista-links">{arquivo}</ul></section>
    </section>"""
    artigos = [a for d in reversed(dias) for a in d.artigos][:20]
    m = Meta(
        titulo=titulo, descricao=desc, canonico=f"{BASE_URL}/blog/",
        ld=({"@context": "https://schema.org", "@type": "Blog", "@id": f"{BASE_URL}/blog/#blog",
             "name": f"Blog {MARCA}", "url": f"{BASE_URL}/blog/", "description": desc, "inLanguage": "pt-BR",
             "publisher": organizacao_curta(),
             "blogPost": [{"@type": "BlogPosting", "headline": truncar(a.titulo, 110), "url": a.url,
                           "datePublished": a.publicado_em} for a in artigos]},
            migalhas_ld([("Início", f"{BASE_URL}/"), ("Blog", f"{BASE_URL}/blog/")])),
    )
    return pagina(m, p, corpo)


def html_arquivo(mes: str, dias: list[Dia]) -> str:
    p = "../../../"
    cartoes = "\n      ".join(cartao_dia(d, p) for d in reversed(dias))
    titulo = f"Arquivo do blog {MARCA}: {mes_extenso(mes)}"
    desc = f"Todos os resumos diários do blog {MARCA} em {mes_extenso(mes)}: tecnologia, segurança, dicas e serviços."
    url = f"{BASE_URL}/blog/arquivo/{mes}/"
    corpo = f"""    <section class="container blog-lista">
      {migalhas_html([("Início", p), ("Blog", f"{p}blog/"), (mes_extenso(mes), None)])}
      <header class="blog-topo">
        <p class="blog-rotulo">Arquivo</p>
        <h1>{e(mes_extenso(mes).capitalize())}</h1>
        <p class="blog-lead">{e(desc)}</p>
      </header>
      <div class="blog-grade">
      {cartoes}
      </div>
    </section>"""
    m = Meta(
        titulo=titulo, descricao=desc, canonico=url,
        ld=({"@context": "https://schema.org", "@type": "CollectionPage", "name": titulo, "url": url,
             "description": desc, "inLanguage": "pt-BR",
             "isPartOf": {"@type": "Blog", "@id": f"{BASE_URL}/blog/#blog", "url": f"{BASE_URL}/blog/"}},
            migalhas_ld([("Início", f"{BASE_URL}/"), ("Blog", f"{BASE_URL}/blog/"), (mes_extenso(mes), url)])),
    )
    return pagina(m, p, corpo)


CSS = """/* Blog TECHDIM: complementa o styles.css do site */
.blog-artigo, .blog-lista { max-width: 860px; padding-top: 7rem; padding-bottom: 4rem; }
.blog-migalhas { font-family: var(--font-mono); font-size: .8rem; color: var(--text-muted); margin-bottom: 1.2rem; line-height: 1.6; }
.blog-migalhas a { color: var(--cyan-neon); text-decoration: none; }
.blog-migalhas a:hover { text-decoration: underline; }
.blog-topo h1 { font-family: var(--font-display); font-size: clamp(1.8rem, 4vw, 2.7rem); line-height: 1.15; color: var(--text-pure); margin: .4rem 0 1rem; }
.blog-rotulo-linha { display: flex; flex-wrap: wrap; gap: .6rem 1rem; align-items: center; font-family: var(--font-mono); font-size: .82rem; color: var(--text-muted); }
.blog-rotulo { display: inline-block; font-family: var(--font-mono); font-size: .72rem; letter-spacing: .06em; text-transform: uppercase; color: var(--cyan-neon); }
.blog-hacker { color: var(--rose-crit); }
.blog-dica { color: var(--amber-warn); }
.blog-servico { color: var(--emerald-live); }
.blog-lead { color: var(--text-muted); font-size: 1.1rem; line-height: 1.65; max-width: 64ch; }
.blog-capa { margin: 1.8rem 0; }
.blog-capa img { display: block; width: 100%; max-width: 480px; height: auto; border-radius: var(--radius-md); border: 1px solid var(--border-cyber); }
.blog-capa figcaption { font-size: .8rem; color: var(--text-dark); margin-top: .5rem; }
.blog-bloco { margin-top: 2.2rem; padding-top: 1.4rem; border-top: 1px solid var(--border-subtle); }
.blog-bloco h2 { font-family: var(--font-display); font-size: clamp(1.25rem, 2.6vw, 1.6rem); line-height: 1.25; color: var(--text-pure); margin-bottom: .9rem; }
.blog-pontos, .blog-passos, .blog-fontes, .blog-lista-links { margin: 0 0 1rem 1.2rem; color: var(--text-main); line-height: 1.7; }
.blog-lista-links { list-style: none; margin-left: 0; }
.blog-pontos li, .blog-passos li, .blog-fontes li, .blog-lista-links li { margin-bottom: .55rem; }
.blog-bloco p { color: var(--text-main); line-height: 1.7; margin-bottom: .8rem; }
.blog-fecho { color: var(--text-pure); font-weight: 600; line-height: 1.6; margin: 1rem 0; }
.blog-fontes a, .blog-bloco a, .blog-lista-links a { color: var(--cyan-neon); }
.blog-cta { margin-top: 2.4rem; padding: 1.4rem 1.5rem; border: 1px solid var(--border-cyber); border-radius: var(--radius-md); background: var(--bg-card); }
.blog-cta p { color: var(--text-main); line-height: 1.65; margin-bottom: .9rem; }
.blog-botao { display: inline-block; padding: .8rem 1.4rem; border-radius: var(--radius-sm); background: var(--cyan-neon); color: #030712; font-weight: 700; text-decoration: none; }
.blog-botao:hover, .blog-botao:focus-visible { box-shadow: 0 0 20px var(--cyan-glow); }
.blog-tags { margin-top: 1.6rem; display: flex; flex-wrap: wrap; gap: .5rem; font-family: var(--font-mono); font-size: .78rem; color: var(--text-muted); }
.blog-aviso { margin-top: 1.6rem; font-size: .85rem; color: var(--text-dark); line-height: 1.6; }
.blog-nav-dias { display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-top: 2.2rem; font-family: var(--font-mono); font-size: .85rem; }
.blog-nav-dias a { color: var(--cyan-neon); text-decoration: none; }
.blog-grade { display: grid; gap: 1.2rem; margin-top: 2rem; }
.blog-cartao { padding: 1.4rem 1.5rem; border: 1px solid var(--border-cyber); border-radius: var(--radius-md); background: var(--bg-card); transition: background .25s var(--ease), transform .25s var(--ease); }
.blog-cartao:hover, .blog-cartao:focus-within { background: var(--bg-card-hover); transform: translateY(-2px); }
.blog-cartao h3 { font-family: var(--font-display); font-size: 1.3rem; line-height: 1.3; margin: .4rem 0 .7rem; }
.blog-cartao h3 a { color: var(--text-pure); text-decoration: none; }
.blog-cartao p { color: var(--text-muted); line-height: 1.6; margin-bottom: .7rem; }
.blog-cartao ul { margin: 0 0 .9rem 1.1rem; color: var(--text-muted); line-height: 1.55; }
.blog-cartao li a { color: var(--text-main); text-decoration: none; }
.blog-mais { font-family: var(--font-mono); font-size: .82rem; color: var(--cyan-neon); text-decoration: none; }
.blog-rodape-nav { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.blog-rodape-nav a { color: var(--cyan-neon); }
/* Bloco "Blog" da página inicial */
.blog-home { padding: 5rem 0; }
.blog-home-grid { display: grid; gap: 1.2rem; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); }
.blog-home-card { display: block; padding: 1.3rem 1.4rem; border: 1px solid var(--border-cyber); border-radius: var(--radius-md); background: var(--bg-card); text-decoration: none; transition: background .25s var(--ease), transform .25s var(--ease); }
.blog-home-card:hover, .blog-home-card:focus-visible { background: var(--bg-card-hover); transform: translateY(-2px); }
.blog-home-card h3 { font-family: var(--font-display); font-size: 1.1rem; line-height: 1.35; color: var(--text-pure); margin: .5rem 0 .6rem; }
.blog-home-card p { color: var(--text-muted); font-size: .92rem; line-height: 1.55; }
.blog-home-mais { text-align: center; margin-top: 2rem; font-family: var(--font-mono); font-size: .9rem; }
.blog-home-mais a { color: var(--cyan-neon); }
@media (max-width: 640px) { .blog-artigo, .blog-lista { padding-top: 6rem; } }
"""


# --------------------------------------------------------- feed, sitemap, robots ---

def feed_xml(dias: list[Dia]) -> str:
    artigos = [a for d in reversed(dias) for a in sorted(d.artigos, key=lambda x: -x.indice)][:40]
    itens = []
    for a in artigos:
        quando = dt.datetime.fromisoformat(a.publicado_em)
        itens.append(f"""    <item>
      <title>{e(a.titulo)}</title>
      <link>{e(a.url)}</link>
      <guid isPermaLink="true">{e(a.url)}</guid>
      <pubDate>{email.utils.format_datetime(quando)}</pubDate>
      <category>{e(a.rotulo)}</category>
      <description>{e(a.descricao)}</description>
    </item>""")
    ultima = email.utils.format_datetime(dt.datetime.fromisoformat(artigos[0].publicado_em)) if artigos else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>Blog {MARCA}</title>
    <link>{BASE_URL}/blog/</link>
    <atom:link href="{BASE_URL}/blog/feed.xml" rel="self" type="application/rss+xml" />
    <description>Radar diário de tecnologia, segurança e IA para empresas.</description>
    <language>pt-BR</language>
    <lastBuildDate>{ultima}</lastBuildDate>
{chr(10).join(itens)}
  </channel>
</rss>
"""


def _outras_urls_do_sitemap(site: pathlib.Path) -> list[tuple[str, str]]:
    """Entradas já existentes do sitemap que ainda valem: mesmo endereço do site e fora do blog.

    Entradas de outro domínio não podem constar num sitemap deste site e ficam de fora.
    """
    arq = site / "sitemap.xml"
    if not arq.exists():
        return []
    try:
        raiz = ET.parse(arq).getroot()
    except ET.ParseError:
        return []
    achadas = []
    for u in raiz.iter(f"{{{SITEMAP_NS}}}url"):
        loc = (u.findtext(f"{{{SITEMAP_NS}}}loc") or "").strip()
        lastmod = (u.findtext(f"{{{SITEMAP_NS}}}lastmod") or "").strip()
        alvo = urllib.parse.urlparse(loc)
        if alvo.netloc != HOST or not alvo.path.startswith(CAMINHO_BASE):
            continue
        if alvo.path.startswith(f"{CAMINHO_BASE}/blog") or alvo.path.rstrip("/") == CAMINHO_BASE:
            continue
        achadas.append((loc, lastmod))
    return achadas


def sitemap_xml(site: pathlib.Path, dias: list[Dia]) -> str:
    ultimo = dias[-1].data if dias else dt.date.today().isoformat()
    entradas: list[tuple[str, str, list[str]]] = [(f"{BASE_URL}/", ultimo, []), (f"{BASE_URL}/blog/", ultimo, [])]
    entradas += [(loc, lm or ultimo, []) for loc, lm in _outras_urls_do_sitemap(site)]
    for mes in sorted({d.data[:7] for d in dias}, reverse=True):
        do_mes = [d.data for d in dias if d.data.startswith(mes)]
        entradas.append((f"{BASE_URL}/blog/arquivo/{mes}/", max(do_mes), []))
    for d in reversed(dias):
        entradas.append((d.url, d.data, []))
        for a in d.artigos:
            entradas.append((a.url, a.data, [a.capa_url] if a.tem_capa else []))
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              f'<urlset xmlns="{SITEMAP_NS}" xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for loc, lastmod, imagens in entradas:
        linhas.append("  <url>")
        linhas.append(f"    <loc>{e(loc)}</loc>")
        linhas.append(f"    <lastmod>{e(lastmod)}</lastmod>")
        for img in imagens:
            linhas.append(f"    <image:image><image:loc>{e(img)}</image:loc></image:image>")
        linhas.append("  </url>")
    linhas.append("</urlset>")
    return "\n".join(linhas) + "\n"


def atualizar_robots(site: pathlib.Path) -> bool:
    """Aponta a linha Sitemap do robots.txt para o sitemap deste site."""
    arq = site / "robots.txt"
    alvo = f"Sitemap: {BASE_URL}/sitemap.xml"
    texto = arq.read_text(encoding="utf-8") if arq.exists() else "User-agent: *\nAllow: /\n"
    if re.search(r"(?mi)^Sitemap:.*$", texto):
        novo = re.sub(r"(?mi)^Sitemap:.*$", alvo, texto)
    else:
        novo = texto.rstrip("\n") + f"\n\n{alvo}\n"
    if novo != texto or not arq.exists():
        arq.write_text(novo, encoding="utf-8")
        return True
    return False


# ------------------------------------------------------------- página inicial ---

def carregar_seo(site: pathlib.Path) -> dict:
    """seo.json do site: códigos de verificação dos buscadores (preenchidos pelo dono)."""
    arq = site / "seo.json"
    if not arq.exists():
        return {}
    try:
        dados = json.loads(arq.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {}
    except json.JSONDecodeError:
        log.warning("seo.json inválido; ignorado")
        return {}


def _bloco(texto: str, nome: str, conteudo: str, ancora: re.Pattern[str], recuo: str, sufixo: str) -> str:
    """Põe `conteudo` entre <!-- nome:inicio --> e <!-- nome:fim -->, trocando o que já houver."""
    marca_ini, marca_fim = f"<!-- {nome}:inicio -->", f"<!-- {nome}:fim -->"
    miolo = f"{marca_ini}\n{conteudo}\n{recuo}{marca_fim}"
    if marca_ini in texto and marca_fim in texto:
        antes, resto = texto.split(marca_ini, 1)
        _, depois = resto.split(marca_fim, 1)
        return antes + miolo + depois
    achou = ancora.search(texto)
    if not achou:
        log.warning("âncora do bloco %s não encontrada na página inicial", nome)
        return texto
    return texto[: achou.start()] + recuo + miolo + sufixo + texto[achou.start():]


def _head_seo(site: pathlib.Path) -> str:
    seo = carregar_seo(site)
    linhas = []
    if seo.get("google_site_verification"):
        linhas.append(f'  <meta name="google-site-verification" content="{e(seo["google_site_verification"])}" />')
    if seo.get("bing_site_verification"):
        linhas.append(f'  <meta name="msvalidate.01" content="{e(seo["bing_site_verification"])}" />')
    linhas += [
        f'  <link rel="alternate" hreflang="pt-BR" href="{BASE_URL}/" />',
        f'  <link rel="alternate" hreflang="x-default" href="{BASE_URL}/" />',
        f'  <link rel="alternate" type="application/rss+xml" title="Blog {MARCA}" href="{BASE_URL}/blog/feed.xml" />',
        '  <link rel="sitemap" type="application/xml" title="Sitemap" href="sitemap.xml" />',
        f'  <meta property="og:image:width" content="{PREVIEW_TAMANHO[0]}" />',
        f'  <meta property="og:image:height" content="{PREVIEW_TAMANHO[1]}" />',
        '  <meta property="og:image:alt" content="TECHDIM — cibersegurança, nuvem e IA para empresas" />',
        '  <meta name="twitter:image:alt" content="TECHDIM — cibersegurança, nuvem e IA para empresas" />',
        '  <link rel="stylesheet" href="blog/blog.css" />',
        recuar(jsonld({"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "@id": f"{BASE_URL}/#website", "url": f"{BASE_URL}/", "name": MARCA,
             "inLanguage": "pt-BR", "publisher": {"@id": f"{BASE_URL}/#organization"}},
            {"@type": "Blog", "@id": f"{BASE_URL}/blog/#blog", "url": f"{BASE_URL}/blog/",
             "name": f"Blog {MARCA}", "inLanguage": "pt-BR",
             "description": "Radar diário de tecnologia, segurança e IA para empresas.",
             "publisher": {"@id": f"{BASE_URL}/#organization"}},
        ]})),
    ]
    return "\n".join(linhas)


def _secao_blog_home(dias: list[Dia]) -> str:
    cards = []
    artigos = [a for d in reversed(dias) for a in d.artigos if a.tema != "servico"][:6]
    for a in artigos:
        cards.append(f"""          <a class="blog-home-card" href="{e(a.caminho)}">
            <span class="blog-rotulo blog-{e(a.tema)}">{e(a.rotulo)}</span>
            <h3>{e(a.titulo)}</h3>
            <p>{e(truncar(a.descricao, 120))}</p>
          </a>""")
    grade = "\n".join(cards)
    return f"""    <section class="blog-home" id="blog" aria-labelledby="blog-titulo">
      <div class="container">
        <div class="section-head">
          <h2 id="blog-titulo">BLOG <span class="gradient-text-cyber">TECHDIM</span></h2>
          <p>Todo dia, notícia de tecnologia, alerta de segurança e dica prática para empresas, sempre com as fontes.</p>
        </div>
        <div class="blog-home-grid">
{grade}
        </div>
        <p class="blog-home-mais"><a href="blog/">Ver todos os posts →</a> · <a href="blog/feed.xml">Assinar o feed RSS</a></p>
      </div>
    </section>"""


def _trocar(texto: str, padrao: str, novo: str) -> str:
    return re.sub(padrao, lambda _: novo, texto, count=1)


def _enriquecer_organizacao(texto: str) -> str:
    """Completa o JSON-LD da empresa (endereço da página, logo, redes) sem tirar nada que já existe."""
    achou = re.search(r'(<script type="application/ld\+json">\s*)(\{.*?\})(\s*</script>)', texto, re.S)
    if not achou:
        return texto
    try:
        org = json.loads(achou.group(2))
    except json.JSONDecodeError:
        return texto
    if org.get("@type") != "ProfessionalService":
        return texto
    org["@id"] = f"{BASE_URL}/#organization"
    org["url"] = f"{BASE_URL}/"
    org.setdefault("logo", LOGO_URL)
    org.setdefault("image", PREVIEW_URL)
    org["sameAs"] = REDES
    org.setdefault("areaServed", {"@type": "Country", "name": "Brasil"})
    fundador = org.get("founder")
    if isinstance(fundador, dict):
        fundador.setdefault("sameAs", [FUNDADOR_LINKEDIN])
    corpo = json.dumps(org, ensure_ascii=False, indent=2).replace("</", "<\\/")
    corpo = "\n".join("    " + linha if linha else linha for linha in corpo.splitlines()).lstrip()
    return texto[: achou.start(2)] + corpo + texto[achou.end(2):]


def atualizar_home(site: pathlib.Path, dias: list[Dia]) -> bool:
    """Ajusta a página inicial para os buscadores e liga os posts mais novos a ela."""
    arq = site / "index.html"
    original = arq.read_text(encoding="utf-8")
    t = original
    canon = f"{BASE_URL}/"
    t = _trocar(t, r'<link rel="canonical" href="[^"]*" />', f'<link rel="canonical" href="{canon}" />')
    t = _trocar(t, r'<meta property="og:url" content="[^"]*" />', f'<meta property="og:url" content="{canon}" />')
    t = _trocar(t, r'<meta property="twitter:url" content="[^"]*" />', f'<meta property="twitter:url" content="{canon}" />')
    t = _trocar(t, r'<meta property="og:image" content="[^"]*" />', f'<meta property="og:image" content="{PREVIEW_URL}" />')
    t = _trocar(t, r'<meta property="twitter:image" content="[^"]*" />', f'<meta property="twitter:image" content="{PREVIEW_URL}" />')
    t = _trocar(t, r'<meta name="robots" content="[^"]*" />', f'<meta name="robots" content="{ROBOTS}" />')
    t = _enriquecer_organizacao(t)
    t = _bloco(t, "seo", _head_seo(site), re.compile(r"</head>"), recuo="  ", sufixo="\n")
    if dias:
        t = _bloco(t, "blog-recentes", _secao_blog_home(dias),
                   re.compile(r"[ \t]*<!-- =+\s*\n\s*Contact & Conversion Section"),
                   recuo="    ", sufixo="\n\n")
    if t != original:
        arq.write_text(t, encoding="utf-8")
    return t != original


# ---------------------------------------------------------------------- geral ---

def escrever(caminho: pathlib.Path, texto: str) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    if caminho.exists() and caminho.read_text(encoding="utf-8") == texto:
        return
    caminho.write_text(texto, encoding="utf-8")


def gerar(site: pathlib.Path, forcar_imagens: bool = False) -> list[Dia]:
    """Gera todo o blog no repositório do site e devolve os dias (do mais antigo ao mais novo)."""
    dias = carregar_dias()
    blog = site / "blog"
    blog.mkdir(exist_ok=True)
    todos = [a for d in dias for a in d.artigos]

    # endereços atuais de cada dia; pastas de artigo que sumiram da pauta saem do site
    for d in dias:
        pasta_dia = blog / d.data
        slugs = {a.slug for a in d.artigos}
        if pasta_dia.is_dir():
            for sub in pasta_dia.iterdir():
                if sub.is_dir() and sub.name not in slugs:
                    shutil.rmtree(sub)
        for a in d.artigos:
            capa = pasta_dia / a.slug / "capa.jpg"
            if forcar_imagens or not capa.exists():
                renderizar_capa(a.data, a.tema, capa)
            a.tem_capa = capa.exists()

    for i, d in enumerate(dias):
        anterior = dias[i - 1] if i > 0 else None
        seguinte = dias[i + 1] if i + 1 < len(dias) else None
        escrever(blog / d.data / "index.html", html_dia(d, anterior, seguinte))
        for a in d.artigos:
            escrever(blog / d.data / a.slug / "index.html", html_artigo(a, d, todos, anterior, seguinte))

    escrever(blog / "blog.css", CSS)
    if dias:
        escrever(blog / "index.html", html_indice(dias))
        for mes in sorted({d.data[:7] for d in dias}):
            escrever(blog / "arquivo" / mes / "index.html", html_arquivo(mes, [d for d in dias if d.data.startswith(mes)]))
        escrever(blog / "feed.xml", feed_xml(dias))
    escrever(site / "sitemap.xml", sitemap_xml(site, dias))
    atualizar_robots(site)
    atualizar_home(site, dias)
    return dias


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", required=True, help="pasta do repositório do site")
    ap.add_argument("--forcar-imagens", action="store_true", help="redesenha a capa de todos os artigos")
    ap.add_argument("--data", action="append", help="obsoleto: todos os dias são sempre regenerados (idempotente)")
    args = ap.parse_args()
    site = pathlib.Path(args.site)
    if not (site / "index.html").exists():
        print(f"{site} não parece ser a pasta do site (sem index.html)", file=sys.stderr)
        return 2
    dias = gerar(site, forcar_imagens=args.forcar_imagens)
    artigos = sum(len(d.artigos) for d in dias)
    print(f"blog: {len(dias)} dia(s) e {artigos} artigo(s) no site")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
