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
from publishers.meta_auth import page_token

log = logging.getLogger(__name__)

POLL_INTERVAL = 5
POLL_MAX = 24  # até 2 minutos esperando o Instagram processar
PUBLISH_RETRIES = 4  # media_publish pode dizer "Media ID is not available" logo após FINISHED
PUBLISH_RETRY_WAIT = 10


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


def _media_publish(ig_id: str, creation_id: str, token: str) -> str:
    """media_publish; repete só o erro 2207027 (container ainda não disponível).

    Nesse erro nada foi publicado, então repetir não duplica o post.
    """
    for tentativa in range(1, PUBLISH_RETRIES + 1):
        try:
            resp = request(
                "POST",
                f"{config.GRAPH}/{ig_id}/media_publish",
                data={"creation_id": creation_id, "access_token": token},
                idempotent=False,
            )
            return resp.json().get("id", "")
        except PublishError as exc:
            if "2207027" not in str(exc) or tentativa == PUBLISH_RETRIES:
                raise
            log.warning("Instagram: mídia ainda indisponível, nova tentativa %d", tentativa + 1)
            time.sleep(PUBLISH_RETRY_WAIT)
    return ""


def publish(creds, caption: str, image_urls: list[str]) -> str:
    if not image_urls:
        raise PublishError("Instagram: nenhuma imagem para publicar")

    ig_id = creds.ig_user_id
    # O Instagram comercial publica com o token da Página do Facebook vinculada.
    token = page_token(creds.meta_token, creds.fb_page_id) if creds.fb_page_id else creds.meta_token
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

    media_id = _media_publish(ig_id, creation_id, token)
    log.info("Instagram: publicado %s", media_id)
    return media_id


def permalink(creds, media_id: str) -> str:
    """Link público do post (melhor esforço: devolve "" se a API não responder)."""
    token = page_token(creds.meta_token, creds.fb_page_id) if creds.fb_page_id else creds.meta_token
    resp = request(
        "GET",
        f"{config.GRAPH}/{media_id}",
        params={"fields": "permalink", "access_token": token},
        attempts=2,
    )
    return resp.json().get("permalink", "")


def _token(creds) -> str:
    return page_token(creds.meta_token, creds.fb_page_id) if creds.fb_page_id else creds.meta_token


def publish_story(creds, image_url: str) -> str:
    """Publica uma imagem nos Stories (instagram_content_publish).

    Story não tem legenda pela API e some do perfil em 24 horas.
    """
    ig_id, token = creds.ig_user_id, _token(creds)
    creation_id = _container(ig_id, token, image_url=image_url, media_type="STORIES")
    _wait_ready(creation_id, token)
    media_id = _media_publish(ig_id, creation_id, token)
    log.info("Instagram Stories: publicado %s", media_id)
    return media_id


def comment(creds, media_id: str, message: str) -> str:
    """Primeiro comentário no post (exige instagram_manage_comments)."""
    resp = request(
        "POST",
        f"{config.GRAPH}/{media_id}/comments",
        data={"message": message, "access_token": _token(creds)},
        idempotent=False,
    )
    return resp.json().get("id", "")
