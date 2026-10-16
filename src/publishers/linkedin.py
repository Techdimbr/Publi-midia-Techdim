"""Publicação no LinkedIn via Versioned API (Images + Videos + Posts).

Três etapas: initializeUpload devolve uma uploadUrl e o URN da imagem; o
binário sobe por PUT nessa URL; o post referencia o URN. Vale tanto para
perfil pessoal (urn:li:person:...) quanto para Página (urn:li:organization:...)
— só muda o author, e a permissão exigida (w_member_social vs
w_organization_social).
Vídeo segue o mesmo caminho, em partes de 4 MB e com um finalizeUpload no fim.
Docs: https://learn.microsoft.com/linkedin/marketing/community-management/shares/images-api
      https://learn.microsoft.com/linkedin/marketing/community-management/shares/videos-api
"""
from __future__ import annotations

import logging
import pathlib
import time
from urllib.parse import quote

import config
from publishers.common import PublishError, request

log = logging.getLogger(__name__)

# Caracteres que o LinkedIn exige escapar no texto do post (Little Text Format).
ESCAPE = "|{}@[]()<>#*_~"

VIDEO_ESPERA = 5        # segundos entre consultas ao processamento do vídeo
VIDEO_TENTATIVAS = 72   # até 6 minutos
TIMEOUT_ENVIO = (15, 300)  # (conexão, leitura) de cada parte do vídeo


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


def resolve_urn(creds) -> str:
    """URN do autor. Sem LINKEDIN_URN, descobre o do dono do token (perfil pessoal).

    O LinkedIn não entrega o URN junto com o token; ele sai do endpoint userinfo
    (escopos openid + profile): urn:li:person:<sub>. Para publicar como página,
    informe LINKEDIN_URN=urn:li:organization:<id>.
    """
    if creds.linkedin_urn:
        return creds.linkedin_urn
    resp = request(
        "GET",
        f"{config.LINKEDIN_API}/v2/userinfo",
        headers={"Authorization": f"Bearer {creds.linkedin_token}"},
        attempts=2,
    )
    sub = resp.json().get("sub")
    if not sub:
        raise PublishError(
            "LinkedIn: não consegui descobrir o URN — o token precisa dos escopos openid e profile"
        )
    creds.linkedin_urn = f"urn:li:person:{sub}"
    log.info("LinkedIn: URN descoberto pelo token (%s)", creds.linkedin_urn)
    return creds.linkedin_urn


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

    resolve_urn(creds)
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
        idempotent=False,
    )
    post_urn = resp.headers.get("x-restli-id") or resp.headers.get("X-RestLi-Id", "")
    log.info("LinkedIn: publicado %s", post_urn)
    return post_urn


def _sem_assinatura(url: str, exc: PublishError) -> PublishError:
    """A uploadUrl leva uma assinatura na query: ela não pode ir para o log público do Actions."""
    return PublishError(str(exc).replace(url, url.split("?")[0] + "?…"))


def _upload_video(creds, video_path: pathlib.Path) -> str:
    """initializeUpload, envio das partes e finalizeUpload. Devolve o URN do vídeo."""
    cab = {**_headers(creds.linkedin_token), "Content-Type": "application/json"}
    tamanho = video_path.stat().st_size
    resp = request(
        "POST",
        f"{config.LINKEDIN_API}/rest/videos?action=initializeUpload",
        headers=cab,
        json={"initializeUploadRequest": {
            "owner": creds.linkedin_urn,
            "fileSizeBytes": tamanho,
            "uploadCaptions": False,
            "uploadThumbnail": False,
        }},
    )
    value = resp.json().get("value", {})
    video_urn, partes = value.get("video"), value.get("uploadInstructions") or []
    if not video_urn or not partes:
        raise PublishError(f"LinkedIn não devolveu o plano de envio do vídeo: {resp.text[:300]}")

    etags: list[str] = []
    with video_path.open("rb") as fh:
        for i, parte in enumerate(partes, 1):
            fh.seek(parte["firstByte"])
            dados = fh.read(parte["lastByte"] - parte["firstByte"] + 1)  # a última parte pode ser menor
            try:
                r = request(
                    "PUT",
                    parte["uploadUrl"],
                    headers={"Authorization": f"Bearer {creds.linkedin_token}",
                             "Content-Type": "application/octet-stream"},
                    data=dados,
                    timeout=TIMEOUT_ENVIO,
                )
            except PublishError as exc:
                raise _sem_assinatura(parte["uploadUrl"], exc) from None
            etag = (r.headers.get("ETag") or "").strip().strip('"')
            if not etag:
                raise PublishError(f"LinkedIn: a parte {i} do vídeo subiu sem ETag")
            etags.append(etag)
    log.info("LinkedIn: vídeo enviado em %d parte(s) (%s)", len(etags), video_urn)

    request(
        "POST",
        f"{config.LINKEDIN_API}/rest/videos?action=finalizeUpload",
        headers=cab,
        json={"finalizeUploadRequest": {
            "video": video_urn,
            "uploadToken": value.get("uploadToken", ""),
            "uploadedPartIds": etags,
        }},
    )
    return video_urn


def _esperar_video(creds, video_urn: str) -> None:
    """Espera o vídeo sair de PROCESSING. Consulta que falha não derruba: o post espera o vídeo ficar pronto."""
    url = f"{config.LINKEDIN_API}/rest/videos/{quote(video_urn, safe='')}"
    for _ in range(VIDEO_TENTATIVAS):
        try:
            dados = request("GET", url, headers=_headers(creds.linkedin_token), attempts=2).json()
        except PublishError as exc:
            log.warning("LinkedIn: não consegui consultar o processamento do vídeo (%s); sigo para o post", exc)
            return
        status = dados.get("status")
        if status == "AVAILABLE":
            return
        if status == "PROCESSING_FAILED":
            raise PublishError(f"LinkedIn não processou o vídeo: {dados.get('processingFailureReason', 'sem motivo')}")
        time.sleep(VIDEO_ESPERA)
    raise PublishError("LinkedIn: o vídeo não ficou disponível a tempo")


def publish_video(creds, caption: str, video_path: pathlib.Path, title: str = "") -> str:
    """Publica um post de vídeo. Devolve o URN do post."""
    resolve_urn(creds)
    video_urn = _upload_video(creds, video_path)
    _esperar_video(creds, video_urn)

    body = {
        "author": creds.linkedin_urn,
        "commentary": escape_commentary(caption),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "content": {"media": {"id": video_urn, "title": (title or "Vídeo TECHDIM")[:200]}},
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }
    resp = request(
        "POST",
        f"{config.LINKEDIN_API}/rest/posts",
        headers={**_headers(creds.linkedin_token), "Content-Type": "application/json"},
        json=body,
        idempotent=False,
    )
    post_urn = resp.headers.get("x-restli-id") or resp.headers.get("X-RestLi-Id", "")
    log.info("LinkedIn: vídeo publicado %s", post_urn)
    return post_urn


def permalink(post_urn: str) -> str:
    return f"https://www.linkedin.com/feed/update/{post_urn}/" if post_urn else ""


def comment(creds, post_urn: str, message: str) -> str:
    """Primeiro comentário no post (Comments API, mesma permissão de publicar)."""
    resp = request(
        "POST",
        f"{config.LINKEDIN_API}/rest/socialActions/{quote(post_urn, safe='')}/comments",
        headers={**_headers(creds.linkedin_token), "Content-Type": "application/json"},
        json={
            "actor": creds.linkedin_urn,
            "object": post_urn,
            "message": {"text": message},
        },
        idempotent=False,
    )
    return resp.headers.get("x-restli-id") or resp.headers.get("X-RestLi-Id", "")
