"""Remoção de credenciais de qualquer texto que vá para o branch assets.

O branch assets é público: registros, diário e relatórios passam por aqui antes
de serem gravados. Um padrão novo (outro provedor, outro formato) entra só
nesta lista e vale para todos os módulos.
"""
from __future__ import annotations

import re

_PADROES = (
    r"\bEAA[A-Za-z0-9]{20,}",         # token da Meta (usuário ou página)
    r"\bAQ[A-Za-z0-9_-]{40,}",        # token de acesso do LinkedIn
    r"\bWPL_AP\d\.[\w./=+-]+",       # client secret do LinkedIn
    r"\bsk-ant-[A-Za-z0-9_-]{20,}",   # chave da API da Anthropic
    r"\bgh[pousr]_[A-Za-z0-9]{30,}",  # tokens do GitHub
    r"\bgithub_pat_[A-Za-z0-9_]{30,}",
)
CREDENCIAL = re.compile("|".join(_PADROES))


def redigir(texto: str | None) -> str:
    """Troca qualquer coisa que pareça credencial por [REDIGIDO]."""
    return CREDENCIAL.sub("[REDIGIDO]", texto or "")
