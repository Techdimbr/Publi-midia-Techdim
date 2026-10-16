"""Publicação no Facebook (Página) via Graph API.

Fluxo de álbum: cada imagem sobe como foto não publicada (published=false),
devolvendo um media_fbid; o post do feed referencia todos eles em
attached_media, que é o que o Facebook renderiza como álbum/carrossel.
Vídeo vai como Reel (9:16, 3 a 90 s): abre a sessão (start), envia o arquivo ao
rupload.facebook.com e publica (finish).
Docs: https://developers.facebook.com/docs/pages-api/posts
      https://developers.facebook.com/docs/video-api/guides/reels-publishing
"""
from __future__ import annotations

import logging
import pathlib
import time

import config
from publishers.common import PublishError, request
from publishers.meta_auth import page_token

log = logging.getLogger(__name__)

REEL_ESPERA = 5        # segundos entre consultas ao status do Reel
REEL_TENTATIVAS = 60   # até 5 minutos
TIMEOUT_ENVIO = (15, 600)  # (conexão, leitura) do envio do arquivo


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

    resp = request("POST", f"{config.GRAPH}/{page_id}/feed", data=payload, idempotent=False)
    post_id = resp.json().get("id", "")
    log.info("Facebook: publicado %s", post_id)
    return post_id


def _status_reel(video_id: str, token: str) -> dict:
    resp = request(
        "GET",
        f"{config.GRAPH}/{video_id}",
        params={"fields": "status", "access_token": token},
        attempts=2,
    )
    return resp.json().get("status") or {}


def publish_reel(creds, caption: str, video_path: pathlib.Path, title: str = "") -> str:
    """Publica o vídeo como Reel da Página e devolve o id do vídeo."""
    page_id = creds.fb_page_id
    token = page_token(creds.meta_token, page_id)

    # 1) abre a sessão de envio (nada vai ao ar ainda)
    inicio = request(
        "POST",
        f"{config.GRAPH}/{page_id}/video_reels",
        data={"upload_phase": "start", "access_token": token},
    ).json()
    video_id = inicio.get("video_id")
    if not video_id:
        raise PublishError(f"Facebook não devolveu video_id para o Reel: {str(inicio)[:300]}")
    destino = inicio.get("upload_url") or f"{config.RUPLOAD}/video-upload/{config.GRAPH_VERSION}/{video_id}"

    # 2) envia o arquivo (repetir é seguro: recomeça do byte 0)
    dados = video_path.read_bytes()
    envio = request(
        "POST",
        destino,
        headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(dados))},
        data=dados,
        timeout=TIMEOUT_ENVIO,
    ).json()
    if not envio.get("success"):
        raise PublishError(f"Facebook recusou o envio do vídeo: {str(envio)[:300]}")
    log.info("Facebook: vídeo %s enviado (%d bytes)", video_id, len(dados))

    # 3) espera o envio ser dado como completo antes de publicar
    for _ in range(REEL_TENTATIVAS):
        estado = _status_reel(video_id, token).get("video_status")
        if estado in {"upload_complete", "processing", "ready"}:
            break
        if estado in {"error", "expired", "upload_failed"}:
            raise PublishError(f"Facebook: envio do Reel falhou ({estado})")
        time.sleep(REEL_ESPERA)
    else:
        raise PublishError("Facebook: o envio do Reel não terminou a tempo")

    # 4) publica
    campos = {
        "video_id": video_id,
        "upload_phase": "finish",
        "video_state": "PUBLISHED",
        "description": caption,
        "access_token": token,
    }
    if title:
        campos["title"] = title[:100]
    fim = request("POST", f"{config.GRAPH}/{page_id}/video_reels", data=campos, idempotent=False).json()
    if not fim.get("success"):
        raise PublishError(f"Facebook não confirmou a publicação do Reel: {str(fim)[:300]}")

    # 5) o processamento é assíncrono: acompanha até aparecer como publicado (ou falhar)
    for _ in range(REEL_TENTATIVAS):
        status = _status_reel(video_id, token)
        publicacao = (status.get("publishing_phase") or {}).get("publish_status")
        if publicacao == "published" or status.get("video_status") == "ready":
            break
        if status.get("video_status") == "error" or publicacao == "error":
            detalhe = (status.get("processing_phase") or {}).get("error") or (
                status.get("publishing_phase") or {}).get("error") or "sem detalhe"
            raise PublishError(f"Facebook rejeitou o Reel: {str(detalhe)[:300]}")
        time.sleep(REEL_ESPERA)
    else:
        log.warning("Facebook: o Reel %s ainda processa; o post sai quando terminar", video_id)
    log.info("Facebook: Reel publicado %s", video_id)
    return video_id


def permalink(creds, post_id: str) -> str:
    """Link público do post (melhor esforço: devolve "" se a API não responder)."""
    token = page_token(creds.meta_token, creds.fb_page_id)
    resp = request(
        "GET",
        f"{config.GRAPH}/{post_id}",
        params={"fields": "permalink_url", "access_token": token},
        attempts=2,
    )
    link = resp.json().get("permalink_url", "")
    # vídeos devolvem o caminho relativo (/reel/123); post de feed já vem completo
    return f"https://www.facebook.com{link}" if link.startswith("/") else link


def comment(creds, post_id: str, message: str) -> str:
    """Primeiro comentário no post (exige pages_manage_engagement)."""
    token = page_token(creds.meta_token, creds.fb_page_id)
    resp = request(
        "POST",
        f"{config.GRAPH}/{post_id}/comments",
        data={"message": message, "access_token": token},
        idempotent=False,
    )
    return resp.json().get("id", "")
