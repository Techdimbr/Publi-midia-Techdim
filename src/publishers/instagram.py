"""Publicação no Instagram (conta comercial) via Content Publishing API.

Carrossel em 3 etapas: um container por imagem (is_carousel_item=true), um
container CAROUSEL agrupando os filhos, e o media_publish. O Instagram busca
cada image_url no servidor dele — a URL precisa ser pública.
Docs: https://developers.facebook.com/docs/instagram-platform/content-publishing
"""
from __future__ import annotations

import logging
import time

import config
from publishers.common import PublishError, request

log = logging.getLogger(__name__)

POLL_INTERVAL = 5
POLL_MAX = 24  # até 2 minutos esperando o Instagram processar


def _container(ig_id: str, token: str, **fields) -> str:
    resp = request(
        "POST", f"{config.GRAPH}/{ig_id}/media", data={**fields, "access_token": token}
    )
    cid = resp.json().get("id")
    if not cid:
        raise PublishError(f"Instagram não devolveu container: {resp.text[:300]}")
    return cid


def _wait_ready(container_id: str, token: str) -> None:
    """Espera o container sair de IN_PROGRESS. ERROR/EXPIRED aborta."""
    for _ in range(POLL_MAX):
        resp = request(
            "GET",
            f"{config.GRAPH}/{container_id}",
            params={"fields": "status_code,status", "access_token": token},
        )
        data = resp.json()
        status = data.get("status_code")
        if status == "FINISHED":
            return
        if status in {"ERROR", "EXPIRED"}:
            raise PublishError(
                f"Instagram rejeitou o container {container_id}: {data.get('status')}"
            )
        time.sleep(POLL_INTERVAL)
    raise PublishError(f"Instagram: container {container_id} não ficou pronto a tempo")


def publish(creds, caption: str, image_urls: list[str]) -> str:
    if not image_urls:
        raise PublishError("Instagram: nenhuma imagem para publicar")

    ig_id, token = creds.ig_user_id, creds.meta_token
    urls = image_urls[:10]  # limite do carrossel

    if len(urls) == 1:
        creation_id = _container(ig_id, token, image_url=urls[0], caption=caption)
    else:
        children = []
        for url in urls:
            child = _container(ig_id, token, image_url=url, is_carousel_item="true")
            _wait_ready(child, token)
            children.append(child)
        log.info("Instagram: %d item(ns) de carrossel prontos", len(children))
        creation_id = _container(
            ig_id,
            token,
            media_type="CAROUSEL",
            children=",".join(children),
            caption=caption,
        )

    _wait_ready(creation_id, token)

    resp = request(
        "POST",
        f"{config.GRAPH}/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
    )
    media_id = resp.json().get("id", "")
    log.info("Instagram: publicado %s", media_id)
    return media_id
