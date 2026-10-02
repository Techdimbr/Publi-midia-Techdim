"""Biblioteca de cenas do infográfico.

Cada cena recebe (cor de destaque, gerador aleatório, bloco do post) e devolve
a imagem da área ilustrada. O gerador é semeado pelo post, então a mesma pauta
gera sempre a mesma arte.

  cena_composta  a cena única de cada post: fundo + até 4 elementos escolhidos
                 pelo Claude conforme o assunto
  cena_noticias, cena_ensino, cena_rede, cena_dev, cena_painel
                 cenas fixas por contexto
  historicas     ver cenas_historicas.py
"""
from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

import cenas_historicas
from desenho import SCENE, bebas, mix, mono, rob, wrap
from desenho import estrelas as _estrelas
from desenho import grad as _grad


def cena_dev(acc, rng, p=None):
    """Mesa de trabalho: monitor com código, notebook com sistema rodando e celular com app.
    Desenhado em 2x e reduzido, para bordas suaves; sombras e brilho de tela dão volume."""
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    S = 2
    W2, H2 = bw * S, bh * S
    img = _grad(W2, H2, (10, 16, 28), (20, 30, 44)).convert("RGBA")
    # escritório desfocado ao fundo (bokeh)
    bok = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bok)
    for _ in range(26):
        x, y, r = rng.randint(0, W2), rng.randint(0, 560), rng.randint(14, 46)
        bd.ellipse([x - r, y - r, x + r, y + r], fill=mix((60, 90, 140), acc, rng.random() * 0.5) + (rng.randint(28, 70),))
    img.alpha_composite(bok.filter(ImageFilter.GaussianBlur(14)))
    d = ImageDraw.Draw(img)
    mesa = 600
    for y in range(mesa, H2):
        d.line([(0, y), (W2, y)], fill=mix((44, 34, 30), (14, 12, 12), (y - mesa) / (H2 - mesa)) + (255,))
    d.line([(0, mesa), (W2, mesa)], fill=(90, 74, 64, 255), width=3)

    def sombra(box, raio=22, desloc=14, alfa=150):
        sh = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        x0, y0, x1, y1 = box
        ImageDraw.Draw(sh).rounded_rectangle([x0 + 6, y0 + desloc, x1 + 6, y1 + desloc], 10, fill=(0, 0, 0, alfa))
        img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(raio)))

    def brilho(box, cor, alfa=70, raio=40):
        g = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
        x0, y0, x1, y1 = box
        ImageDraw.Draw(g).rectangle([x0 - 30, y0 - 20, x1 + 30, y1 + 50], fill=cor + (alfa,))
        img.alpha_composite(g.filter(ImageFilter.GaussianBlur(raio)))

    # --- monitor com editor de código
    mx0, my0, mx1, my1 = 50, 90, 650, 520
    sombra((mx0, my0, mx1, my1))
    brilho((mx0, my0, mx1, my1), acc, 60)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([mx0, my0, mx1, my1], 14, fill=(26, 28, 34, 255), outline=(60, 64, 74, 255), width=3)
    sx0, sy0, sx1, sy1 = mx0 + 16, my0 + 16, mx1 - 16, my1 - 16
    d.rectangle([sx0, sy0, sx1, sy1], fill=(13, 17, 26, 255))
    d.rectangle([sx0, sy0, sx1, sy0 + 34], fill=(24, 30, 44, 255))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([sx0 + 14 + i * 24, sy0 + 10, sx0 + 28 + i * 24, sy0 + 24], fill=c + (255,))
    d.text((sx0 + 100, sy0 + 8), "app.ts  —  TECHDIM", font=mono(18), fill=(150, 160, 175, 255))
    d.rectangle([sx0, sy0 + 34, sx0 + 150, sy1], fill=(17, 22, 34, 255))
    for i, nome in enumerate(("src", "  api.ts", "  app.ts", "  ui.tsx", "tests", "deploy.yml")):
        d.text((sx0 + 14, sy0 + 50 + i * 30), nome, font=mono(17), fill=(120, 132, 150, 255))
    codigo = [
        ("const ", "app", " = criarSistema({"), ("  nome: ", '"Sob medida"', ","),
        ("  plataformas: ", '["web","desktop","ios","android"]', ","),
        ("  integra: ", '["ERP","CRM","API","planilhas"]', ","), ("});", "", ""),
        ("", "", ""), ("app.", "rodar", "();  // no ar"),
    ]
    cod = mono(19)
    y = sy0 + 56
    for i, (a, b, c) in enumerate(codigo):
        x = sx0 + 168
        d.text((x - 32, y), f"{i + 1:02d}", font=cod, fill=(70, 80, 98, 255))
        d.text((x, y), a, font=cod, fill=(200, 120, 255, 255) if a.startswith("const") else (170, 180, 195, 255))
        x += d.textlength(a, font=cod)
        d.text((x, y), b, font=cod, fill=acc + (255,) if b.startswith('"') or b.startswith("[") else (120, 200, 255, 255))
        x += d.textlength(b, font=cod)
        d.text((x, y), c, font=cod, fill=(150, 160, 175, 255))
        y += 32
    for i in range(7):  # blocos de código abaixo, só textura
        w = rng.randint(120, 330)
        d.rounded_rectangle([sx0 + 168, y + 12 + i * 20, sx0 + 168 + w, y + 20 + i * 20], 3,
                            fill=mix((40, 60, 90), acc, rng.random() * 0.4) + (255,))
    d.rectangle([mx0 + 280, my1, mx0 + 320, 574], fill=(40, 44, 52, 255))
    d.rounded_rectangle([mx0 + 190, 566, mx0 + 410, 586], 8, fill=(52, 56, 66, 255))

    # --- notebook com o sistema funcionando
    lx0, ly0, lx1, ly1 = 410, 390, 930, 740
    sombra((lx0, ly0, lx1, ly1 + 40), 26, 18, 190)
    brilho((lx0, ly0, lx1, ly1), (60, 200, 150), 60)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([lx0, ly0, lx1, ly1], 14, fill=(30, 32, 38, 255), outline=(70, 74, 84, 255), width=3)
    ex0, ey0, ex1, ey1 = lx0 + 14, ly0 + 14, lx1 - 14, ly1 - 14
    d.rectangle([ex0, ey0, ex1, ey1], fill=(244, 247, 251, 255))
    d.rectangle([ex0, ey0, ex1, ey0 + 44], fill=acc + (255,))
    d.text((ex0 + 18, ey0 + 11), "TECHDIM · Painel", font=rob(22, 700), fill=(255, 255, 255, 255))
    for i, (rot, val) in enumerate((("Pedidos", "128"), ("Hoje", "R$ 8,4 mil"), ("Prazo", "98%"))):
        cx = ex0 + 16 + i * 160
        d.rounded_rectangle([cx, ey0 + 60, cx + 148, ey0 + 128], 8, fill=(255, 255, 255, 255), outline=(214, 222, 232, 255), width=2)
        d.text((cx + 12, ey0 + 68), rot, font=rob(16, 400), fill=(110, 120, 135, 255))
        d.text((cx + 12, ey0 + 90), val, font=rob(26, 700), fill=(24, 32, 46, 255))
    gx0, gy0, gx1, gy1 = ex0 + 16, ey0 + 144, ex1 - 16, ey1 - 14
    d.rounded_rectangle([gx0, gy0, gx1, gy1], 8, fill=(255, 255, 255, 255), outline=(214, 222, 232, 255), width=2)
    barras = [34, 52, 44, 66, 58, 82, 74, 96]
    bwid = (gx1 - gx0 - 40) / len(barras)
    for i, v in enumerate(barras):
        bx = gx0 + 20 + i * bwid
        d.rectangle([bx + 6, gy1 - 14 - v * 1.25, bx + bwid - 6, gy1 - 14], fill=mix(acc, (255, 255, 255), 0.25 if i < 7 else 0) + (255,))
    pts = [(gx0 + 20 + i * bwid + bwid / 2, gy1 - 30 - v * 1.25) for i, v in enumerate(barras)]
    d.line(pts, fill=(24, 32, 46, 255), width=4)
    d.polygon([(lx0 - 34, ly1 + 6), (lx1 + 34, ly1 + 6), (lx1 + 60, ly1 + 44), (lx0 - 60, ly1 + 44)], fill=(150, 154, 164, 255))
    d.rounded_rectangle([lx0 + 190, ly1 + 8, lx1 - 190, ly1 + 18], 5, fill=(110, 114, 124, 255))

    # --- celular com o aplicativo
    px0, py0, px1, py1 = 60, 520, 240, 880
    sombra((px0, py0, px1, py1), 20, 16, 200)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([px0, py0, px1, py1], 30, fill=(18, 20, 24, 255), outline=(84, 88, 98, 255), width=3)
    d.rounded_rectangle([px0 + 10, py0 + 10, px1 - 10, py1 - 10], 24, fill=(244, 247, 251, 255))
    d.rounded_rectangle([px0 + 62, py0 + 16, px1 - 62, py0 + 26], 5, fill=(18, 20, 24, 255))
    d.rectangle([px0 + 10, py0 + 40, px1 - 10, py0 + 96], fill=acc + (255,))
    d.text((px0 + 24, py0 + 54), "Meu app", font=rob(24, 700), fill=(255, 255, 255, 255))
    for i in range(3):
        cy = py0 + 112 + i * 76
        d.rounded_rectangle([px0 + 22, cy, px1 - 22, cy + 62], 10, fill=(255, 255, 255, 255), outline=(214, 222, 232, 255), width=2)
        d.ellipse([px0 + 32, cy + 14, px0 + 66, cy + 48], fill=mix(acc, (255, 255, 255), 0.3 + 0.2 * i) + (255,))
        d.rounded_rectangle([px0 + 78, cy + 16, px1 - 40, cy + 26], 4, fill=(60, 70, 88, 255))
        d.rounded_rectangle([px0 + 78, cy + 36, px1 - 70, cy + 44], 4, fill=(190, 198, 210, 255))
    d.rounded_rectangle([px0 + 28, py1 - 92, px1 - 28, py1 - 48], 22, fill=acc + (255,))
    d.text(((px0 + px1) // 2, py1 - 70), "Novo pedido", font=rob(20, 700), fill=(255, 255, 255, 255), anchor="mm")

    out = img.convert("RGB").resize((bw, bh), Image.LANCZOS)
    od = ImageDraw.Draw(out)
    od.rectangle([0, bh - 34, bw, bh], fill=(8, 12, 20))
    od.text((14, bh - 26), "WEB  ·  DESKTOP  ·  CELULAR  ·  INTEGRAÇÕES", font=rob(15, 700), fill=(200, 215, 230))
    return out


class _Tela:
    """Tela em 2x com sombra e brilho, para cenas de ambiente."""

    def __init__(self, rng, acc, topo=(10, 16, 28), base=(20, 30, 44), mesa=None):
        self.bw, self.bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
        self.W, self.H = self.bw * 2, self.bh * 2
        self.acc, self.rng = acc, rng
        self.img = _grad(self.W, self.H, topo, base).convert("RGBA")
        bok = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bok)
        for _ in range(24):
            x, y, r = rng.randint(0, self.W), rng.randint(0, 560), rng.randint(14, 44)
            bd.ellipse([x - r, y - r, x + r, y + r], fill=mix((60, 90, 140), acc, rng.random() * 0.5) + (rng.randint(24, 60),))
        self.img.alpha_composite(bok.filter(ImageFilter.GaussianBlur(14)))
        self.mesa = mesa
        if mesa:
            d = ImageDraw.Draw(self.img)
            for y in range(mesa, self.H):
                d.line([(0, y), (self.W, y)], fill=mix((44, 34, 30), (14, 12, 12), (y - mesa) / (self.H - mesa)) + (255,))
            d.line([(0, mesa), (self.W, mesa)], fill=(90, 74, 64, 255), width=3)

    def sombra(self, box, raio=22, desloc=14, alfa=150):
        sh = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        x0, y0, x1, y1 = box
        ImageDraw.Draw(sh).rounded_rectangle([x0 + 6, y0 + desloc, x1 + 6, y1 + desloc], 10, fill=(0, 0, 0, alfa))
        self.img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(raio)))

    def brilho(self, box, cor, alfa=60, raio=40):
        g = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        x0, y0, x1, y1 = box
        ImageDraw.Draw(g).rectangle([x0 - 30, y0 - 20, x1 + 30, y1 + 50], fill=cor + (alfa,))
        self.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(raio)))

    def draw(self):
        return ImageDraw.Draw(self.img)

    def fim(self, legenda):
        out = self.img.convert("RGB").resize((self.bw, self.bh), Image.LANCZOS)
        od = ImageDraw.Draw(out)
        od.rectangle([0, self.bh - 34, self.bw, self.bh], fill=(8, 12, 20))
        od.text((14, self.bh - 26), legenda, font=rob(15, 700), fill=(200, 215, 230))
        return out


def _monitor(t, box, titulo=""):
    t.sombra(box)
    t.brilho(box, t.acc, 55)
    d = t.draw()
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, 14, fill=(26, 28, 34, 255), outline=(60, 64, 74, 255), width=3)
    tela = (x0 + 16, y0 + 16, x1 - 16, y1 - 16)
    d.rectangle(tela, fill=(13, 17, 26, 255))
    return tela


def cena_noticias(acc, rng, p=None):
    """Painel de notícias: manchetes, mapa de pontos e gráfico, mais um celular com alerta."""
    t = _Tela(rng, acc, mesa=600)
    mx0, my0, mx1, my1 = 40, 80, 700, 540
    sx0, sy0, sx1, sy1 = _monitor(t, (mx0, my0, mx1, my1))
    d = t.draw()
    d.rectangle([sx0, sy0, sx1, sy0 + 40], fill=acc + (255,))
    d.text((sx0 + 16, sy0 + 8), "TECH NEWS · AO VIVO", font=rob(22, 700), fill=(10, 14, 20, 255))
    # mapa de pontos
    mapa = [(x, y) for x in range(sx0 + 20, sx0 + 270, 12) for y in range(sy0 + 66, sy0 + 250, 12)
            if ((x - sx0 - 145) / 125) ** 2 + ((y - sy0 - 158) / 92) ** 2 < 1 and rng.random() > 0.28]
    for x, y in mapa:
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(60, 90, 130, 255))
    for x, y in rng.sample(mapa, 7):
        d.ellipse([x - 7, y - 7, x + 7, y + 7], outline=acc + (255,), width=3)
        d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=acc + (255,))
    # manchetes
    for i in range(3):
        y = sy0 + 64 + i * 66
        d.rounded_rectangle([sx0 + 300, y, sx1 - 16, y + 56], 8, fill=(22, 30, 46, 255))
        d.rectangle([sx0 + 300, y, sx0 + 308, y + 56], fill=acc + (255,))
        d.rounded_rectangle([sx0 + 322, y + 12, sx1 - 40 - rng.randint(0, 60), y + 24], 4, fill=(220, 228, 240, 255))
        d.rounded_rectangle([sx0 + 322, y + 34, sx1 - 120 - rng.randint(0, 80), y + 42], 4, fill=(110, 124, 146, 255))
    # gráfico
    gy = sy0 + 280
    d.rounded_rectangle([sx0 + 16, gy, sx1 - 16, sy1 - 14], 8, fill=(18, 24, 38, 255))
    pts, v = [], 80
    for i in range(24):
        v = max(20, min(110, v + rng.randint(-22, 24)))
        pts.append((sx0 + 36 + i * 24, sy1 - 30 - v))
    d.line(pts, fill=acc + (255,), width=4)
    d.rectangle([mx0 + 300, my1, mx0 + 340, 584], fill=(40, 44, 52, 255))
    d.rounded_rectangle([mx0 + 210, 576, mx0 + 430, 596], 8, fill=(52, 56, 66, 255))
    # celular com alerta
    px0, py0, px1, py1 = 740, 470, 920, 860
    t.sombra((px0, py0, px1, py1), 20, 16, 200)
    d = t.draw()
    d.rounded_rectangle([px0, py0, px1, py1], 30, fill=(18, 20, 24, 255), outline=(84, 88, 98, 255), width=3)
    d.rounded_rectangle([px0 + 10, py0 + 10, px1 - 10, py1 - 10], 24, fill=(14, 20, 34, 255))
    d.text(((px0 + px1) // 2, py0 + 60), "09:41", font=rob(40, 700), fill=(240, 244, 250, 255), anchor="mm")
    for i in range(3):
        y = py0 + 110 + i * 100
        d.rounded_rectangle([px0 + 22, y, px1 - 22, y + 86], 14, fill=(32, 42, 62, 255))
        d.ellipse([px0 + 34, y + 24, px0 + 72, y + 62], fill=acc + (255,))
        d.rounded_rectangle([px0 + 86, y + 22, px1 - 36, y + 34], 4, fill=(230, 236, 246, 255))
        d.rounded_rectangle([px0 + 86, y + 46, px1 - 60, y + 56], 4, fill=(130, 144, 168, 255))
    return t.fim("NOTÍCIA DO DIA  ·  TECNOLOGIA  ·  IA  ·  NEGÓCIOS")


def cena_ensino(acc, rng, p=None):
    """Quadro com passo a passo e diagrama, notebook com apresentação e caneca."""
    t = _Tela(rng, acc, topo=(18, 24, 36), base=(26, 36, 50), mesa=640)
    qx0, qy0, qx1, qy1 = 50, 70, 910, 560
    t.sombra((qx0, qy0, qx1, qy1), 24, 16, 170)
    d = t.draw()
    d.rounded_rectangle([qx0, qy0, qx1, qy1], 12, fill=(120, 124, 132, 255))
    d.rounded_rectangle([qx0 + 12, qy0 + 12, qx1 - 12, qy1 - 12], 8, fill=(22, 46, 40, 255))
    d.rectangle([qx0 + 40, qy1, qx1 - 40, qy1 + 16], fill=(100, 104, 112, 255))
    giz, giz2 = (236, 240, 232, 255), acc + (255,)
    d.text((qx0 + 40, qy0 + 36), "COMO FAZER", font=bebas(64), fill=giz2)
    d.line([(qx0 + 40, qy0 + 106), (qx0 + 340, qy0 + 108)], fill=giz2, width=4)
    for i, txt in enumerate(("Identifique", "Configure", "Teste e registre")):
        y = qy0 + 140 + i * 100
        d.ellipse([qx0 + 40, y, qx0 + 100, y + 60], outline=giz, width=4)
        d.text((qx0 + 70, y + 30), str(i + 1), font=bebas(44), fill=giz, anchor="mm")
        d.text((qx0 + 120, y + 8), txt, font=rob(40, 600), fill=giz)
        if i < 2:
            d.line([(qx0 + 70, y + 66), (qx0 + 70, y + 96)], fill=giz2, width=4)
    # diagrama
    cx, cy = qx0 + 640, qy0 + 230
    for dx, dy, r in ((-150, 70, 46), (150, 70, 46), (0, -90, 54)):
        d.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r], outline=giz, width=4)
    for a, b in (((cx - 110, cy + 40), (cx - 30, cy - 50)), ((cx + 110, cy + 40), (cx + 30, cy - 50)), ((cx - 104, cy + 70), (cx + 104, cy + 70))):
        d.line([a, b], fill=giz2, width=4)
    d.ellipse([cx - 22, cy - 112, cx + 22, cy - 68], fill=giz2)
    d.text((cx, cy + 200), "O QUE · POR QUÊ · COMO", font=rob(26, 700), fill=giz, anchor="mm")
    # notebook
    lx0, ly0, lx1, ly1 = 420, 640, 880, 880
    t.sombra((lx0, ly0, lx1, ly1 + 30), 22, 14, 190)
    d = t.draw()
    d.rounded_rectangle([lx0, ly0, lx1, ly1], 12, fill=(30, 32, 38, 255), outline=(70, 74, 84, 255), width=3)
    d.rectangle([lx0 + 12, ly0 + 12, lx1 - 12, ly1 - 12], fill=(244, 247, 251, 255))
    d.rectangle([lx0 + 12, ly0 + 12, lx1 - 12, ly0 + 48], fill=acc + (255,))
    d.text((lx0 + 28, ly0 + 18), "Aula · Passo 1 de 3", font=rob(20, 700), fill=(255, 255, 255, 255))
    for i in range(4):
        d.ellipse([lx0 + 32, ly0 + 74 + i * 38, lx0 + 46, ly0 + 88 + i * 38], fill=acc + (255,))
        d.rounded_rectangle([lx0 + 60, ly0 + 76 + i * 38, lx1 - 40 - i * 36, ly0 + 86 + i * 38], 4, fill=(60, 72, 92, 255))
    d.polygon([(lx0 - 30, ly1 + 6), (lx1 + 30, ly1 + 6), (lx1 + 54, ly1 + 38), (lx0 - 54, ly1 + 38)], fill=(150, 154, 164, 255))
    # caneca e livro
    d.rounded_rectangle([110, 700, 250, 790], 12, fill=(236, 238, 242, 255))
    d.rounded_rectangle([250, 716, 290, 760], 16, outline=(236, 238, 242, 255), width=8)
    d.rectangle([128, 720, 232, 740], fill=acc + (255,))
    d.rounded_rectangle([60, 800, 330, 840], 6, fill=mix(acc, (20, 30, 40), 0.35) + (255,))
    d.rectangle([60, 800, 330, 810], fill=(236, 238, 242, 255))
    return t.fim("PASSO A PASSO  ·  APRENDA  ·  APLIQUE")


def cena_rede(acc, rng, p=None):
    """Rack de servidores com LEDs, switch e diagrama de rede com cadeado."""
    t = _Tela(rng, acc, topo=(8, 12, 22), base=(16, 22, 34))
    rx0, ry0, rx1, ry1 = 60, 50, 430, 870
    t.sombra((rx0, ry0, rx1, ry1), 26, 16, 190)
    t.brilho((rx0, ry0, rx1, ry1), acc, 40)
    d = t.draw()
    d.rounded_rectangle([rx0, ry0, rx1, ry1], 12, fill=(28, 30, 36, 255), outline=(70, 74, 84, 255), width=4)
    for i in range(12):
        y = ry0 + 24 + i * 66
        d.rounded_rectangle([rx0 + 20, y, rx1 - 20, y + 54], 6, fill=(40, 44, 54, 255), outline=(66, 70, 82, 255), width=2)
        for k in range(8):
            d.rectangle([rx0 + 40 + k * 14, y + 14, rx0 + 48 + k * 14, y + 40], fill=(24, 26, 32, 255))
        for k in range(4):
            cor = (60, 230, 140) if rng.random() > 0.2 else (255, 190, 60)
            d.ellipse([rx1 - 120 + k * 22, y + 20, rx1 - 106 + k * 22, y + 34], fill=cor + (255,))
    # diagrama de rede
    cx, cy = 690, 330
    nos = [(cx - 190, cy - 170), (cx + 190, cy - 170), (cx - 210, cy + 170), (cx + 210, cy + 170), (cx, cy + 300)]
    for x, y in nos:
        d.line([(cx, cy), (x, y)], fill=acc + (255,), width=5)
    for x, y in nos:
        d.rounded_rectangle([x - 52, y - 38, x + 52, y + 38], 10, fill=(20, 28, 44, 255), outline=acc + (255,), width=3)
        d.rectangle([x - 30, y - 16, x + 30, y + 10], outline=(210, 224, 240, 255), width=3)
        d.line([(x - 14, y + 20), (x + 14, y + 20)], fill=(210, 224, 240, 255), width=3)
    d.ellipse([cx - 96, cy - 96, cx + 96, cy + 96], fill=(14, 22, 38, 255), outline=acc + (255,), width=5)
    d.polygon([(cx, cy - 66), (cx + 52, cy - 40), (cx + 52, cy + 14), (cx, cy + 66), (cx - 52, cy + 14), (cx - 52, cy - 40)], outline=acc + (255,), fill=(20, 40, 60, 255))
    d.rounded_rectangle([cx - 20, cy - 4, cx + 20, cy + 30], 5, fill=acc + (255,))
    d.arc([cx - 14, cy - 28, cx + 14, cy + 6], 180, 360, fill=acc + (255,), width=6)
    return t.fim("INFRAESTRUTURA  ·  REDE  ·  SEGURANÇA  ·  BACKUP")




def cena_painel(acc, rng, p=None):
    """Terminal com linhas do post: p["terminal"] = [[prefixo, texto, cor]], cor em
    ok|risco|cmd|txt. Estilo de relatório técnico, para o tema hacker/IA."""
    p = p or {}
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = Image.new("RGB", (bw, bh), (8, 10, 16))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, 34], fill=(24, 30, 42))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=c)
    d.text((100, 8), p.get("terminal_titulo", "relatório"), font=rob(16, 400), fill=(150, 160, 175))
    cores = {"ok": (90, 230, 150), "risco": (255, 120, 110), "cmd": (120, 200, 255), "txt": (230, 235, 245)}
    fonte = rob(19, 400)
    y = 56
    for pre, txt, cor in p.get("terminal", []):
        if y > bh - 50:  # sem espaço: o que sobrar fica de fora, não passa da moldura
            break
        x = 18
        if pre:
            d.text((x, y), pre, font=fonte, fill=acc)
            x += d.textlength(pre, font=fonte)
        for ln in wrap(d, txt, fonte, bw - x - 18):
            d.text((x, y), ln, font=fonte, fill=cores.get(cor, cores["txt"]))
            y += 28
        y += 4
    d.rectangle([18, y + 2, 32, y + 24], fill=acc)
    return img


# ------------------------------------------------------------ cena composta
# O Claude (Routine) descreve a cena do post: fundo + até 4 elementos + legenda.
# Cada combinação gera uma imagem diferente, sempre ligada ao assunto.


def _el_notebook(t, cx, by, s, tela="grafico"):
    d = t.draw(); acc = t.acc
    w, h = int(330 * s), int(210 * s)
    x0, y0 = cx - w // 2, by - h - int(26 * s)
    t.sombra((x0, y0, x0 + w, by), 20, 12, 180)
    d = t.draw()
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 10, fill=(30, 32, 38, 255), outline=(70, 74, 84, 255), width=3)
    d.rectangle([x0 + 10, y0 + 10, x0 + w - 10, y0 + h - 10], fill=(244, 247, 251, 255))
    d.rectangle([x0 + 10, y0 + 10, x0 + w - 10, y0 + 10 + int(30 * s)], fill=acc + (255,))
    for i, v in enumerate((30, 52, 44, 70, 62, 86)):
        bx = x0 + 28 + i * int(46 * s)
        d.rectangle([bx, y0 + h - 22 - int(v * s * 1.2), bx + int(30 * s), y0 + h - 22], fill=mix(acc, (255, 255, 255), 0.2) + (255,))
    d.polygon([(x0 - int(30 * s), by - int(24 * s)), (x0 + w + int(30 * s), by - int(24 * s)), (x0 + w + int(50 * s), by), (x0 - int(50 * s), by)], fill=(150, 154, 164, 255))


def _el_monitor(t, cx, by, s, tela="codigo"):
    d = t.draw(); acc = t.acc
    w, h = int(400 * s), int(270 * s)
    x0, y0 = cx - w // 2, by - h - int(50 * s)
    t.sombra((x0, y0, x0 + w, y0 + h)); t.brilho((x0, y0, x0 + w, y0 + h), acc, 50)
    d = t.draw()
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], 12, fill=(26, 28, 34, 255), outline=(60, 64, 74, 255), width=3)
    d.rectangle([x0 + 12, y0 + 12, x0 + w - 12, y0 + h - 12], fill=(13, 17, 26, 255))
    for i in range(9):
        wd = t.rng.randint(60, int(w * 0.7))
        d.rounded_rectangle([x0 + 30, y0 + 28 + i * int(24 * s), x0 + 30 + wd, y0 + 36 + i * int(24 * s)], 3,
                            fill=mix((50, 80, 130), acc, (i % 3) / 3) + (255,))
    d.rectangle([cx - 18, y0 + h, cx + 18, by - 14], fill=(40, 44, 52, 255))
    d.rounded_rectangle([cx - int(70 * s), by - 16, cx + int(70 * s), by], 6, fill=(52, 56, 66, 255))


def _el_celular(t, cx, by, s, tela=""):
    d = t.draw(); acc = t.acc
    w, h = int(120 * s), int(240 * s)
    x0, y0 = cx - w // 2, by - h
    t.sombra((x0, y0, x0 + w, by), 14, 10, 200)
    d = t.draw()
    d.rounded_rectangle([x0, y0, x0 + w, by], 22, fill=(18, 20, 24, 255), outline=(84, 88, 98, 255), width=3)
    d.rounded_rectangle([x0 + 8, y0 + 8, x0 + w - 8, by - 8], 16, fill=(244, 247, 251, 255))
    d.rectangle([x0 + 8, y0 + 30, x0 + w - 8, y0 + 30 + int(36 * s)], fill=acc + (255,))
    for i in range(3):
        yy = y0 + 30 + int(36 * s) + 14 + i * int(48 * s)
        d.rounded_rectangle([x0 + 16, yy, x0 + w - 16, yy + int(38 * s)], 8, fill=(255, 255, 255, 255), outline=(214, 222, 232, 255), width=2)
        d.ellipse([x0 + 22, yy + 8, x0 + 22 + int(22 * s), yy + 8 + int(22 * s)], fill=mix(acc, (255, 255, 255), 0.3) + (255,))


def _el_rack(t, cx, by, s, tela=""):
    w, h = int(200 * s), int(330 * s)
    x0, y0 = cx - w // 2, by - h
    t.sombra((x0, y0, x0 + w, by), 20, 12, 190)
    d = t.draw()
    d.rounded_rectangle([x0, y0, x0 + w, by], 8, fill=(28, 30, 36, 255), outline=(70, 74, 84, 255), width=3)
    for i in range(6):
        y = y0 + 14 + i * int(52 * s)
        d.rounded_rectangle([x0 + 12, y, x0 + w - 12, y + int(42 * s)], 5, fill=(40, 44, 54, 255), outline=(66, 70, 82, 255), width=2)
        for k in range(3):
            c = (60, 230, 140) if t.rng.random() > 0.2 else (255, 190, 60)
            d.ellipse([x0 + w - 70 + k * 16, y + int(16 * s), x0 + w - 60 + k * 16, y + int(26 * s)], fill=c + (255,))


def _el_nuvem(t, cx, by, s, tela=""):
    acc = t.acc
    cy = by - int(150 * s)
    g = Image.new("RGBA", (t.W, t.H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    gd.ellipse([cx - 150 * s, cy - 60 * s, cx + 150 * s, cy + 60 * s], fill=acc + (90,))
    t.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
    d = t.draw()
    col = (226, 236, 248, 255)
    for dx, dy, r in ((-80, 10, 50), (-20, -20, 66), (50, 0, 56), (110, 20, 40)):
        d.ellipse([cx + (dx - r) * s, cy + (dy - r) * s, cx + (dx + r) * s, cy + (dy + r) * s], fill=col)
    d.rounded_rectangle([cx - 130 * s, cy + 6 * s, cx + 150 * s, cy + 60 * s], 20, fill=col)
    d.polygon([(cx - 14, cy - 10), (cx + 14, cy - 10), (cx, cy - 36)], fill=acc + (255,))
    d.rectangle([cx - 5, cy - 10, cx + 5, cy + 36], fill=acc + (255,))


def _el_escudo(t, cx, by, s, tela=""):
    d = t.draw(); acc = t.acc
    cy = by - int(170 * s)
    g = Image.new("RGBA", (t.W, t.H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([cx - 180 * s, cy - 180 * s, cx + 180 * s, cy + 180 * s], fill=acc + (90,))
    t.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(36)))
    d = t.draw()
    pts = [(cx - 110 * s, cy - 120 * s), (cx + 110 * s, cy - 120 * s), (cx + 110 * s, cy + 10 * s), (cx, cy + 140 * s), (cx - 110 * s, cy + 10 * s)]
    d.polygon(pts, fill=(14, 30, 58, 255)); d.line(pts + [pts[0]], fill=acc + (255,), width=6)
    d.rounded_rectangle([cx - 30 * s, cy - 6 * s, cx + 30 * s, cy + 46 * s], 7, fill=acc + (255,))
    d.arc([cx - 22 * s, cy - 42 * s, cx + 22 * s, cy + 6 * s], 180, 360, fill=acc + (255,), width=8)


def _el_globo(t, cx, by, s, tela=""):
    d = t.draw(); acc = t.acc
    r = int(120 * s); cy = by - r - int(30 * s)
    g = Image.new("RGBA", (t.W, t.H), (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse([cx - r - 30, cy - r - 30, cx + r + 30, cy + r + 30], fill=acc + (80,))
    t.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(30)))
    d = t.draw()
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(14, 28, 52, 255), outline=acc + (255,), width=4)
    for k in (0.35, 0.7):
        d.ellipse([cx - r * k, cy - r, cx + r * k, cy + r], outline=acc + (160,), width=2)
        d.ellipse([cx - r, cy - r * k, cx + r, cy + r * k], outline=acc + (160,), width=2)
    for _ in range(9):
        x, y = t.rng.randint(-70, 70) * s, t.rng.randint(-70, 70) * s
        d.ellipse([cx + x - 6, cy + y - 6, cx + x + 6, cy + y + 6], fill=acc + (255,))


def _el_engrenagens(t, cx, by, s, tela=""):
    d = t.draw(); acc = t.acc
    def eng(x, y, r, n, cor):
        pts = []
        for i in range(n * 2):
            a = math.pi * i / n
            rr = r if i % 2 == 0 else r * 0.82
            pts += [(x + rr * math.cos(a), y + rr * math.sin(a)), (x + rr * math.cos(a + math.pi / (2 * n)), y + rr * math.sin(a + math.pi / (2 * n)))]
        d.polygon(pts, fill=cor); d.ellipse([x - r * 0.35, y - r * 0.35, x + r * 0.35, y + r * 0.35], fill=(12, 16, 24, 255))
    eng(cx - 50 * s, by - 150 * s, 90 * s, 10, acc + (255,))
    eng(cx + 74 * s, by - 90 * s, 62 * s, 8, mix(acc, (255, 255, 255), 0.4) + (255,))
    eng(cx + 10 * s, by - 250 * s, 44 * s, 6, mix(acc, (30, 40, 60), 0.3) + (255,))


def _el_grafico(t, cx, by, s, tela=""):
    d = t.draw(); acc = t.acc
    w, h = int(300 * s), int(200 * s)
    x0, y0 = cx - w // 2, by - h
    d.rounded_rectangle([x0, y0, x0 + w, by], 10, fill=(18, 24, 38, 255), outline=mix(acc, (30, 40, 60), 0.5) + (255,), width=2)
    vals = [30, 48, 40, 66, 58, 88, 80, 110]
    bw = (w - 30) / len(vals)
    for i, v in enumerate(vals):
        d.rectangle([x0 + 15 + i * bw + 4, by - 14 - v * s * 1.2, x0 + 15 + (i + 1) * bw - 4, by - 14], fill=mix(acc, (255, 255, 255), 0.15) + (255,))
    d.line([(x0 + 15 + i * bw + bw / 2, by - 24 - v * s * 1.2) for i, v in enumerate(vals)], fill=(240, 244, 250, 255), width=4)


def _el_documento(t, cx, by, s, tela=""):
    d = t.draw(); acc = t.acc
    w, h = int(190 * s), int(250 * s)
    x0, y0 = cx - w // 2, by - h
    t.sombra((x0, y0, x0 + w, by), 14, 10, 160)
    d = t.draw()
    d.rounded_rectangle([x0, y0, x0 + w, by], 8, fill=(244, 247, 251, 255))
    d.rectangle([x0, y0, x0 + w, y0 + int(34 * s)], fill=acc + (255,))
    for i in range(6):
        d.rounded_rectangle([x0 + 18, y0 + int(54 * s) + i * int(26 * s), x0 + w - 18 - (i % 3) * 22, y0 + int(62 * s) + i * int(26 * s)], 3, fill=(120, 134, 156, 255))
    d.ellipse([x0 + w - 70, by - 70, x0 + w - 20, by - 20], outline=acc + (255,), width=5)
    d.line([(x0 + w - 58, by - 46), (x0 + w - 48, by - 36), (x0 + w - 32, by - 56)], fill=acc + (255,), width=5)


def _el_chip(t, cx, by, s, tela=""):
    d = t.draw(); acc = t.acc
    r = int(80 * s); cy = by - r - int(40 * s)
    g = Image.new("RGBA", (t.W, t.H), (0, 0, 0, 0))
    ImageDraw.Draw(g).rectangle([cx - r - 40, cy - r - 40, cx + r + 40, cy + r + 40], fill=acc + (90,))
    t.img.alpha_composite(g.filter(ImageFilter.GaussianBlur(32)))
    d = t.draw()
    for i in range(6):
        p = -r + 20 + i * (2 * r - 40) / 5
        for (a, b, c2, e) in ((cx + p, cy - r - 24, cx + p, cy - r), (cx + p, cy + r, cx + p, cy + r + 24), (cx - r - 24, cy + p, cx - r, cy + p), (cx + r, cy + p, cx + r + 24, cy + p)):
            d.line([(a, b), (c2, e)], fill=(200, 210, 224, 255), width=6)
    d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], 12, fill=(20, 26, 40, 255), outline=acc + (255,), width=5)
    d.text((cx, cy), "IA", font=bebas(int(90 * s)), fill=acc + (255,), anchor="mm")


ELEMENTOS = {"notebook": _el_notebook, "monitor": _el_monitor, "celular": _el_celular, "rack": _el_rack,
             "nuvem": _el_nuvem, "escudo": _el_escudo, "globo": _el_globo, "engrenagens": _el_engrenagens,
             "grafico": _el_grafico, "documento": _el_documento, "chip": _el_chip}
FUNDOS = {"escritorio": ((10, 16, 28), (20, 30, 44), 640), "datacenter": ((6, 10, 20), (12, 20, 34), None),
          "espaco": ((4, 6, 14), (14, 18, 34), None), "cidade": ((18, 24, 44), (36, 40, 70), 660),
          "laboratorio": ((12, 22, 26), (22, 38, 44), 640)}


def cena_composta(acc, rng, p=None):
    """p["cena_composta"] = {"fundo": ..., "elementos": [...até 4...], "legenda": "..."}."""
    c = (p or {}).get("cena_composta", {})
    topo, base, mesa = FUNDOS.get(c.get("fundo", "escritorio"), FUNDOS["escritorio"])
    t = _Tela(rng, acc, topo=topo, base=base, mesa=mesa)
    if c.get("fundo") == "espaco":
        d = t.draw()
        _estrelas(d, t.W, t.H, 160, rng)
    if c.get("fundo") == "cidade":
        d = t.draw()
        for i in range(14):
            x = i * 70 + rng.randint(0, 20); h = rng.randint(180, 420)
            d.rectangle([x, 660 - h, x + 56, 660], fill=mix((20, 26, 48), acc, 0.08) + (255,))
            for yy in range(660 - h + 16, 640, 30):
                if rng.random() > 0.45:
                    d.rectangle([x + 10, yy, x + 18, yy + 12], fill=(255, 210, 120, 255))
    els = [e for e in c.get("elementos", []) if e in ELEMENTOS][:4] or ["notebook", "celular"]
    n = len(els)
    by = 810 if mesa else 840
    slots = {1: [480], 2: [320, 660], 3: [200, 480, 760], 4: [150, 370, 590, 810]}[n]
    escala = {1: 1.9, 2: 1.5, 3: 1.2, 4: 1.0}[n]
    ordem = sorted(range(n), key=lambda i: -abs(slots[i] - 480))  # centro por último, na frente
    for i in ordem:
        ELEMENTOS[els[i]](t, slots[i], by, escala)
    return t.fim(c.get("legenda", "TECHDIM")[:60].upper())



CENAS = {
    "composta": cena_composta, "noticias": cena_noticias, "ensino": cena_ensino,
    "rede": cena_rede, "painel": cena_painel, "dev": cena_dev,
    "titanic": cenas_historicas.cena_titanic, "maginot": cenas_historicas.cena_maginot,
    "vasa": cenas_historicas.cena_vasa, "apollo": cenas_historicas.cena_apollo,
    "troia": cenas_historicas.cena_troia,
}
