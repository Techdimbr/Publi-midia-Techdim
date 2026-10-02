"""Apaga posts (Facebook, Instagram, LinkedIn) e registra cada exclusão no diário.

  python src/apagar.py --dest /tmp/assets --motivo "teste" \
      --posts "facebook:123_456,instagram:1789,linkedin:urn:li:share:7511"

Exclusão é irreversível: só roda pelo workflow "Apagar posts", disparado à mão.
Falha em um post não impede os demais; cada resultado vira um movimento
("apagou" ou "falhou") no diário do dia.
"""
from __future__ import annotations

import argparse
import logging
import pathlib
import sys
from urllib.parse import quote

import config
import movimentos
from publishers import linkedin
from publishers.common import PublishError, request
from publishers.meta_auth import page_token

log = logging.getLogger("apagar")


def apagar(creds, rede: str, ident: str) -> None:
    if rede in ("facebook", "instagram"):
        token = page_token(creds.meta_token, creds.fb_page_id)
        request("DELETE", f"{config.GRAPH}/{ident}", params={"access_token": token})
    elif rede == "linkedin":
        request(
            "DELETE",
            f"{config.LINKEDIN_API}/rest/posts/{quote(ident, safe='')}",
            headers={**linkedin._headers(creds.linkedin_token), "X-RestLi-Method": "DELETE"},
        )
    else:
        raise PublishError(f"rede desconhecida: {rede}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True)
    ap.add_argument("--posts", required=True, help="rede:id separados por vírgula")
    ap.add_argument("--motivo", default="post de teste")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    creds = config.Credentials()
    eventos, falhas = [], 0
    for item in [x.strip() for x in a.posts.split(",") if x.strip()]:
        rede, _, ident = item.partition(":")
        base = {"rede": rede, "origem": "workflow Apagar posts", "teste": "teste" in a.motivo.lower()}
        try:
            apagar(creds, rede, ident)
        except PublishError as exc:
            falhas += 1
            log.error("%s %s: %s", rede, ident, str(exc)[:200])
            eventos.append({**base, "tipo": "falhou", "detalhe": f"não consegui apagar {ident}: {str(exc)[:160]}"})
        else:
            log.info("apagado: %s %s", rede, ident)
            eventos.append({**base, "tipo": "apagou", "detalhe": f"{ident} — motivo: {a.motivo}"})
    movimentos.registrar(pathlib.Path(a.dest), eventos)
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
