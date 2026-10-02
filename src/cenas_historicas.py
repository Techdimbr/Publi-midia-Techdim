"""Cenas históricas: cinco histórias reais (ou lendas) que viram lição de TI.

Cada uma é uma ilustração vetorial desenhada por código. Entram no registro de
cenas de cenas.py e podem ser pedidas com "cena": "titanic" etc.
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

from desenho import SCENE, bebas, hexrgb, rob
from desenho import estrelas as _estrelas
from desenho import grad as _grad
from desenho import ondas as _ondas


def cena_titanic(acc, rng, p=None):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = _grad(bw, bh, (6, 12, 30), (18, 60, 90))
    d = ImageDraw.Draw(img)
    _estrelas(d, bw, 200, 70, rng)
    mar = 330
    d.rectangle([0, mar, bw, bh], fill=(10, 34, 58))
    # iceberg: ponta acima da água e massa abaixo
    d.polygon([(380, mar), (420, 255), (445, 272), (472, 215), (500, 250), (bw, mar)], fill=(205, 228, 245))
    d.polygon([(420, 255), (445, 272), (430, mar), (400, mar)], fill=(150, 185, 210))
    sub = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(sub).polygon([(360, mar), (bw, mar), (bw, 430), (470, 445), (400, 400)], fill=(120, 170, 210, 90))
    img.paste(sub, (0, 0), sub)
    # navio
    d.polygon([(25, 285), (395, 285), (440, 258), (405, 332), (60, 332)], fill=(14, 18, 26))
    d.rectangle([85, 245, 360, 285], fill=(20, 26, 36))
    d.rectangle([125, 220, 330, 245], fill=(26, 33, 45))
    for x in (150, 200, 250, 300):
        d.rectangle([x, 175, x + 24, 220], fill=(26, 33, 45))
        d.rectangle([x, 175, x + 24, 189], fill=(255, 176, 0))
    for x in range(100, 350, 11):
        d.rectangle([x, 262, x + 4, 267], fill=(255, 210, 120))
    for i in range(20):  # os 20 botes salva-vidas
        x = 132 + i * 9.6
        d.rounded_rectangle([x, 212, x + 7, 218], 2, fill=hexrgb("#4DA3FF"))
    _ondas(img, mar + 4, (30, 80, 120), rng)
    d.text((18, bh - 52), "20 BOTES  ·  ~1.178 LUGARES  ·  ~2.224 A BORDO", font=rob(17, 700), fill=(200, 220, 235))
    return img


def cena_maginot(acc, rng, p=None):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = Image.new("RGB", (bw, bh), (20, 14, 16))
    d = ImageDraw.Draw(img)
    for x in range(0, bw, 40):
        d.line([(x, 0), (x, bh)], fill=(34, 24, 28))
    for y in range(0, bh, 40):
        d.line([(0, y), (bw, y)], fill=(34, 24, 28))
    # floresta (Ardenas) à direita
    for _ in range(60):
        x, y = rng.randint(340, bw - 10), rng.randint(40, bh - 20)
        s = rng.randint(14, 26)
        d.polygon([(x, y - s), (x - s // 2, y + s // 2), (x + s // 2, y + s // 2)], fill=(24, rng.randint(56, 84), 40))
    d.text((352, 56), "ARDENAS", font=rob(20, 700), fill=(150, 200, 150))
    d.text((352, 80), "(fora da linha)", font=rob(16, 400), fill=(120, 160, 120))
    # linha fortificada
    ym = 215
    d.rectangle([30, ym, 330, ym + 22], fill=(70, 74, 82))
    for x in range(52, 330, 56):
        d.pieslice([x - 22, ym - 22, x + 22, ym + 22], 180, 360, fill=(104, 110, 120))
        d.line([(x, ym - 6), (x + 22, ym - 24)], fill=(160, 166, 176), width=4)
    d.text((34, ym + 32), "LINHA FORTIFICADA", font=rob(18, 700), fill=(200, 205, 212))
    # ataque de frente: bloqueado
    d.line([(290, 440), (290, ym + 40)], fill=acc, width=6)
    d.polygon([(290, ym + 36), (276, ym + 62), (304, ym + 62)], fill=acc)
    d.line([(272, ym + 62), (308, ym + 98)], fill=(255, 255, 255), width=5)
    d.line([(308, ym + 62), (272, ym + 98)], fill=(255, 255, 255), width=5)
    d.text((180, 262), "bloqueado", font=rob(18, 400), fill=(255, 190, 190))
    # contorno: passa por fora e entra por trás
    pts = [(300, 440), (400, 420), (430, 300), (410, 160), (330, 88), (220, 74), (150, 70)]
    for a, b in zip(pts, pts[1:], strict=False):
        d.line([a, b], fill=acc, width=6)
    d.polygon([(130, 70), (160, 54), (160, 86)], fill=acc)
    d.text((150, 36), "contornado", font=rob(18, 700), fill=acc)
    d.text((18, bh - 40), "1940: A LINHA FOI CONTORNADA", font=rob(17, 700), fill=(220, 190, 190))
    return img


def cena_vasa(acc, rng, p=None):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = _grad(bw, bh, (20, 18, 30), (40, 70, 90))
    d = ImageDraw.Draw(img)
    _estrelas(d, bw, 160, 40, rng)
    nav = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    n = ImageDraw.Draw(nav)
    n.polygon([(110, 300), (400, 300), (360, 380), (150, 380)], fill=(60, 40, 24, 255))
    n.polygon([(70, 205), (150, 205), (170, 300), (110, 300)], fill=(78, 52, 30, 255))  # castelo de popa
    n.rectangle([86, 175, 150, 205], fill=(92, 62, 36, 255))
    for x, topo in ((190, 100), (265, 80), (340, 110)):
        n.rectangle([x - 3, topo, x + 3, 300], fill=(50, 34, 20, 255))
        for y0, h, larg in ((topo + 10, 70, 74), (topo + 92, 90, 90)):
            n.rectangle([x - larg // 2, y0, x + larg // 2, y0 + h], fill=(224, 212, 184, 255))
    for x in range(170, 380, 34):
        n.rectangle([x, 322, x + 14, 336], fill=(18, 12, 8, 255))
    n.line([(110, 300), (400, 300)], fill=(255, 176, 0, 255), width=4)
    nav = nav.rotate(-20, center=(260, 340), resample=Image.BICUBIC)
    img.paste(nav, (0, 0), nav)
    d = ImageDraw.Draw(img)
    mar = 360
    agua = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(agua).rectangle([0, mar, bw, bh], fill=(14, 52, 72, 200))
    img.paste(agua, (0, 0), agua)
    _ondas(img, mar, (30, 100, 130), rng, 16)
    d = ImageDraw.Draw(img)
    for _ in range(26):
        x, y, r = rng.randint(40, 470), rng.randint(mar + 10, bh - 50), rng.randint(3, 9)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(150, 210, 230), width=2)
    d.text((18, bh - 40), "10/08/1628  ·  PRIMEIRA VIAGEM", font=rob(17, 700), fill=(210, 225, 235))
    return img


def cena_apollo(acc, rng, p=None):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = Image.new("RGB", (bw, bh), (5, 7, 14))
    d = ImageDraw.Draw(img)
    _estrelas(d, bw, bh, 120, rng)
    glow = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([-120, 250, 280, 650], fill=(60, 140, 255, 130))
    glow = glow.filter(ImageFilter.GaussianBlur(26))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img)
    d.ellipse([-100, 270, 260, 630], fill=(22, 70, 140))
    d.ellipse([-40, 330, 120, 450], fill=(40, 120, 70))
    d.ellipse([60, 400, 200, 520], fill=(36, 106, 64))
    d.ellipse([360, 70, 440, 150], fill=(150, 150, 156))
    for cx, cy, r in ((385, 95, 7), (415, 118, 5), (395, 128, 4)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(110, 110, 116))
    # trajetória em oito
    pts = []
    for t in range(0, 101):
        a = t / 100 * 2 * math.pi
        pts.append((250 + 150 * math.sin(a), 270 - 120 * math.sin(a) * math.cos(a)))
    for i in range(0, len(pts) - 1, 2):
        d.line([pts[i], pts[i + 1]], fill=acc, width=3)
    cap = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    c = ImageDraw.Draw(cap)
    c.rectangle([200, 245, 280, 285], fill=(210, 214, 220, 255))
    c.polygon([(280, 245), (280, 285), (330, 265)], fill=(236, 238, 242, 255))
    c.polygon([(200, 255), (176, 248), (176, 282), (200, 275)], fill=(120, 124, 132, 255))
    c.rectangle([220, 245, 226, 285], fill=(150, 156, 164, 255))
    cap = cap.rotate(18, center=(255, 265), resample=Image.BICUBIC)
    img.paste(cap, (0, 0), cap)
    d = ImageDraw.Draw(img)
    # o problema dos filtros: quadrado × redondo
    d.rounded_rectangle([250, 380, 470, 460], 10, outline=(90, 100, 118), width=2, fill=(10, 14, 24))
    d.rectangle([266, 400, 306, 440], outline=acc, width=4)
    d.text((262, 444), "QUADRADO", font=rob(13, 700), fill=(200, 205, 212))
    d.polygon([(320, 412), (345, 412), (345, 404), (362, 420), (345, 436), (345, 428), (320, 428)], fill=(255, 255, 255))
    d.ellipse([376, 400, 416, 440], outline=(120, 220, 160), width=4)
    d.text((372, 444), "REDONDO", font=rob(13, 700), fill=(200, 205, 212))
    d.text((430, 408), "CO₂", font=bebas(40), fill=(255, 255, 255))
    d.text((18, bh - 40), "ABRIL DE 1970  ·  APOLLO 13", font=rob(17, 700), fill=(210, 220, 235))
    return img


def cena_troia(acc, rng, p=None):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = _grad(bw, bh, (30, 16, 40), (120, 56, 40))
    d = ImageDraw.Draw(img)
    chao = 400
    d.rectangle([0, chao, bw, bh], fill=(30, 20, 18))
    # muralha e portão
    d.rectangle([300, 190, bw, chao], fill=(70, 52, 48))
    for x in range(300, bw, 36):
        d.rectangle([x, 168, x + 20, 190], fill=(70, 52, 48))
    for x in (320, 420):
        d.rectangle([x, 120, x + 50, 190], fill=(84, 62, 56))
        d.rectangle([x + 18, 150, x + 32, 176], fill=(20, 14, 14))
    d.rounded_rectangle([360, 270, 440, chao], 40, fill=(18, 12, 12))
    d.rectangle([360, 330, 440, chao], fill=(18, 12, 12))
    # cavalo de madeira
    mad, ripa = (122, 78, 44), (150, 100, 58)
    d.polygon([(235, 250), (275, 168), (312, 184), (288, 262)], fill=mad)
    d.polygon([(275, 168), (338, 164), (350, 192), (310, 200)], fill=mad)
    d.polygon([(280, 168), (286, 144), (298, 168)], fill=mad)
    d.rounded_rectangle([105, 245, 255, 312], 14, fill=mad)
    d.polygon([(108, 252), (74, 300), (92, 306), (120, 276)], fill=mad)
    for x in (122, 160, 214, 240):
        d.rectangle([x, 312, x + 20, 376], fill=mad)
        d.rectangle([x - 2, 372, x + 22, 382], fill=(90, 56, 32))
    for y in (262, 280, 298):
        d.line([(112, y), (250, y)], fill=ripa, width=2)
    d.ellipse([322, 176, 330, 184], fill=(255, 200, 120))
    d.rectangle([90, 386, 268, 396], fill=(70, 46, 28))
    for x in (110, 170, 230):
        d.ellipse([x - 12, 392, x + 12, 416], fill=(50, 34, 22), outline=ripa, width=2)
    d.text((18, bh - 40), "O 'PRESENTE' QUE ABRIU OS PORTÕES", font=rob(17, 700), fill=(240, 215, 200))
    return img


