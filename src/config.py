"""Configuração central: identidade visual, credenciais e grade de publicação."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

# ---------------------------------------------------------------- marca

BG = "#0D1117"          # fundo NOC
AMBER = "#FFB000"       # destaque primário
GREEN = "#39FF14"       # destaque secundário / terminal
FG = "#E6EDF3"          # texto corrido
MUTED = "#7D8590"       # texto secundário
GRID = "#161B22"        # linhas e caixas

BRAND = "TECHDIM"
TAGLINE = "Infraestrutura · Segurança · IA"
SITE = "www.techdim.com.br"
SITE_URL = "https://www.techdim.com.br"
IG_HANDLE = "@techdimbr"

# Praça de atendimento. Entra nas hashtags e no texto porque é por geografia que
# uma conta nova é descoberta por quem pode virar cliente: "#campinas" tem
# público; "#TECHDIM" só tem quem já conhece a marca.
CIDADE = "Campinas"
REGIAO = "Campinas e região"

# Identidade visual por tema: cor de acento, cor secundária e motivo de fundo.
THEME_STYLE = {
    "noticias": {
        "accent": "#4DA3FF",   # azul sinal / transmissão
        "second": "#FFB000",
        "motif": "ondas",
        "glyph": "//",
    },
    "hacker": {
        "accent": "#FF3B30",   # vermelho alerta
        "second": "#39FF14",
        "motif": "scanlines",
        "glyph": "!!",
    },
    "dica": {
        "accent": "#39FF14",   # verde terminal
        "second": "#FFB000",
        "motif": "grade",
        "glyph": ">>",
    },
    "servico": {
        "accent": "#FFB000",   # âmbar da marca
        "second": "#4DA3FF",
        "motif": "circuito",
        "glyph": "##",
    },
    "especial": {
        "accent": "#FFB000",   # âmbar da marca: anúncio institucional sob demanda
        "second": "#4DA3FF",
        "motif": "ondas",
        "glyph": "++",
    },
    "destaque": {
        "accent": "#FF8A00",   # laranja de alerta: notícia curada do dia
        "second": "#FF3B30",
        "motif": "radar",
        "glyph": "**",
    },
}


def style(theme: str) -> dict:
    return THEME_STYLE.get(theme, THEME_STYLE["servico"])


# ---------------------------------------------------------------- formatos

# (largura, altura) por destino
SIZE_INSTAGRAM = (1080, 1350)  # 4:5 — ocupa a altura máxima do feed do IG
SIZE_FACEBOOK = (1200, 1500)   # 4:5 na resolução que o FB serve sem recomprimir
SIZE_LINKEDIN = (1200, 1200)   # 1:1 — melhor aproveitamento no feed do LinkedIn

SIZE_STORY = (1080, 1920)      # 9:16 — Stories do Instagram

SIZE_BY_NETWORK = {
    "instagram_stories": SIZE_STORY,
    "instagram": SIZE_INSTAGRAM,
    "facebook": SIZE_FACEBOOK,
    "linkedin": SIZE_LINKEDIN,
}

CAROUSEL_SLIDES = 4

# ---------------------------------------------------------------- credenciais


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


# WhatsApp comercial, só dígitos com DDI e DDD (ex.: 5519999998888). Vem do
# ambiente para não ficar no código; sem ele, o CTA cai no site.
WHATSAPP = _env("WHATSAPP_NUMERO").replace("+", "").replace(" ", "").replace("-", "")


@dataclass
class Credentials:
    """Credenciais lidas do ambiente (GitHub Secrets em produção)."""

    meta_token: str = field(default_factory=lambda: _env("META_ACCESS_TOKEN"))
    fb_page_id: str = field(default_factory=lambda: _env("FB_PAGE_ID"))
    ig_user_id: str = field(default_factory=lambda: _env("IG_USER_ID"))

    linkedin_token: str = field(default_factory=lambda: _env("LINKEDIN_ACCESS_TOKEN"))
    linkedin_urn: str = field(default_factory=lambda: _env("LINKEDIN_URN"))

    # host público das imagens (preenchido pelo uploader)
    asset_base_url: str = field(default_factory=lambda: _env("ASSET_BASE_URL"))

    @property
    def has_meta(self) -> bool:
        return bool(self.meta_token and (self.fb_page_id or self.ig_user_id))

    @property
    def has_facebook(self) -> bool:
        return bool(self.meta_token and self.fb_page_id)

    @property
    def has_instagram(self) -> bool:
        return bool(self.meta_token and self.ig_user_id)

    @property
    def has_linkedin(self) -> bool:
        # O URN é opcional: sem ele, o publicador o descobre pelo token.
        return bool(self.linkedin_token)


# v21.0 funciona até 21/01/2027 — atualizar antes dessa data.
GRAPH_VERSION = "v21.0"
GRAPH = f"https://graph.facebook.com/{GRAPH_VERSION}"
LINKEDIN_API = "https://api.linkedin.com"
# LinkedIn mantém cada versão por ~1 ano; versão vencida devolve HTTP 426.
# 202609 vale até ~09/2027 — atualizar uma vez por ano.
LINKEDIN_VERSION = "202609"

TZ = "America/Sao_Paulo"


def _fuso():
    try:
        from zoneinfo import ZoneInfo

        return ZoneInfo(TZ)
    except Exception:  # sem base de fusos: Brasília é UTC-3 fixo desde 2019
        return timezone(timedelta(hours=-3))


def agora() -> datetime:
    """Hora atual em Brasília (o runner do GitHub roda em UTC)."""
    return datetime.now(_fuso())


def hoje() -> date:
    """Data de hoje em Brasília: é ela que nomeia pauta, imagens e registros."""
    return agora().date()

# ---------------------------------------------------------------- grade

# Janela em que vale a pena publicar (hora de Brasília; início inclusivo, fim
# exclusivo): o horário em que donos e gestores de PME estão na rede. Em
# 02/10/2026 quatro posts saíram entre 00h22 e 01h11, sem ninguém para
# interagir. É uma premissa, não uma medição: o relatório semanal compara os
# horários e é ele que deve ajustar esta janela.
JANELA_PUBLICACAO = (7, 22)


def dentro_da_janela(quando: datetime | None = None) -> bool:
    inicio, fim = JANELA_PUBLICACAO
    return inicio <= (quando or agora()).hour < fim


# Quais redes recebem post de feed em cada tema.
# Editar aqui é o jeito de reduzir volume sem mexer em código.
THEME_TARGETS = {
    "noticias": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "hacker": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "dica": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "servico": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "destaque": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "especial": ["linkedin", "facebook", "instagram", "instagram_stories"],
}

THEME_LABELS = {
    "noticias": "Notícias de Tecnologia",
    "hacker": "Cibersegurança · IA · Hacker",
    "dica": "Conhecimento",
    "servico": "TECHDIM · Serviços",
    "destaque": "Destaque do Dia",
    "especial": "TECHDIM + IA",
}
