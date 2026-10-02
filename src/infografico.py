"""Infográfico de 1080×1350: título em duas cores, texto curto, "3 lições
táticas", pergunta final com chamada para conversar e uma cena ilustrada.

É o padrão visual dos posts diários (LinkedIn, Facebook e Instagram). O texto
vem do bloco "infografico" da pauta; a cena é desenhada por código (cenas.py),
sem banco de imagem e sem direito autoral de terceiros. Fontes: Bebas Neue e
Roboto Condensed (OFL), em fonts/.

  validar(bloco, tema)   confere e normaliza o bloco; levanta InfograficoInvalido
  renderizar(...)        valida e desenha — é o que o pipeline chama
  desenhar(p, caminho)   desenho de baixo nível, sobre um bloco já normalizado
"""
from __future__ import annotations

import pathlib
import random
import re

from PIL import Image, ImageDraw, ImageFilter

import config
from cenas import CENAS, ELEMENTOS, FUNDOS
from desenho import (
    BG,
    FG,
    MUTED,
    ROOT,
    SCENE,
    H,
    W,
    bebas,
    hexrgb,
    limitar_linhas,
    mix,
    rob,
    wrap,
)
from texto import cortar

CENA_PADRAO = {"noticias": "noticias", "destaque": "noticias", "hacker": "painel",
               "dica": "ensino", "servico": "dev", "especial": "dev"}
COR_PADRAO = {"noticias": "#4DA3FF", "destaque": "#FF8A00", "hacker": "#FF3B30",
              "dica": "#FFB000", "servico": "#2EE59D", "especial": "#2EE59D"}

CORES_TERMINAL = ("cmd", "ok", "risco", "txt")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class InfograficoInvalido(ValueError):
    """O bloco "infografico" da pauta não serve; quem chama usa a arte antiga."""


# ---------------------------------------------------------------- validação


def _hashtags(valor: object) -> list[str]:
    tags: list[str] = []
    for h in valor if isinstance(valor, list) else []:
        if not isinstance(h, str):
            continue
        h = "#" + re.sub(r"[^\w]", "", h.lstrip("#"))
        if len(h) > 1 and h.lower() not in [t.lower() for t in tags]:
            tags.append(h[:30])
    return tags[:6] or ["#TI", "#TECHDIM"]


def _terminal(valor: object) -> list[list[str]]:
    linhas: list[list[str]] = []
    for item in valor if isinstance(valor, (list, tuple)) else []:
        if not isinstance(item, (list, tuple)) or len(item) < 2:
            continue
        pre, txt = item[0], item[1]
        cor = item[2] if len(item) > 2 else "txt"
        if not isinstance(txt, str) or not txt.strip():
            continue
        linhas.append([pre if isinstance(pre, str) else "", cortar(txt, 70),
                       cor if cor in CORES_TERMINAL else "txt"])
    return linhas[:8]


def _composta(valor: object) -> dict | None:
    if not isinstance(valor, dict):
        return None
    elementos: list[str] = []
    for e in valor.get("elementos") if isinstance(valor.get("elementos"), list) else []:
        if e in ELEMENTOS and e not in elementos:
            elementos.append(e)
    if not elementos:
        return None
    fundo = valor.get("fundo")
    return {
        "fundo": fundo if fundo in FUNDOS else "escritorio",
        "elementos": elementos[:4],
        "legenda": cortar(valor.get("legenda"), 60) or "TECHDIM",
    }


def validar(bloco: object, tema: str) -> dict | None:
    """Bloco "infografico" normalizado, pronto para desenhar.

    Devolve None quando o post não tem bloco (usa a arte antiga) e levanta
    InfograficoInvalido quando o bloco existe mas não dá para desenhar.
    Textos longos são cortados com reticências em vez de estourar a arte.
    """
    if bloco is None:
        return None
    if not isinstance(bloco, dict):
        raise InfograficoInvalido("o bloco infografico precisa ser um objeto")

    branco = cortar(bloco.get("titulo_branco"), 80)
    destaque = cortar(bloco.get("titulo_destaque"), 60)
    if not (branco or destaque):
        raise InfograficoInvalido("faltam titulo_branco/titulo_destaque")

    licoes = []
    for item in bloco.get("licoes") if isinstance(bloco.get("licoes"), list) else []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            tit, txt = cortar(item[0], 28), cortar(item[1], 140)
            if tit and txt:
                licoes.append([tit, txt])
    if not licoes:
        raise InfograficoInvalido("faltam as licoes (pares [título, texto])")

    cor = bloco.get("cor")
    if not (isinstance(cor, str) and _HEX.match(cor)):
        cor = COR_PADRAO.get(tema, "#4DA3FF")

    p = {
        "titulo_branco": branco,
        "titulo_destaque": destaque,
        "historia": cortar(bloco.get("historia"), 300),
        "licoes": licoes[:3],
        "pergunta": cortar(bloco.get("pergunta"), 100)
        or "Quer conversar sobre a TI da sua empresa?",
        "hashtags": _hashtags(bloco.get("hashtags")),
        "cor": cor,
    }

    composta = _composta(bloco.get("cena_composta"))
    cena = bloco.get("cena")
    terminal = _terminal(bloco.get("terminal"))
    if composta:
        p["cena"], p["cena_composta"] = "composta", composta
    else:
        if cena not in CENAS or cena == "composta":
            cena = CENA_PADRAO.get(tema, "noticias")
        if cena == "painel" and not terminal:
            cena = "noticias"
        p["cena"] = cena
    if terminal:
        p["terminal"] = terminal
        p["terminal_titulo"] = cortar(bloco.get("terminal_titulo"), 50) or "relatório"
    # fundo de foto e crédito: só nos exemplos, nunca vêm da pauta
    return p


# ---------------------------------------------------------------- desenho


def _pintar_fundo(img: Image.Image, acc: tuple[int, int, int]) -> None:
    d = ImageDraw.Draw(img)
    for x in range(0, W, 54):
        d.line([(x, 0), (x, H)], fill=(14, 18, 26))
    for y in range(0, H, 54):
        d.line([(0, y), (W, y)], fill=(14, 18, 26))
    brilho = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(brilho).ellipse([520, 40, 1160, 700], fill=acc + (46,))
    brilho = brilho.filter(ImageFilter.GaussianBlur(70))
    img.paste(brilho, (0, 0), brilho)


def _pintar_cena(img: Image.Image, p: dict, acc, rng) -> None:
    x0, y0, x1, y1 = SCENE
    cena = CENAS[p["cena"]](acc, rng, p).convert("RGB")
    mascara = Image.new("L", cena.size, 0)
    ImageDraw.Draw(mascara).rounded_rectangle([0, 0, cena.size[0], cena.size[1]], 26, fill=255)
    img.paste(cena, (x0, y0), mascara)
    ImageDraw.Draw(img).rounded_rectangle([x0, y0, x1, y1], 26, outline=mix(acc, BG, 0.45), width=2)


def _pintar_foto(img: Image.Image, p: dict, acc) -> None:
    """Foto de fundo inteira, escurecida e sem moldura (usada nos exemplos)."""
    foto = Image.open(ROOT / "fotos" / p["fundo"]).convert("RGB")
    k = max(W / foto.width, 700 / foto.height)
    foto = foto.resize((int(foto.width * k) + 1, int(foto.height * k) + 1)).crop((0, 0, W, 700))
    foto = Image.blend(foto.convert("L").convert("RGB"), Image.new("RGB", (W, 700), acc), 0.35)
    fade = Image.new("L", (W, 700))
    fd = ImageDraw.Draw(fade)
    for yy in range(700):
        fd.line([(0, yy), (W, yy)], fill=int(255 * (0.55 + 0.45 * min(1, yy / 700) ** 1.6)))
    fundo = Image.new("RGB", (W, 700), BG)
    img.paste(fundo, (0, 0))
    img.paste(Image.composite(fundo, foto, fade), (0, 0))
    ImageDraw.Draw(img).text((1040, 664), p.get("credito", ""), font=rob(15, 400), fill=MUTED, anchor="ra")


def _titulo(d: ImageDraw.ImageDraw, p: dict, acc) -> int:
    """Título em duas cores; devolve o y logo abaixo dele."""
    x, larg, y = 68, 470, 146
    d.rectangle([40, 150, 48, 470], fill=acc)
    branco = " ".join(p["titulo_branco"].split())
    destaque = " ".join(p["titulo_destaque"].split())
    tam, limite = 104, 330
    while True:
        f = bebas(tam)
        linhas_b, linhas_d = wrap(d, branco, f, larg), wrap(d, destaque, f, larg)
        passo = int(tam * 0.98)
        if (len(linhas_b) + len(linhas_d)) * passo <= limite or tam <= 60:
            break
        tam -= 4
    # no menor corpo ainda pode não caber: corta as linhas, nunca invade a história
    maximo = max(1, limite // passo)
    if len(linhas_b) + len(linhas_d) > maximo:
        linhas_d = limitar_linhas(d, linhas_d, f, larg, max(1, maximo - len(linhas_b))) if linhas_d else []
        linhas_b = limitar_linhas(d, linhas_b, f, larg, max(1, maximo - len(linhas_d)))
    for ln in linhas_b:
        d.text((x, y), ln, font=f, fill=FG)
        y += passo
    for ln in linhas_d:
        d.text((x, y), ln, font=f, fill=acc)
        y += passo
    return y


def _historia(d: ImageDraw.ImageDraw, p: dict, y: int) -> None:
    corpo = rob(25, 400)
    y = max(y + 16, 500)
    for ln in limitar_linhas(d, wrap(d, p["historia"], corpo, 468), corpo, 468, 5):
        d.text((68, y), ln, font=corpo, fill=(206, 212, 220))
        y += 31


def _licoes(d: ImageDraw.ImageDraw, p: dict, acc) -> None:
    yb, colw = 690, 330
    d.line([(40, yb + 22), (330, yb + 22)], fill=mix(acc, BG, 0.55), width=2)
    d.line([(750, yb + 22), (1040, yb + 22)], fill=mix(acc, BG, 0.55), width=2)
    d.text((360, yb - 8), "3", font=bebas(60), fill=acc)
    d.text((388, yb), "LIÇÕES TÁTICAS", font=bebas(46), fill=FG)
    ft, ftx = rob(23, 800), rob(21, 400)
    for i, (tit, txt) in enumerate(p["licoes"]):
        cx = 40 + i * (colw + 5)
        if i:
            d.line([(cx - 4, yb + 70), (cx - 4, yb + 330)], fill=(40, 48, 60), width=2)
        d.ellipse([cx + 4, yb + 70, cx + 74, yb + 140], outline=acc, width=3)
        d.text((cx + 39, yb + 105), str(i + 1), font=bebas(46), fill=acc, anchor="mm")
        yy = yb + 70
        for ln in limitar_linhas(d, wrap(d, tit.upper(), ft, colw - 100), ft, colw - 100, 2):
            d.text((cx + 90, yy), ln, font=ft, fill=FG)
            yy += 27
        yy = max(yy + 4, yb + 158)
        for ln in limitar_linhas(d, wrap(d, txt, ftx, colw - 16), ftx, colw - 16, 7):
            d.text((cx + 6, yy), ln, font=ftx, fill=(190, 198, 208))
            yy += 26


def _chamada(d: ImageDraw.ImageDraw, p: dict, acc) -> None:
    yc = 1060
    d.rounded_rectangle([40, yc, 1040, yc + 112], 12, outline=mix(acc, BG, 0.35), width=2, fill=(14, 18, 26))
    d.rounded_rectangle([780, yc, 1040, yc + 112], 12, fill=acc)
    d.rectangle([780, yc, 800, yc + 112], fill=acc)
    pf = rob(27, 800)
    yy = yc + 16
    for ln in limitar_linhas(d, wrap(d, p["pergunta"].upper(), pf, 700), pf, 700, 2):
        d.text((70, yy), ln, font=pf, fill=FG)
        yy += 33
    d.text((910, yc + 40), "VAMOS", font=bebas(48), fill=(10, 13, 19), anchor="mm")
    d.text((910, yc + 80), "CONVERSAR?", font=bebas(48), fill=(10, 13, 19), anchor="mm")


def _rodape(d: ImageDraw.ImageDraw, p: dict, acc) -> None:
    fonte = rob(19, 700)
    tags = list(p["hashtags"])
    while len(tags) > 1 and d.textlength(" ".join(tags).upper(), font=fonte) > 1000:
        tags.pop()  # hashtag que não cabe na linha sai, em vez de passar da borda
    d.text((40, 1244), " ".join(tags).upper(), font=fonte, fill=mix(acc, FG, 0.25))
    d.line([(40, 1282), (1040, 1282)], fill=(34, 42, 54), width=2)
    d.text((40, 1296), "TECHDIM", font=bebas(40), fill=acc)
    d.text((1040, 1306), config.SITE, font=rob(24, 600), fill=MUTED, anchor="ra")


def desenhar(p: dict, caminho: pathlib.Path) -> pathlib.Path:
    """Desenha o infográfico de um bloco já normalizado e grava o PNG."""
    acc = hexrgb(p["cor"])
    rng = random.Random(p.get("slug", "infografico"))
    img = Image.new("RGB", (W, H), BG)
    _pintar_fundo(img, acc)
    if p.get("fundo"):
        _pintar_foto(img, p, acc)
    else:
        _pintar_cena(img, p, acc, rng)
    d = ImageDraw.Draw(img)
    y = _titulo(d, p, acc)
    _historia(d, p, y)
    _licoes(d, p, acc)
    _chamada(d, p, acc)
    _rodape(d, p, acc)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    img.save(caminho, "PNG", optimize=True)
    return caminho


def renderizar(bloco: object, tema: str, slug: str, caminho: pathlib.Path) -> pathlib.Path | None:
    """Valida o bloco da pauta e desenha. None quando o post não tem bloco."""
    p = validar(bloco, tema)
    if p is None:
        return None
    return desenhar({**p, "slug": slug}, caminho)
