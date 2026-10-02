"""Infográficos de 1080×1350: uma história real (ou lenda) que vira lição de TI.

Cada peça tem título em duas cores, texto curto, "3 lições táticas", uma
pergunta final com chamada para conversar, e uma cena ilustrada por código
(vetorial, sem banco de imagem). Fontes: Bebas Neue e Roboto Condensed (OFL).
"""
from __future__ import annotations

import math
import pathlib
import random
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import config

ROOT = pathlib.Path(__file__).resolve().parent.parent
W, H = 1080, 1350
BG = (10, 13, 19)
FG = (236, 240, 245)
MUTED = (150, 160, 172)

SCENE = (560, 150, 1040, 640)  # x0, y0, x1, y1


def bebas(size):
    return ImageFont.truetype(str(ROOT / "fonts" / "BebasNeue-Regular.ttf"), size)


def rob(size, peso=400):
    f = ImageFont.truetype(str(ROOT / "fonts" / "RobotoCondensed[wght].ttf"), size)
    f.set_variation_by_axes([peso])
    return f


def hexrgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def wrap(draw, text, font, largura):
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


# ---------------------------------------------------------------- cenas
# Cada cena desenha numa tela local (bw × bh) e devolve uma imagem RGBA.


def _grad(bw, bh, topo, base):
    img = Image.new("RGB", (bw, bh))
    d = ImageDraw.Draw(img)
    for y in range(bh):
        d.line([(0, y), (bw, y)], fill=mix(topo, base, y / bh))
    return img


def _estrelas(d, bw, limite, n, rng):
    for _ in range(n):
        x, y = rng.randint(0, bw), rng.randint(0, limite)
        r = rng.choice([1, 1, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=mix((120, 130, 150), (255, 255, 255), rng.random()))


def _ondas(img, y0, cor, rng, passo=14):
    d = ImageDraw.Draw(img)
    bw, bh = img.size
    for k, y in enumerate(range(y0, bh, passo)):
        pts = [(x, y + 3 * math.sin((x + k * 37) / 23)) for x in range(0, bw + 8, 8)]
        d.line(pts, fill=mix(cor, (255, 255, 255), 0.10 + 0.04 * (k % 3)), width=2)


def cena_titanic(acc, rng):
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
    rot = bebas(24)
    d.text((18, bh - 52), "20 BOTES  ·  ~1.178 LUGARES  ·  ~2.224 A BORDO", font=rob(17, 700), fill=(200, 220, 235))
    return img


def cena_maginot(acc, rng):
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
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=acc, width=6)
    d.polygon([(130, 70), (160, 54), (160, 86)], fill=acc)
    d.text((150, 36), "contornado", font=rob(18, 700), fill=acc)
    d.text((18, bh - 40), "1940: A LINHA FOI CONTORNADA", font=rob(17, 700), fill=(220, 190, 190))
    return img


def cena_vasa(acc, rng):
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
        for k, (y0, h, larg) in enumerate(((topo + 10, 70, 74), (topo + 92, 90, 90))):
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


def cena_apollo(acc, rng):
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


def cena_troia(acc, rng):
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


CENAS = {
    "titanic": cena_titanic, "maginot": cena_maginot, "vasa": cena_vasa,
    "apollo": cena_apollo, "troia": cena_troia,
}


def desenhar(p: dict, caminho: pathlib.Path) -> pathlib.Path:
    acc = hexrgb(p["cor"])
    rng = random.Random(p["slug"])
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # fundo: grade fina e brilho na cor de destaque
    for x in range(0, W, 54):
        d.line([(x, 0), (x, H)], fill=(14, 18, 26))
    for y in range(0, H, 54):
        d.line([(0, y), (W, y)], fill=(14, 18, 26))
    brilho = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(brilho).ellipse([520, 40, 1160, 700], fill=acc + (46,))
    brilho = brilho.filter(ImageFilter.GaussianBlur(70))
    img.paste(brilho, (0, 0), brilho)
    d = ImageDraw.Draw(img)

    # cena com bordas suaves
    x0, y0, x1, y1 = SCENE
    cena = CENAS[p["cena"]](acc, rng).convert("RGB")
    mascara = Image.new("L", cena.size, 0)
    md = ImageDraw.Draw(mascara)
    md.rounded_rectangle([0, 0, cena.size[0], cena.size[1]], 26, fill=255)
    img.paste(cena, (x0, y0), mascara)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], 26, outline=mix(acc, BG, 0.45), width=2)

    # barra vertical e título
    d.rectangle([40, 150, 48, 470], fill=acc)
    x = 68
    larg = 470
    y = 146
    branco = " ".join(p["titulo_branco"].split())
    destaque = " ".join(p["titulo_destaque"].split())
    tam = 104
    while tam > 56:
        f = bebas(tam)
        linhas_b = wrap(d, branco, f, larg)
        linhas_d = wrap(d, destaque, f, larg)
        if (len(linhas_b) + len(linhas_d)) * int(tam * 0.98) <= 330:
            break
        tam -= 4
    for ln in linhas_b:
        d.text((x, y), ln, font=f, fill=FG)
        y += int(tam * 0.98)
    for ln in linhas_d:
        d.text((x, y), ln, font=f, fill=acc)
        y += int(tam * 0.98)

    # texto da história
    y = max(y + 16, 500)
    corpo = rob(25, 400)
    for ln in wrap(d, p["historia"], corpo, 468):
        if y > 640:
            break
        d.text((x, y), ln, font=corpo, fill=(206, 212, 220))
        y += 31

    # 3 lições táticas
    yb = 690
    d.line([(40, yb + 22), (330, yb + 22)], fill=mix(acc, BG, 0.55), width=2)
    d.line([(750, yb + 22), (1040, yb + 22)], fill=mix(acc, BG, 0.55), width=2)
    d.text((360, yb - 8), "3", font=bebas(60), fill=acc)
    d.text((388, yb), "LIÇÕES TÁTICAS", font=bebas(46), fill=FG)
    colw = 330
    for i, (tit, txt) in enumerate(p["licoes"]):
        cx = 40 + i * (colw + 5)
        if i:
            d.line([(cx - 4, yb + 70), (cx - 4, yb + 330)], fill=(40, 48, 60), width=2)
        d.ellipse([cx + 4, yb + 70, cx + 74, yb + 140], outline=acc, width=3)
        d.text((cx + 39, yb + 105), str(i + 1), font=bebas(46), fill=acc, anchor="mm")
        ft = rob(23, 800)
        yy = yb + 70
        for ln in wrap(d, tit.upper(), ft, colw - 100):
            d.text((cx + 90, yy), ln, font=ft, fill=FG)
            yy += 27
        yy = max(yy + 4, yb + 158)
        ftx = rob(21, 400)
        for ln in wrap(d, txt, ftx, colw - 16):
            d.text((cx + 6, yy), ln, font=ftx, fill=(190, 198, 208))
            yy += 26

    # pergunta final e chamada
    yc = 1060
    d.rounded_rectangle([40, yc, 1040, yc + 112], 12, outline=mix(acc, BG, 0.35), width=2, fill=(14, 18, 26))
    d.rounded_rectangle([780, yc, 1040, yc + 112], 12, fill=acc)
    d.rectangle([780, yc, 800, yc + 112], fill=acc)
    pf = rob(27, 800)
    yy = yc + 16
    for ln in wrap(d, p["pergunta"].upper(), pf, 700):
        d.text((70, yy), ln, font=pf, fill=FG)
        yy += 33
    d.text((910, yc + 40), "VAMOS", font=bebas(48), fill=(10, 13, 19), anchor="mm")
    d.text((910, yc + 80), "CONVERSAR?", font=bebas(48), fill=(10, 13, 19), anchor="mm")

    # rodapé
    d.text((40, 1244), " ".join(p["hashtags"]), font=rob(19, 700), fill=mix(acc, FG, 0.25))
    d.line([(40, 1282), (1040, 1282)], fill=(34, 42, 54), width=2)
    d.text((40, 1296), "TECHDIM", font=bebas(40), fill=acc)
    d.text((1040, 1306), config.SITE, font=rob(24, 600), fill=MUTED, anchor="ra")

    caminho.parent.mkdir(parents=True, exist_ok=True)
    img.save(caminho, "PNG", optimize=True)
    return caminho


PECAS = [
    {
        "slug": "01-titanic-backup", "cena": "titanic", "cor": "#4DA3FF",
        "titulo_branco": "O Titanic tinha botes para cerca de",
        "titulo_destaque": "metade de quem estava a bordo.",
        "historia": "O navio cumpria a norma da época e era tido como praticamente inafundável. Na TI é parecido: muita empresa faz backup só para cumprir tabela, e nunca testou se ele restaura.",
        "licoes": [
            ("Regra 3-2-1", "Três cópias dos dados, em duas mídias diferentes, com uma delas fora do local."),
            ("Teste a restauração", "Backup que nunca foi restaurado é só esperança. Agende testes periódicos."),
            ("Meça o tempo de volta", "Defina em quanto tempo o negócio precisa voltar e quanto dado pode perder."),
        ],
        "pergunta": "Se o seu sistema parar hoje, em quanto tempo a sua empresa volta?",
        "hashtags": ["#BACKUP", "#CONTINUIDADE", "#INFRAESTRUTURA", "#TI", "#TECHDIM"],
    },
    {
        "slug": "02-maginot-defesa-em-camadas", "cena": "maginot", "cor": "#FF3B30",
        "titulo_branco": "A Linha Maginot era impenetrável.",
        "titulo_destaque": "Pela frente.",
        "historia": "Nos anos 1930 a França fortificou a fronteira com a Alemanha. Em 1940 o ataque contornou a linha pelas Ardenas. Segurança que protege um único ponto deixa o resto exposto.",
        "licoes": [
            ("Defesa em camadas", "Firewall, e-mail, estações e acessos: cada camada cobre a falha da outra."),
            ("Proteja a pessoa", "Phishing e senha fraca contornam o firewall. Treine a equipe e use verificação em duas etapas."),
            ("Revise o mapa", "A infraestrutura muda. Revise o que está exposto a cada mudança relevante."),
        ],
        "pergunta": "A sua segurança cobre todas as entradas ou só a principal?",
        "hashtags": ["#CIBERSEGURANÇA", "#DEFESAEMCAMADAS", "#ZEROTRUST", "#TI", "#TECHDIM"],
    },
    {
        "slug": "03-vasa-teste-antes-de-publicar", "cena": "vasa", "cor": "#FFB000",
        "titulo_branco": "O Vasa afundou na primeira viagem,",
        "titulo_destaque": "a menos de 2 km do porto.",
        "historia": "O navio de guerra mais ambicioso da Suécia saiu sem passar por um teste de estabilidade: o teste foi interrompido porque ele balançava demais. Mudança em produção sem teste é a versão moderna disso.",
        "licoes": [
            ("Teste antes de publicar", "Valide em um ambiente de homologação antes de mexer no sistema real."),
            ("Tenha plano de volta", "Toda mudança precisa de um procedimento claro para desfazer."),
            ("Janela e responsável", "Mude fora do horário de pico, com alguém acompanhando de ponta a ponta."),
        ],
        "pergunta": "As mudanças de TI da sua empresa passam por teste antes de ir ao ar?",
        "hashtags": ["#GESTÃODEMUDANÇA", "#HOMOLOGAÇÃO", "#DEVOPS", "#TI", "#TECHDIM"],
    },
    {
        "slug": "04-apollo-13-resposta-a-incidentes", "cena": "apollo", "cor": "#FF8A00",
        "titulo_branco": "Na Apollo 13, a solução veio com o que havia",
        "titulo_destaque": "a bordo e muito método.",
        "historia": "Os filtros de CO₂ do módulo de comando eram quadrados e os do módulo lunar, redondos. Engenheiros em Terra criaram um adaptador com itens da própria tripulação. Incidente se resolve com plano, comunicação e prática.",
        "licoes": [
            ("Plano de resposta", "Defina quem decide, quem comunica e quem executa antes de o incidente acontecer."),
            ("Simule a falha", "Exercícios periódicos mostram o que o papel esconde."),
            ("Comunicação clara", "Um canal único e o registro de cada ação feita durante o incidente."),
        ],
        "pergunta": "A sua empresa sabe o que fazer nos primeiros 15 minutos de um incidente?",
        "hashtags": ["#INCIDENTES", "#RESILIÊNCIA", "#SEGURANÇA", "#TI", "#TECHDIM"],
    },
    {
        "slug": "05-troia-engenharia-social", "cena": "troia", "cor": "#2EE59D",
        "titulo_branco": "Troia resistiu ao cerco.",
        "titulo_destaque": "Um presente abriu os portões.",
        "historia": "Na lenda grega, a muralha não cedeu à força: a cidade abriu o portão para um presente. Hoje o cavalo de Troia chega por e-mail, anexo ou instalador falso, e quem abre é a própria equipe.",
        "licoes": [
            ("Desconfie do presente", "Remetente inesperado, urgência e anexo pedem confirmação por outro canal."),
            ("Menor privilégio", "Cada pessoa acessa só o necessário. Isso limita o estrago de um clique errado."),
            ("Treine a equipe", "Simulações de phishing periódicas reduzem cliques de risco."),
        ],
        "pergunta": "O seu time sabe reconhecer um presente de grego digital?",
        "hashtags": ["#PHISHING", "#ENGENHARIASOCIAL", "#CIBERSEGURANÇA", "#TI", "#TECHDIM"],
    },
]


def main() -> int:
    saida = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "exemplos" / "infograficos"
    for p in PECAS:
        print(desenhar(p, saida / f"{p['slug']}.png"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
