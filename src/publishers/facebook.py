"""Publicação no Facebook (Página) via Graph API.

Fluxo de álbum: cada imagem sobe como foto não publicada (published=false),
devolvendo um media_fbid; o post do feed referencia todos eles em
attached_media, que é o que o Facebook renderiza como álbum/carrossel.
Docs: https://developers.facebook.com/docs/pages-api/posts
"""
from __future__ import annotations

import logging

import config
from publishers.common import PublishError, request
from publishers.meta_auth import page_token

log = logging.getLogger(__name__)


def _upload_photo(page_id: str, token: str, image_url: str) -> str:
    resp = request(
        "POST",
        f"{config.GRAPH}/{page_id}/photos",
        data={"url": image_url, "published": "false", "access_token": token},
    )
    fbid = resp.json().get("id")
    if not fbid:
        raise PublishError(f"Facebook não devolveu media_fbid: {resp.text[:300]}")
    return fbid


def publish(creds, caption: str, image_urls: list[str]) -> str:
    """Publica o álbum e devolve o id do post."""
    if not image_urls:
        raise PublishError("Facebook: nenhuma imagem para publicar")

    page_id = creds.fb_page_id
    token = page_token(creds.meta_token, page_id)

    fbids = [_upload_photo(page_id, token, url) for url in image_urls]
    log.info("Facebook: %d foto(s) enviada(s)", len(fbids))

    payload = {"message": caption, "access_token": token}
    for i, fbid in enumerate(fbids):
        payload[f"attached_media[{i}]"] = f'{{"media_fbid":"{fbid}"}}'

    resp = request("POST", f"{config.GRAPH}/{page_id}/feed", data=payload)
    post_id = resp.json().get("id", "")
    log.info("Facebook: publicado %s", post_id)
    return post_id


def permalink(creds, post_id: str) -> str:
    """Link público do post (melhor esforço: devolve "" se a API não responder)."""
    token = page_token(creds.meta_token, creds.fb_page_id)
    resp = request(
        "GET",
        f"{config.GRAPH}/{post_id}",
        params={"fields": "permalink_url", "access_token": token},
        attempts=2,
    )
    return resp.json().get("permalink_url", "")
