"""Renderização das imagens no tema NOC da TECHDIM.

Cada tema tem cor de acento e um motivo gráfico gerado por código, para que as
quatro publicações do dia não se pareçam. O motivo é determinístico: a mesma
data e o mesmo tema produzem sempre a mesma arte, o que torna uma falha
reproduzível.
"""
from __future__ import annotations

import logging
import math
import pathlib
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config
import infografico

log = logging.getLogger(__name__)

FONT_DIRS = [
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/TTF",
    "/Library/Fonts",
    "C:/Windows/Fonts",
]
FONT_FILES = {
    "bold": ["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"],
    "regular": ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"],
    "mono": ["DejaVuSansMono.ttf", "Courier New.ttf", "cour.ttf"],
    "monobold": ["DejaVuSansMono-Bold.ttf", "Courier New Bold.ttf", "courbd.ttf"],
}


def _font(style: str, size: int) -> ImageFont.FreeTypeFont:
    for directory in FONT_DIRS:
        for name in FONT_FILES[style]:
            path = pathlib.Path(directory) / name
            if path.exists():
                return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size)


def _rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _mix(a: str, b: str, t: float) -> tuple[int, int, int]:
    ra, rb = _rgb(a), _rgb(b)
    return tuple(int(ra[i] + (rb[i] - ra[i]) * t) for i in range(3))  # type: ignore[return-value]


# ---------------------------------------------------------------- texto


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words, lines, current = text.split(), [], ""
    for word in words:
        probe = f"{current} {word}".strip()
        if draw.textlength(probe, font=font) <= max_width or not current:
            current = probe
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _fit(
    draw: ImageDraw.ImageDraw,
    text: str,
    style: str,
    max_width: int,
    max_height: int,
    start: int,
    minimum: int = 22,
) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    """Maior corpo de fonte em que o texto ainda cabe na caixa."""
    size = start
    while size > minimum:
        font = _font(style, size)
        lines = _wrap(draw, text, font, max_width)
        leading = int(size * 1.28)
        if len(lines) * leading <= max_height:
            return font, lines, leading
        size -= 2
    font = _font(style, minimum)
    return font, _wrap(draw, text, font, max_width), int(minimum * 1.28)


# ---------------------------------------------------------------- motivos


def _motif_ondas(img: Image.Image, st: dict, rng: random.Random) -> None:
    """Notícias: ondas concêntricas de transmissão, saindo do canto."""
    w, h = img.size
    layer = Image.new("RGB", (w, h), config.BG)
    draw = ImageDraw.Draw(layer)
    cx, cy = int(w * 1.05), int(h * 0.12)
    passo = int(w * 0.075)
    for i in range(22):
        r = passo * (i + 1) + rng.randint(-6, 6)
        t = min(1.0, i / 16)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=_mix(st["accent"], config.BG, 0.72 + t * 0.26),
            width=3 if i % 3 else 5,
        )
    img.paste(Image.blend(img, layer, 0.95), (0, 0))

    # barra de espectro no rodapé
    draw = ImageDraw.Draw(img)
    base_y = int(h * 0.80)
    largura = int(w * 0.018)
    x = 0
    while x < w:
        alt = int(abs(math.sin(x / (w * 0.07))) * h * 0.055) + 6
        draw.rectangle(
            [x, base_y - alt, x + largura - 4, base_y],
            fill=_mix(st["accent"], config.BG, 0.80),
        )
        x += largura


def _motif_scanlines(img: Image.Image, st: dict, rng: random.Random) -> None:
    """Hacker: scanlines, bloco de hexdump e faixa de glitch."""
    w, h = img.size
    draw = ImageDraw.Draw(img)

    for y in range(0, h, 4):
        draw.line([(0, y), (w, y)], fill=_mix(config.BG, st["accent"], 0.07), width=1)

    # hexdump de fundo
    mono = _font("mono", int(w * 0.021))
    hexa = "0123456789ABCDEF"
    y = int(h * 0.60)
    while y < h - int(h * 0.10):
        linha = " ".join(
            "".join(rng.choice(hexa) for _ in range(2)) for _ in range(26)
        )
        draw.text(
            (int(w * 0.06), y),
            linha,
            font=mono,
            fill=_mix(config.BG, st["second"], 0.16),
        )
        y += int(w * 0.030)

    # faixas de glitch
    for _ in range(3):
        gy = rng.randint(int(h * 0.12), int(h * 0.88))
        gh = rng.randint(4, 14)
        draw.rectangle(
            [0, gy, w, gy + gh], fill=_mix(config.BG, st["accent"], 0.30)
        )
        draw.rectangle(
            [rng.randint(0, w // 2), gy, w, gy + max(2, gh // 3)],
            fill=_mix(config.BG, st["second"], 0.35),
        )


def _motif_grade(img: Image.Image, st: dict, rng: random.Random) -> None:
    """Dica: grade técnica com nós acesos, como um diagrama de rede."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    passo = int(w * 0.055)

    for x in range(0, w + passo, passo):
        draw.line([(x, 0), (x, h)], fill=config.GRID, width=1)
    for y in range(0, h + passo, passo):
        draw.line([(0, y), (w, y)], fill=config.GRID, width=1)

    nos = [
        (x, y)
        for x in range(passo, w, passo)
        for y in range(passo, h, passo)
        if rng.random() < 0.07
    ]
    for x, y in nos:
        r = rng.choice([3, 4, 6])
        draw.ellipse(
            [x - r, y - r, x + r, y + r],
            fill=_mix(st["accent"], config.BG, 0.45),
        )
    # alguns enlaces entre nós vizinhos
    for i in range(min(len(nos) - 1, 14)):
        a, b = nos[i], nos[i + 1]
        if abs(a[0] - b[0]) <= passo * 3 and abs(a[1] - b[1]) <= passo * 3:
            draw.line([a, b], fill=_mix(st["accent"], config.BG, 0.74), width=2)


def _motif_circuito(img: Image.Image, st: dict, rng: random.Random) -> None:
    """Serviço: trilhas de placa em ângulos retos, com terminais."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    passo = int(w * 0.045)

    for _ in range(26):
        x, y = rng.randrange(0, w, passo), rng.randrange(0, h, passo)
        cor = _mix(st["accent"] if rng.random() < 0.6 else st["second"], config.BG, 0.70)
        pontos = [(x, y)]
        for _ in range(rng.randint(3, 7)):
            if rng.random() < 0.5:
                x += rng.choice([-1, 1]) * passo * rng.randint(1, 4)
            else:
                y += rng.choice([-1, 1]) * passo * rng.randint(1, 4)
            pontos.append((x, y))
        draw.line(pontos, fill=cor, width=3, joint="curve")
        ex, ey = pontos[-1]
        draw.ellipse([ex - 6, ey - 6, ex + 6, ey + 6], outline=cor, width=3)


def _motif_radar(img: Image.Image, st: dict, rng: random.Random) -> None:
    """Destaque: radar com varredura e alvos detectados."""
    w, h = img.size
    draw = ImageDraw.Draw(img)
    cx, cy = int(w * 0.80), int(h * 0.30)
    raio = int(w * 0.62)

    # anéis e eixos
    for i in range(1, 6):
        r = raio * i // 5
        draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                     outline=_mix(st["accent"], config.BG, 0.80), width=2)
    draw.line([(cx - raio, cy), (cx + raio, cy)], fill=_mix(st["accent"], config.BG, 0.85), width=1)
    draw.line([(cx, cy - raio), (cx, cy + raio)], fill=_mix(st["accent"], config.BG, 0.85), width=1)

    # varredura: leque de raios cada vez mais apagados
    inicio = rng.uniform(150, 230)
    for k in range(40):
        ang = math.radians(inicio - k * 1.6)
        t = k / 40
        draw.line(
            [(cx, cy), (cx + raio * math.cos(ang), cy - raio * math.sin(ang))],
            fill=_mix(st["accent"], config.BG, 0.45 + t * 0.53),
            width=3,
        )

    # alvos detectados
    for _ in range(7):
        ang = math.radians(rng.uniform(0, 360))
        r = rng.uniform(0.2, 0.95) * raio
        x, y = cx + r * math.cos(ang), cy - r * math.sin(ang)
        tam = rng.choice([5, 7, 9])
        cor = _mix(st["second"], config.BG, rng.uniform(0.25, 0.55))
        draw.ellipse([x - tam, y - tam, x + tam, y + tam], fill=cor)
        draw.ellipse([x - tam * 2.2, y - tam * 2.2, x + tam * 2.2, y + tam * 2.2],
                     outline=cor, width=2)


_MOTIFS = {
    "ondas": _motif_ondas,
    "scanlines": _motif_scanlines,
    "grade": _motif_grade,
    "circuito": _motif_circuito,
    "radar": _motif_radar,
}


def _background(size: tuple[int, int], theme: str, seed: int) -> Image.Image:
    """Fundo NOC com o motivo do tema, levemente desfocado e escurecido."""
    w, h = size
    st = config.style(theme)
    rng = random.Random(f"{theme}-{seed}")

    img = Image.new("RGB", size, config.BG)
    _MOTIFS[st["motif"]](img, st, rng)
    img = img.filter(ImageFilter.GaussianBlur(0.6))

    # vinheta: escurece as bordas para o texto ganhar contraste
    vinheta = Image.new("L", size, 0)
    vd = ImageDraw.Draw(vinheta)
    vd.ellipse(
        [-int(w * 0.35), -int(h * 0.30), int(w * 1.35), int(h * 1.30)], fill=150
    )
    vinheta = vinheta.filter(ImageFilter.GaussianBlur(int(w * 0.10)))
    escuro = Image.new("RGB", size, config.BG)
    img = Image.composite(img, escuro, vinheta)

    # véu escuro uniforme: o motivo fica como textura, nunca disputa com o texto
    return Image.blend(img, Image.new("RGB", size, config.BG), 0.42)


# ---------------------------------------------------------------- moldura


def _chrome(draw: ImageDraw.ImageDraw, w: int, h: int, pad: int, st: dict) -> None:
    draw.rectangle([0, 0, w, 12], fill=st["accent"])
    draw.rectangle([0, h - 6, w, h], fill=_mix(st["second"], config.BG, 0.35))

    foot_size = int(w * 0.028)
    base = h - pad
    draw.line([(pad, base - int(w * 0.050)), (w - pad, base - int(w * 0.050))],
              fill=_mix(st["accent"], config.BG, 0.60), width=2)
    draw.text(
        (pad, base - int(w * 0.034)),
        config.BRAND,
        font=_font("bold", foot_size),
        fill=st["accent"],
    )
    draw.text(
        (pad, base + int(w * 0.002)),
        config.SITE,
        font=_font("mono", int(w * 0.022)),
        fill=config.MUTED,
    )


def _chip(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, color: str, w: int) -> int:
    size = int(w * 0.024)
    font = _font("monobold", size)
    label = text.upper()
    tw = draw.textlength(label, font=font)
    px, py = int(size * 0.7), int(size * 0.45)
    h = size + py * 2
    draw.rectangle([x, y, x + tw + px * 2, y + h], fill=_mix(color, config.BG, 0.82))
    draw.rectangle([x, y, x + tw + px * 2, y + h], outline=color, width=2)
    draw.rectangle([x, y, x + 6, y + h], fill=color)
    draw.text((x + px, y + py - 2), label, font=font, fill=color)
    return h


# ---------------------------------------------------------------- slides


def _area(w: int, h: int, pad: int) -> tuple[int, int]:
    return pad + int(w * 0.040), h - pad - int(w * 0.085)


def _slide_capa(draw, w, h, pad, slide, st, index, total) -> None:
    top, bottom = _area(w, h, pad)
    box_w = w - pad * 2

    font, lines, leading = _fit(
        draw, slide["titulo"], "bold", box_w,
        int((bottom - top) * 0.62), start=int(w * 0.088)
    )
    chip_h = int(w * 0.024) + int(w * 0.024 * 0.9)
    extra = int(w * 0.055) if total > 1 else 0
    if slide.get("fonte"):
        extra += int(w * 0.060)
    bloco = chip_h + int(w * 0.045) + len(lines) * leading + int(w * 0.030) + extra
    y = top + max(0, (bottom - top - bloco) // 2)

    y += _chip(draw, pad, y, slide["label"], st["accent"], w) + int(w * 0.045)
    for line in lines:
        draw.text((pad, y), line, font=font, fill=config.FG)
        y += leading

    y += int(w * 0.022)
    draw.rectangle([pad, y, pad + int(w * 0.16), y + 7], fill=st["second"])

    if slide.get("fonte"):
        y += int(w * 0.034)
        draw.text(
            (pad, y),
            f"fonte: {slide['fonte']}",
            font=_font("mono", int(w * 0.022)),
            fill=config.MUTED,
        )

    if total > 1:
        draw.text(
            (pad, y + int(w * 0.040)),
            "arraste \u2192",
            font=_font("mono", int(w * 0.026)),
            fill=config.MUTED,
        )


def _slide_ponto(draw, w, h, pad, slide, st, index, total) -> None:
    top, bottom = _area(w, h, pad)
    box_w = w - pad * 2

    num_size = int(w * 0.145)
    font, lines, leading = _fit(
        draw, slide["texto"], "regular", box_w,
        int((bottom - top) * 0.55), start=int(w * 0.058)
    )
    bloco = int(num_size * 1.10) + int(w * 0.040) + int(w * 0.040) + len(lines) * leading
    y = top + max(0, (bottom - top - bloco) // 2)

    # número grande com glifo do tema ao lado
    num_font = _font("bold", num_size)
    label = f"{slide['n']:02d}"
    draw.text((pad, y), label, font=num_font, fill=st["accent"])
    nw = draw.textlength(label, font=num_font)
    draw.text(
        (pad + nw + int(w * 0.020), y + int(num_size * 0.22)),
        st["glyph"],
        font=_font("monobold", int(num_size * 0.42)),
        fill=_mix(st["second"], config.BG, 0.45),
    )
    y += int(num_size * 1.10) + int(w * 0.040)

    draw.rectangle([pad, y, pad + int(w * 0.11), y + 6], fill=st["second"])
    y += int(w * 0.040)

    for line in lines:
        draw.text((pad, y), line, font=font, fill=config.FG)
        y += leading


def _slide_cta(draw, w, h, pad, slide, st, index, total) -> None:
    top, bottom = _area(w, h, pad)
    box_w = w - pad * 2

    mono_size = int(w * 0.038)
    linha = int(w * 0.058)
    font, lines, leading = _fit(
        draw, slide["fecho"], "bold", box_w,
        int((bottom - top) * 0.45), start=int(w * 0.068)
    )
    chip_h = int(w * 0.024) + int(w * 0.024 * 0.9)
    bloco = chip_h + int(w * 0.050) + len(lines) * leading + int(w * 0.050) + linha * 2
    y = top + max(0, (bottom - top - bloco) // 2)

    y += _chip(draw, pad, y, "fale com a techdim", st["accent"], w) + int(w * 0.050)
    for line in lines:
        draw.text((pad, y), line, font=font, fill=config.FG)
        y += leading

    y += int(w * 0.050)
    mono = _font("monobold", mono_size)
    draw.text((pad, y), f"\u25b8 {config.SITE}", font=mono, fill=st["accent"])
    y += linha
    draw.text(
        (pad, y),
        config.TAGLINE,
        font=_font("mono", int(mono_size * 0.80)),
        fill=config.MUTED,
    )


_RENDERERS = {"capa": _slide_capa, "ponto": _slide_ponto, "cta": _slide_cta}


def render_slide(
    slide: dict, size: tuple[int, int], theme: str, index: int, total: int, seed: int
) -> Image.Image:
    w, h = size
    pad = int(w * 0.075)
    st = config.style(theme)

    # o motivo varia por slide, para o carrossel não ficar repetitivo
    img = _background(size, theme, seed * 100 + index)
    draw = ImageDraw.Draw(img)

    _chrome(draw, w, h, pad, st)
    _RENDERERS[slide["kind"]](draw, w, h, pad, slide, st, index, total)

    if total > 1:
        mono = _font("mono", int(w * 0.024))
        tag = f"{index + 1:02d}/{total:02d}"
        tw = draw.textlength(tag, font=mono)
        draw.text((w - pad - tw, pad + int(w * 0.042)), tag, font=mono, fill=config.MUTED)

    return img


def render_infografico(post, destino: pathlib.Path, slug: str) -> pathlib.Path | None:
    """Infográfico do post (padrão visual atual), um só para todas as redes de feed.

    Devolve None quando o post não tem bloco "infografico" ou quando o desenho
    falha: aí quem chama usa a arte antiga, e o horário nunca fica sem post.
    """
    if not getattr(post, "infografico", None):
        return None
    try:
        return infografico.renderizar(post.infografico, post.theme, slug, destino)
    except Exception:  # noqa: BLE001 — um bloco ruim não pode derrubar a publicação
        log.exception("infográfico de %r falhou; usando a arte antiga", post.theme)
        return None


def render_post(post, network: str, out_dir: pathlib.Path, seed: int = 0) -> list[pathlib.Path]:
    """Gera os PNGs da arte antiga (carrossel/capa) no formato ideal da rede."""
    if network == "instagram_stories":
        return [render_story(post, out_dir, seed)]

    out_dir.mkdir(parents=True, exist_ok=True)
    size = config.SIZE_BY_NETWORK[network]

    # LinkedIn publica imagem única: só a capa, em 1:1.
    slides = post.slides[:1] if network == "linkedin" else post.slides

    paths: list[pathlib.Path] = []
    for i, slide in enumerate(slides):
        img = render_slide(slide, size, post.theme, i, len(slides), seed)
        path = out_dir / f"{post.theme}-{network}-{i + 1:02d}.png"
        img.save(path, "PNG", optimize=True)
        paths.append(path)
    return paths


def render_story(post, out_dir: pathlib.Path, seed: int = 0) -> pathlib.Path:
    """Story 9:16 para os temas de notícia: título, o que fazer e chamada para o post.

    O Instagram cobre ~250 px no topo (barra de progresso, perfil) e ~250 px
    embaixo (responder); o conteúdo fica entre essas faixas.
    """
    size = config.SIZE_STORY
    w, h = size
    pad = int(w * 0.08)
    st = config.style(post.theme)
    img = _background(size, post.theme, seed * 100 + 7)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, w, 14], fill=st["accent"])
    draw.rectangle([0, h - 8, w, h], fill=_mix(st["second"], config.BG, 0.35))

    top, bottom = 290, h - 330
    box_w = w - pad * 2
    label = config.THEME_LABELS.get(post.theme, post.theme)

    # Pedido de resposta. Responder um Story é mandar uma DM: conta como
    # interação para o alcance e abre conversa com quem pode virar cliente. É a
    # única conversão que a API permite — o adesivo de link não é publicável por
    # API, só à mão.
    pergunta = getattr(post, "pergunta", "")
    pergunta_h = 0
    if pergunta:
        rotulo_p = int(w * 0.028)
        font_p, linhas_p, lead_p = _fit(
            draw, pergunta, "regular", box_w, int(w * 0.13), start=int(w * 0.042)
        )
        # folga de 24: o "Post completo no perfil" + @perfil ocupam um pouco mais
        # do que o 0,11·w reservado para eles no cálculo abaixo
        pergunta_h = 56 + rotulo_p + 18 + len(linhas_p) * lead_p + 24

    chip_h = int(w * 0.024) + int(w * 0.024 * 0.9)
    rotulo_h = int(w * 0.030)

    # Tudo que tem altura fixa vem primeiro; título e "o que fazer" dividem o que
    # sobra, na proporção de sempre (62% / 38%). Antes cada um tinha um teto
    # próprio, calibrado sem o pedido de resposta, e a soma passava do espaço: com
    # uma pauta real de serviço o texto invadia a marca do rodapé.
    fixo = (
        chip_h + 50 + 40 + 8 + 60
        + (28 + int(w * 0.024) if post.fontes else 0)
        + rotulo_h + 24 + 70 + int(w * 0.11) + pergunta_h
    )
    resto = max((bottom - top) - fixo, int((bottom - top) * 0.30))
    font_t, linhas_t, lead_t = _fit(
        draw, post.titulo, "bold", box_w, int(resto * 0.62), start=int(w * 0.092)
    )
    reco = post.pontos[-1] if post.pontos else ""
    font_r, linhas_r, lead_r = _fit(
        draw, reco, "regular", box_w - 48, int(resto * 0.38), start=int(w * 0.048)
    )
    bloco = fixo + len(linhas_t) * lead_t + len(linhas_r) * lead_r
    y = top + max(0, (bottom - top - bloco) // 2)

    y += _chip(draw, pad, y, label, st["accent"], w) + 50
    for linha in linhas_t:
        draw.text((pad, y), linha, font=font_t, fill=config.FG)
        y += lead_t
    y += 40
    draw.rectangle([pad, y, pad + int(w * 0.16), y + 8], fill=st["second"])
    y += 8
    if post.fontes:
        fonte = "fonte: " + " · ".join(nome for nome, _ in post.fontes[:2])
        draw.text((pad, y + 28), fonte, font=_font("mono", int(w * 0.024)), fill=config.MUTED)
        y += 28 + int(w * 0.024)
    y += 60

    # caixa "o que fazer"
    caixa_top = y
    draw.text((pad + 36, y), "O QUE FAZER", font=_font("monobold", rotulo_h), fill=st["accent"])
    y += rotulo_h + 24
    for linha in linhas_r:
        draw.text((pad + 36, y), linha, font=font_r, fill=config.FG)
        y += lead_r
    draw.rectangle([pad, caixa_top - 6, pad + 8, y + 6], fill=st["accent"])
    y += 70

    draw.text((pad, y), "Post completo no perfil", font=_font("regular", int(w * 0.040)), fill=config.MUTED)
    y += int(w * 0.055)
    draw.text((pad, y), config.IG_HANDLE, font=_font("bold", int(w * 0.060)), fill=st["accent"])

    if pergunta_h:
        y += int(w * 0.075) + 56
        draw.text((pad, y), "RESPONDE AQUI EMBAIXO", font=_font("monobold", rotulo_p), fill=st["second"])
        y += rotulo_p + 18
        for linha in linhas_p:
            draw.text((pad, y), linha, font=font_p, fill=config.FG)
            y += lead_p

    # marca, logo acima da faixa coberta pelo campo "responder"
    base = h - 330 + 90
    draw.line([(pad, base - 26), (w - pad, base - 26)], fill=_mix(st["accent"], config.BG, 0.60), width=2)
    draw.text((pad, base), config.BRAND, font=_font("bold", int(w * 0.034)), fill=st["accent"])
    draw.text(
        (pad, base + int(w * 0.046)), config.SITE,
        font=_font("mono", int(w * 0.026)), fill=config.MUTED,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{post.theme}-instagram_stories-01.png"
    img.save(path, "PNG", optimize=True)
    return path
