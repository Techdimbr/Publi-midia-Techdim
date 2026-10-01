"""Checa a validade do token da Meta e avisa antes de expirar.

Token de página 'de longa duração' cai se o token de usuário por trás dele
expirar ou se a senha da conta Meta mudar — e aí a publicação falha em
silêncio. Este script roda semanalmente e falha de propósito quando faltam
poucos dias, para o GitHub mandar a notificação.
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import sys

import config
from publishers.common import PublishError, request

log = logging.getLogger("token-check")

ALERTA_DIAS = 10


def check(creds: config.Credentials) -> int:
    if not creds.meta_token:
        log.error("META_ACCESS_TOKEN não configurado")
        return 1

    resp = request(
        "GET",
        f"{config.GRAPH}/debug_token",
        params={"input_token": creds.meta_token, "access_token": creds.meta_token},
    )
    data = resp.json().get("data", {})

    if not data.get("is_valid"):
        log.error("TOKEN INVÁLIDO: %s", data.get("error", {}).get("message", "sem detalhe"))
        return 2

    expira = data.get("expires_at", 0)
    tipo = data.get("type", "?")
    escopos = ", ".join(data.get("scopes", []))
    log.info("token válido | tipo=%s | escopos=%s", tipo, escopos)

    if not expira:
        log.info("token sem data de expiração (não expira)")
        restam = 9999
    else:
        quando = dt.datetime.fromtimestamp(expira, dt.timezone.utc)
        restam = (quando - dt.datetime.now(dt.timezone.utc)).days
        log.info("expira em %s (%d dias)", quando.date().isoformat(), restam)

    faltando = [
        s
        for s in ("pages_manage_posts", "pages_read_engagement", "instagram_content_publish")
        if s not in data.get("scopes", [])
    ]
    if faltando:
        log.warning("escopos ausentes: %s", ", ".join(faltando))

    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as fh:
            fh.write(
                f"### Token da Meta\n\n"
                f"- Tipo: `{tipo}`\n"
                f"- Expira em: **{restam if restam < 9999 else 'nunca'}** dia(s)\n"
                f"- Escopos: `{escopos}`\n"
                + (f"- ⚠️ Escopos ausentes: `{', '.join(faltando)}`\n" if faltando else "")
            )

    if restam <= ALERTA_DIAS:
        log.error("RENOVE O TOKEN: faltam %d dias", restam)
        return 3
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        sys.exit(check(config.Credentials()))
    except PublishError as exc:
        log.error("falha ao consultar o token: %s", exc)
        sys.exit(1)
