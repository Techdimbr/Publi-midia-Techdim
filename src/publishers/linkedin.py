"""Publicação no LinkedIn via Versioned API (Images + Posts).

Três etapas: initializeUpload devolve uma uploadUrl e o URN da imagem; o
binário sobe por PUT nessa URL; o post referencia o URN. Vale tanto para
perfil pessoal (urn:li:person:...) quanto para Página (urn:li:organization:...)
— só muda o author, e a permissão exigida (w_member_social vs
w_organization_social).
Docs: https://learn.microsoft.com/linkedin/marketing/community-management/shares/images-api
"""
from __future__ import annotations

import logging
import pathlib

import config
from publishers.common import PublishError, request

log = logging.getLogger(__name__)

# Caracteres que o LinkedIn exige escapar no texto do post (Little Text Format).
ESCAPE = "|{}@[]()<>#*_~"


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": config.LINKEDIN_VERSION,
        "X-Restli-Protocol-Version": "2.0.0",
    }


def escape_commentary(text: str) -> str:
    """Escapa os caracteres reservados do formato de texto do LinkedIn."""
    out = []
    for ch in text:
        if ch in ESCAPE:
            out.append("\\")
        out.append(ch)
    return "".join(out)


def _upload_image(creds, image_path: pathlib.Path) -> str:
    resp = request(
        "POST",
        f"{config.LINKEDIN_API}/rest/images?action=initializeUpload",
        headers={**_headers(creds.linkedin_token), "Content-Type": "application/json"},
        json={"initializeUploadRequest": {"owner": creds.linkedin_urn}},
    )
    value = resp.json().get("value", {})
    upload_url, image_urn = value.get("uploadUrl"), value.get("image")
    if not upload_url or not image_urn:
        raise PublishError(f"LinkedIn não devolveu uploadUrl: {resp.text[:300]}")

    request(
        "PUT",
        upload_url,
        headers={"Authorization": f"Bearer {creds.linkedin_token}"},
        data=image_path.read_bytes(),
    )
    log.info("LinkedIn: imagem enviada %s", image_urn)
    return image_urn


def publish(creds, caption: str, image_paths: list[pathlib.Path], alt: str = "") -> str:
    """Publica um post de imagem única. Devolve o URN do post."""
    if not image_paths:
        raise PublishError("LinkedIn: nenhuma imagem para publicar")

    image_urn = _upload_image(creds, image_paths[0])

    body = {
        "author": creds.linkedin_urn,
        "commentary": escape_commentary(caption),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {
            "media": {
                "id": image_urn,
                "altText": (alt or "Publicação TECHDIM")[:200],
            }
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    resp = request(
        "POST",
        f"{config.LINKEDIN_API}/rest/posts",
        headers={**_headers(creds.linkedin_token), "Content-Type": "application/json"},
        json=body,
    )
    post_urn = resp.headers.get("x-restli-id") or resp.headers.get("X-RestLi-Id", "")
    log.info("LinkedIn: publicado %s", post_urn)
    return post_urn


def permalink(post_urn: str) -> str:
    return f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else ""
