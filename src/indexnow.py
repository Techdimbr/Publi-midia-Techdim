"""Avisa os buscadores das páginas novas ou alteradas do blog (protocolo IndexNow).

IndexNow é aceito por Bing, Yandex, Naver, Seznam e Yep (e, por tabela, por quem usa o
índice do Bing, como DuckDuckGo e Ecosia). O Google NÃO participa: para ele valem o sitemap
enviado no Search Console, o feed RSS, os links internos e os links vindos das redes sociais
(veja docs/SEO.md).

A chave é pública por desenho: fica num arquivo <chave>.txt na raiz do site, e é esse
arquivo que prova ao buscador que o site é seu.

Uso:
    python src/indexnow.py --site /caminho/do/repo-do-site              # páginas do último commit
    python src/indexnow.py --site /caminho/do/repo-do-site --todas      # todas as do sitemap
    python src/indexnow.py --site ... --simular                         # só mostra o que enviaria
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

BASE_URL = "https://techdimbr.github.io/techdimbr"
HOST = urllib.parse.urlparse(BASE_URL).netloc
CAMINHO_BASE = urllib.parse.urlparse(BASE_URL).path
ENDPOINT = "https://api.indexnow.org/indexnow"
SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
LIMITE_POR_ENVIO = 10000  # limite do protocolo


def achar_chave(site: pathlib.Path) -> str | None:
    """Chave do IndexNow: a de seo.json ou a de um arquivo <chave>.txt com o mesmo texto na raiz."""
    cfg = site / "seo.json"
    if cfg.exists():
        try:
            chave = str(json.loads(cfg.read_text(encoding="utf-8")).get("indexnow_key", "")).strip()
        except json.JSONDecodeError:
            chave = ""
        if chave and (site / f"{chave}.txt").exists():
            return chave
    for arq in sorted(site.glob("*.txt")):
        if re.fullmatch(r"[A-Za-z0-9-]{16,128}", arq.stem) and arq.read_text(encoding="utf-8").strip() == arq.stem:
            return arq.stem
    return None


def url_da_pagina(caminho: str) -> str | None:
    """Endereço público de um arquivo do site; só páginas HTML interessam."""
    if caminho == "index.html":
        return f"{BASE_URL}/"
    if caminho.startswith("blog/") and caminho.endswith("/index.html"):
        return f"{BASE_URL}/{caminho[: -len('index.html')]}"
    return None


def urls_do_commit(site: pathlib.Path, commit: str = "HEAD") -> list[str]:
    """Páginas HTML criadas ou alteradas pelo commit."""
    saida = subprocess.run(
        ["git", "-C", str(site), "show", "--name-only", "--pretty=format:", "--diff-filter=AM", commit],
        capture_output=True, text=True, check=True,
    ).stdout
    urls = [u for u in (url_da_pagina(linha.strip()) for linha in saida.splitlines()) if u]
    return sorted(set(urls))


def urls_do_sitemap(site: pathlib.Path) -> list[str]:
    raiz = ET.parse(site / "sitemap.xml").getroot()
    urls = []
    for u in raiz.iter(f"{SITEMAP_NS}url"):
        loc = (u.findtext(f"{SITEMAP_NS}loc") or "").strip()
        alvo = urllib.parse.urlparse(loc)
        if alvo.netloc == HOST and alvo.path.startswith(CAMINHO_BASE):
            urls.append(loc)
    return sorted(set(urls))


def esta_no_ar(url: str, timeout: int = 15) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
            return r.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def esperar_no_ar(urls: list[str], tentativas: int = 30, intervalo: int = 10) -> bool:
    """O GitHub Pages leva de segundos a alguns minutos para publicar; avisar antes dá 404 ao buscador."""
    for i in range(tentativas):
        if all(esta_no_ar(u) for u in urls):
            return True
        if i < tentativas - 1:
            time.sleep(intervalo)
    return False


def corpo_do_envio(urls: list[str], chave: str) -> dict:
    return {
        "host": HOST,
        "key": chave,
        "keyLocation": f"{BASE_URL}/{chave}.txt",
        "urlList": urls,
    }


def enviar(urls: list[str], chave: str, endpoint: str = ENDPOINT) -> int:
    """Envia as URLs (em lotes) e devolve o pior código HTTP; 200 e 202 são sucesso."""
    pior = 200
    for i in range(0, len(urls), LIMITE_POR_ENVIO):
        lote = urls[i: i + LIMITE_POR_ENVIO]
        pedido = urllib.request.Request(
            endpoint, data=json.dumps(corpo_do_envio(lote, chave)).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        try:
            with urllib.request.urlopen(pedido, timeout=30) as r:
                codigo = r.status
        except urllib.error.HTTPError as exc:
            codigo = exc.code
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f"IndexNow: sem resposta ({exc})", file=sys.stderr)
            codigo = 599
        print(f"IndexNow: {len(lote)} endereço(s) enviado(s), resposta HTTP {codigo}")
        if codigo not in (200, 202):
            pior = max(pior, codigo)
    return pior


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--site", required=True)
    ap.add_argument("--commit", default="HEAD", help="commit do site cujas páginas serão avisadas")
    ap.add_argument("--todas", action="store_true", help="avisa todas as páginas do sitemap")
    ap.add_argument("--sem-esperar", action="store_true", help="não espera a publicação do GitHub Pages")
    ap.add_argument("--simular", action="store_true", help="só mostra o que seria enviado")
    args = ap.parse_args()

    site = pathlib.Path(args.site)
    chave = achar_chave(site)
    if not chave:
        print("IndexNow: sem chave no site (seo.json / <chave>.txt); nada enviado", file=sys.stderr)
        return 2
    urls = urls_do_sitemap(site) if args.todas else urls_do_commit(site, args.commit)
    if not urls:
        print("IndexNow: nenhuma página nova ou alterada; nada a enviar")
        return 0
    if args.simular:
        print(json.dumps(corpo_do_envio(urls, chave), ensure_ascii=False, indent=2))
        return 0
    if not args.sem_esperar and not esperar_no_ar([f"{BASE_URL}/{chave}.txt", urls[0]]):
        print("IndexNow: o site ainda não publicou a chave/páginas; tente de novo daqui a pouco", file=sys.stderr)
        return 3
    codigo = enviar(urls, chave)
    return 0 if codigo in (200, 202) else 1


if __name__ == "__main__":
    raise SystemExit(main())
