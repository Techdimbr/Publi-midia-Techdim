"""Limpeza e corte de texto vindo de fontes externas (pauta, RSS)."""
from __future__ import annotations


def uma_linha(texto: object) -> str:
    """Texto em uma linha só, sem espaços repetidos. Valor que não é texto vira ""."""
    return " ".join(texto.split()) if isinstance(texto, str) else ""


def cortar(texto: object, limite: int) -> str:
    """Corta em palavra inteira, com reticências, quando passa do limite."""
    t = uma_linha(texto)
    if len(t) <= limite:
        return t
    return t[: limite - 1].rsplit(" ", 1)[0].rstrip(" ,;:.") + "…"
