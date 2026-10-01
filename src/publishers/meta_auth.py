"""Derivação do Page Access Token a partir do token de usuário.

A Graph API exige o token DA PÁGINA para publicar nela — o token de usuário,
mesmo com pages_manage_posts, é recusado. Derivar a cada execução significa
que você guarda uma credencial só (o token de usuário) e nunca precisa
atualizar o da página.

Se o que estiver configurado já for um token de página, a derivação é pulada.
"""
from __future__ import annotations

import functools
import logging

import config
from publishers.common import PublishError, request

log = logging.getLogger(__name__)


@functools.lru_cache(maxsize=4)
def _debug(token: str) -> dict:
    resp = request(
        "GET",
        f"{config.GRAPH}/debug_token",
        params={"input_token": token, "access_token": token},
    )
    return resp.json().get("data", {})


@functools.lru_cache(maxsize=4)
def page_token(user_token: str, page_id: str) -> str:
    """Devolve o token da página. Aceita token de usuário ou já de página."""
    if not user_token or not page_id:
        raise PublishError("token ou page_id ausente")

    tipo = _debug(user_token).get("type")
    if tipo == "PAGE":
        log.info("token já é de página, usando direto")
        return user_token

    resp = request(
        "GET",
        f"{config.GRAPH}/me/accounts",
        params={"fields": "id,name,access_token", "access_token": user_token},
    )
    paginas = resp.json().get("data", [])
    for p in paginas:
        if p.get("id") == page_id:
            log.info("page token derivado para %r", p.get("name"))
            return p["access_token"]

    conhecidas = ", ".join(f"{p.get('name')} ({p.get('id')})" for p in paginas) or "nenhuma"
    raise PublishError(
        f"página {page_id} não está entre as que este token administra: {conhecidas}"
    )
