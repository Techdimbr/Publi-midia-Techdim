"""Links rastreáveis: tudo que sai num post carrega de onde veio.

Sem UTM não há como saber se o site recebeu visita vinda de um post, e sem isso
o relatório mede curtida em vez de cliente. O WhatsApp é o CTA de conversão: um
toque abre a conversa com a mensagem já escrita, e o assunto dentro da mensagem
diz qual post trouxe a pessoa — é a atribuição que a Meta não entrega.
"""
from __future__ import annotations

import datetime as dt
from urllib.parse import urlencode

import config
from texto import cortar

# Redes em que o link é clicável. No Instagram ele não é (nem na legenda, nem no
# comentário), então lá vai o endereço limpo, que a pessoa digita ou acha na bio.
CLICAVEL = ("facebook", "linkedin")


def site(tema: str = "", rede: str = "", data: dt.date | None = None) -> str:
    """Endereço do site com UTM. Sem tema e sem rede, devolve o site puro."""
    if not (tema or rede):
        return config.SITE_URL
    params = {
        "utm_source": rede or "social",
        "utm_medium": "social",
        "utm_campaign": "diario",
        "utm_content": f"{tema or 'post'}-{(data or config.hoje()).isoformat()}",
    }
    return f"{config.SITE_URL}/?{urlencode(params)}"


def site_para(rede: str, tema: str = "", data: dt.date | None = None) -> str:
    """Site na forma certa para a rede: com UTM onde o link é clicável."""
    return site(tema, rede, data) if rede in CLICAVEL else config.SITE


def whatsapp(assunto: str = "", tema: str = "") -> str:
    """Conversa de WhatsApp já aberta no assunto do post. Vazio se não houver número."""
    if not config.WHATSAPP:
        return ""
    sobre = cortar(assunto, 90)
    texto = (
        f'Olá! Vi o post da TECHDIM sobre "{sobre}" e quero falar com vocês.'
        if sobre
        else "Olá! Vim pelas redes da TECHDIM e quero falar com vocês."
    )
    return f"https://wa.me/{config.WHATSAPP}?{urlencode({'text': texto})}"


def contato(rede: str, assunto: str = "", tema: str = "", data: dt.date | None = None) -> str:
    """Melhor destino de contato para a rede: WhatsApp quando houver, senão o site."""
    return whatsapp(assunto, tema) or site_para(rede, tema, data)
