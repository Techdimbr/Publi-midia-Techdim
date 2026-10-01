"""Utilitários compartilhados pelos publicadores."""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

TIMEOUT = 60
RETRY_STATUS = {429, 500, 502, 503, 504}


class PublishError(RuntimeError):
    """Falha definitiva ao publicar numa rede."""


def request(
    method: str,
    url: str,
    *,
    attempts: int = 4,
    **kwargs,
) -> requests.Response:
    """Chamada HTTP com retry exponencial em erro transitório."""
    kwargs.setdefault("timeout", TIMEOUT)
    last: Exception | None = None

    for attempt in range(attempts):
        try:
            resp = requests.request(method, url, **kwargs)
        except requests.RequestException as exc:
            last = exc
            log.warning("rede falhou (%s/%s): %s", attempt + 1, attempts, exc)
        else:
            if resp.status_code < 400:
                return resp
            if resp.status_code in RETRY_STATUS and attempt < attempts - 1:
                log.warning(
                    "HTTP %s em %s (%s/%s)", resp.status_code, url, attempt + 1, attempts
                )
                last = PublishError(f"HTTP {resp.status_code}: {resp.text[:400]}")
            else:
                raise PublishError(
                    f"{method} {url} -> HTTP {resp.status_code}: {resp.text[:600]}"
                )
        time.sleep(2 ** attempt)

    raise PublishError(f"{method} {url} falhou após {attempts} tentativas: {last}")


def redact(text: str, *secrets: str) -> str:
    """Remove credenciais de mensagens antes de logar."""
    for secret in secrets:
        if secret and len(secret) > 8:
            text = text.replace(secret, f"{secret[:6]}…[REDIGIDO]")
    return text
