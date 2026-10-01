"""LinkedIn: descobre o URN do perfil/página e confere a validade do token.

  python src/linkedin_ids.py           imprime LINKEDIN_URN de perfil e páginas
  python src/linkedin_ids.py --check   falha se o token estiver vencido

Token do LinkedIn vale 60 dias e, em apps sem programa de parceiro, não se
renova sozinho: o --check roda toda semana para avisar antes.
"""
from __future__ import annotations

import os
import sys

import requests

import config


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": config.LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def main() -> int:
    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    check = "--check" in sys.argv
    if not token:
        print("LINKEDIN_ACCESS_TOKEN não configurado — LinkedIn segue desligado (sem falha).")
        return 0

    r = requests.get("https://api.linkedin.com/v2/userinfo",
                     headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code == 401:
        print("::error::token do LinkedIn vencido ou revogado — gere um novo (vale 60 dias)")
        return 1
    if r.status_code == 426:
        print(f"::error::LinkedIn recusou a versão {config.LINKEDIN_VERSION} — atualize LINKEDIN_VERSION")
        return 1
    perfil = r.json() if r.ok else {}
    if check:
        print(f"token do LinkedIn válido (HTTP {r.status_code})")
        return 0

    if perfil.get("sub"):
        print(f"Perfil: {perfil.get('name', '?')}")
        print(f"  LINKEDIN_URN = urn:li:person:{perfil['sub']}   (publicar como perfil pessoal)\n")
    else:
        print(f"Perfil não lido (HTTP {r.status_code}): o token precisa dos escopos openid e profile.\n")

    o = requests.get(
        "https://api.linkedin.com/rest/organizationAcls",
        params={"q": "roleAssignee", "role": "ADMINISTRATOR", "state": "APPROVED"},
        headers=_headers(token), timeout=30,
    )
    if o.ok and o.json().get("elements"):
        print("Páginas que você administra:")
        for e in o.json()["elements"]:
            print(f"  LINKEDIN_URN = {e.get('organization')}   (publicar como página)")
    else:
        print(f"Páginas não listadas (HTTP {o.status_code}): publicar como página exige o produto\n"
              "Community Management API aprovado no app do LinkedIn.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
