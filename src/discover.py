"""Descobre Page ID e IG Business Account ID a partir do token.

Roda uma vez, manualmente (workflow 'descobrir-ids'), para você não precisar
caçar esses números na interface da Meta. Nenhum id é segredo — podem ir
direto nas variáveis do repositório.
"""
from __future__ import annotations

import logging
import sys

import config
from publishers.common import PublishError, request

log = logging.getLogger("discover")


def main() -> int:
    creds = config.Credentials()
    if not creds.meta_token:
        log.error("META_ACCESS_TOKEN não configurado")
        return 1

    me = request(
        "GET", f"{config.GRAPH}/me",
        params={"fields": "id,name", "access_token": creds.meta_token},
    ).json()
    print(f"\nConta do token: {me.get('name')} (id {me.get('id')})\n")

    contas = request(
        "GET",
        f"{config.GRAPH}/me/accounts",
        params={
            "fields": "id,name,instagram_business_account{id,username}",
            "access_token": creds.meta_token,
        },
    ).json()

    paginas = contas.get("data", [])
    if not paginas:
        print(
            "Nenhuma página encontrada. Provavelmente o token é de usuário sem a\n"
            "permissão pages_show_list, ou já é um token de página."
        )
        return 1

    print("Páginas que este token administra:\n")
    for p in paginas:
        ig = p.get("instagram_business_account") or {}
        print(f"  Página  : {p.get('name')}")
        print(f"  FB_PAGE_ID = {p.get('id')}")
        if ig:
            print(f"  IG_USER_ID = {ig.get('id')}   (@{ig.get('username', '?')})")
        else:
            print("  IG_USER_ID = (nenhum Instagram comercial vinculado a esta página)")
        print()

    print("Copie os valores acima para as Variables do repositório.")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        sys.exit(main())
    except PublishError as exc:
        log.error("%s", exc)
        sys.exit(1)
