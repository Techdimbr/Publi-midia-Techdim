"""Utilitários compartilhados pelos publicadores."""
from __future__ import annotations

import logging
import time

import requests

log = logging.getLogger(__name__)

TIMEOUT = (15, 60)  # (conexão, leitura) em segundos
RETRY_STATUS = {429, 500, 502, 503, 504}
# Chamada que CRIA algo (post, comentário): só se repete quando o servidor
# garantidamente não processou o pedido — limite de uso (429) ou serviço
# indisponível (503). Um 500/502/504 ou um timeout de leitura podem ter criado
# o post mesmo assim, e repetir publicaria em duplicidade.
RETRY_STATUS_SEM_DUPLICAR = {429, 503}
ESPERA_MAXIMA = 60


class PublishError(RuntimeError):
    """Falha definitiva ao publicar numa rede."""


def _espera(resp: requests.Response | None, tentativa: int) -> float:
    """Pausa até a próxima tentativa; respeita Retry-After quando o servidor manda."""
    if resp is not None:
        try:
            return min(float(resp.headers.get("Retry-After", "")), ESPERA_MAXIMA)
        except ValueError:
            pass
    return 2**tentativa


def request(
    method: str,
    url: str,
    *,
    attempts: int = 4,
    idempotent: bool = True,
    **kwargs,
) -> requests.Response:
    """Chamada HTTP com retry exponencial em erro transitório.

    idempotent=False marca chamadas que criam algo (publicar, comentar): nelas
    o retry se limita aos casos em que repetir não pode duplicar.
    """
    kwargs.setdefault("timeout", TIMEOUT)
    repetir_status = RETRY_STATUS if idempotent else RETRY_STATUS_SEM_DUPLICAR
    last: Exception | None = None

    for attempt in range(attempts):
        resp = None
        try:
            resp = requests.request(method, url, **kwargs)
        except requests.ConnectTimeout as exc:
            # nada chegou ao servidor: repetir é sempre seguro
            last = exc
            log.warning("conexão falhou (%s/%s): %s", attempt + 1, attempts, exc)
        except requests.RequestException as exc:
            if not idempotent:
                raise PublishError(
                    f"{method} {url} sem resposta ({type(exc).__name__}); não repeti "
                    f"para não duplicar. Confira na rede se o item foi criado: {exc}"
                ) from exc
            last = exc
            log.warning("rede falhou (%s/%s): %s", attempt + 1, attempts, exc)
        else:
            if resp.status_code < 400:
                return resp
            if resp.status_code in repetir_status and attempt < attempts - 1:
                log.warning(
                    "HTTP %s em %s (%s/%s)", resp.status_code, url, attempt + 1, attempts
                )
                last = PublishError(f"HTTP {resp.status_code}: {resp.text[:400]}")
            else:
                raise PublishError(
                    f"{method} {url} -> HTTP {resp.status_code}: {resp.text[:600]}"
                )
        if attempt < attempts - 1:
            time.sleep(_espera(resp, attempt))

    raise PublishError(f"{method} {url} falhou após {attempts} tentativas: {last}")


def redact(text: str, *secrets: str) -> str:
    """Remove credenciais de mensagens antes de logar."""
    for secret in secrets:
        if secret and len(secret) > 8:
            text = text.replace(secret, f"{secret[:6]}…[REDIGIDO]")
    return text
