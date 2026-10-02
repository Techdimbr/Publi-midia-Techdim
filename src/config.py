"""Configuração central: identidade visual, credenciais e grade de publicação."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

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

# ---------------------------------------------------------------- grade

# Quais redes recebem post de feed em cada tema.
# Editar aqui é o jeito de reduzir volume sem mexer em código.
THEME_TARGETS = {
    "noticias": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "hacker": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "dica": ["linkedin", "facebook", "instagram"],
    "servico": ["linkedin", "facebook", "instagram"],
    "destaque": ["linkedin", "facebook", "instagram", "instagram_stories"],
    "especial": ["linkedin", "facebook", "instagram"],
}

THEME_LABELS = {
    "noticias": "Notícias de Tecnologia",
    "hacker": "Cibersegurança · IA · Hacker",
    "dica": "Conhecimento",
    "servico": "TECHDIM · Serviços",
    "destaque": "Destaque do Dia",
    "especial": "TECHDIM + IA",
}
