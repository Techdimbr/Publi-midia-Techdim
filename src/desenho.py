"""Ferramentas de desenho compartilhadas pelo infográfico e pelas cenas:
fontes, cores, quebra de texto e primitivas de fundo."""
from __future__ import annotations

import functools
import math
import pathlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTES = ROOT / "fonts"

W, H = 1080, 1350
BG = (10, 13, 19)
FG = (236, 240, 245)
MUTED = (150, 160, 172)

SCENE = (560, 150, 1040, 640)  # x0, y0, x1, y1 da área ilustrada

# Fonte monoespaçada só para o código desenhado nas cenas; vem do sistema
# (o runner do GitHub tem DejaVu) e, se faltar, cai na fonte da marca.
_DIRS_MONO = (
    "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF",
    "/Library/Fonts", "C:/Windows/Fonts",
)
_ARQ_MONO = ("DejaVuSansMono.ttf", "Courier New.ttf", "cour.ttf")


@functools.lru_cache(maxsize=None)
def bebas(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTES / "BebasNeue-Regular.ttf"), size)


@functools.lru_cache(maxsize=None)
def rob(size: int, peso: int = 400) -> ImageFont.FreeTypeFont:
    f = ImageFont.truetype(str(FONTES / "RobotoCondensed[wght].ttf"), size)
    f.set_variation_by_axes([peso])
    return f


@functools.lru_cache(maxsize=None)
def mono(size: int) -> ImageFont.FreeTypeFont:
    for pasta in _DIRS_MONO:
        for nome in _ARQ_MONO:
            caminho = pathlib.Path(pasta) / nome
            if caminho.exists():
                return ImageFont.truetype(str(caminho), size)
    return rob(size, 400)


def hexrgb(c: str) -> tuple[int, int, int]:
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def mix(a, b, t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def wrap(draw: ImageDraw.ImageDraw, text: str, font, largura: float) -> list[str]:
    """Quebra o texto em linhas que cabem na largura (uma palavra longa fica só)."""
    linhas, atual = [], ""
    for p in text.split():
        t = f"{atual} {p}".strip()
        if draw.textlength(t, font=font) <= largura or not atual:
            atual = t
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def limitar_linhas(draw, linhas: list[str], font, largura: float, maximo: int) -> list[str]:
    """No máximo `maximo` linhas; o que passar vira reticências na última."""
    if len(linhas) <= maximo:
        return linhas
    ultima = linhas[maximo - 1] + " " + " ".join(linhas[maximo:])
    while ultima and draw.textlength(ultima + "…", font=font) > largura:
        ultima = ultima[:-1]
    return linhas[: maximo - 1] + [ultima.rstrip(" ,;:.") + "…"]


# ---------------------------------------------------------------- fundos


def grad(bw: int, bh: int, topo, base) -> Image.Image:
    img = Image.new("RGB", (bw, bh))
    d = ImageDraw.Draw(img)
    for y in range(bh):
        d.line([(0, y), (bw, y)], fill=mix(topo, base, y / bh))
    return img


def estrelas(d, bw: int, limite: int, n: int, rng) -> None:
    for _ in range(n):
        x, y = rng.randint(0, bw), rng.randint(0, limite)
        r = rng.choice([1, 1, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=mix((120, 130, 150), (255, 255, 255), rng.random()))


def ondas(img: Image.Image, y0: int, cor, rng, passo: int = 14) -> None:
    d = ImageDraw.Draw(img)
    bw, bh = img.size
    for k, y in enumerate(range(y0, bh, passo)):
        pts = [(x, y + 3 * math.sin((x + k * 37) / 23)) for x in range(0, bw + 8, 8)]
        d.line(pts, fill=mix(cor, (255, 255, 255), 0.10 + 0.04 * (k % 3)), width=2)
