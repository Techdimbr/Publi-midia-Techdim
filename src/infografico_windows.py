"""Cinco variações de padrão visual para o mesmo tema (Hardening do Windows)."""
from __future__ import annotations

import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter

import infografico as ig
from infografico import SCENE, ROOT, bebas, rob, hexrgb, mix

CRED = "Foto: BalticServers, CC BY-SA 3.0, Wikimedia Commons"


def cena_escudo(acc, rng):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = ig._grad(bw, bh, (8, 16, 34), (12, 40, 80))
    d = ImageDraw.Draw(img)
    for x in range(0, bw, 32):
        d.line([(x, 0), (x, bh)], fill=(16, 34, 64))
    for y in range(0, bh, 32):
        d.line([(0, y), (bw, y)], fill=(16, 34, 64))
    cx, cy = bw // 2, bh // 2 - 10
    glow = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([cx - 190, cy - 190, cx + 190, cy + 190], fill=acc + (110,))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img.paste(glow, (0, 0), glow)
    d = ImageDraw.Draw(img)
    sh = [(cx - 120, cy - 130), (cx + 120, cy - 130), (cx + 120, cy + 10), (cx, cy + 150), (cx - 120, cy + 10)]
    d.polygon(sh, fill=(14, 30, 58), outline=acc)
    d.line(sh + [sh[0]], fill=acc, width=5)
    # logotipo em quatro painéis
    for dx, dy in ((-52, -78), (6, -78), (-52, -20), (6, -20)):
        d.rectangle([cx + dx, cy + dy, cx + dx + 46, cy + dy + 50], fill=(230, 240, 255))
    d.rounded_rectangle([cx - 26, cy + 46, cx + 26, cy + 92], 6, fill=acc)
    d.arc([cx - 18, cy + 18, cx + 18, cy + 62], 180, 360, fill=acc, width=6)
    d.ellipse([cx - 5, cy + 62, cx + 5, cy + 72], fill=(10, 14, 20))
    for i, t in enumerate(("BitLocker", "Defender", "Firewall", "MFA")):
        px = 24 + (i % 2) * 330 if False else (24 if i % 2 == 0 else bw - 150)
        py = 40 + (i // 2) * 330
        d.rounded_rectangle([px, py, px + 126, py + 34], 17, outline=acc, width=2, fill=(10, 20, 40))
        d.text((px + 63, py + 17), t, font=rob(18, 700), fill=(220, 235, 255), anchor="mm")
    d.text((18, bh - 40), "WINDOWS ENDURECIDO", font=rob(17, 700), fill=(210, 225, 240))
    return img


def cena_terminal(acc, rng):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = Image.new("RGB", (bw, bh), (8, 10, 16))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, bw, 34], fill=(24, 30, 42))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([14 + i * 22, 11, 26 + i * 22, 23], fill=c)
    d.text((100, 8), "Administrador: Windows PowerShell", font=rob(16, 400), fill=(150, 160, 175))
    mono = rob(19, 400)
    linhas = [
        ("PS C:\\> ", "Get-SmbServerConfiguration", (120, 200, 255)),
        ("", "EnableSMB1Protocol : True   [risco]", (255, 120, 110)),
        ("PS C:\\> ", "Set-SmbServerConfiguration `", (120, 200, 255)),
        ("", "   -EnableSMB1Protocol $false", (230, 235, 245)),
        ("", "[OK] SMBv1 desativado", (90, 230, 150)),
        ("PS C:\\> ", "Set-MpPreference -EnableNetworkProtection 1", (120, 200, 255)),
        ("", "[OK] Proteção de rede ativa", (90, 230, 150)),
        ("PS C:\\> ", "Enable-BitLocker -MountPoint C:", (120, 200, 255)),
        ("", "[OK] Disco cifrado", (90, 230, 150)),
        ("PS C:\\> ", "auditpol /set /category:* /success:enable", (120, 200, 255)),
        ("", "[OK] Auditoria ligada", (90, 230, 150)),
    ]
    y = 56
    for pre, txt, cor in linhas:
        x = 18
        if pre:
            d.text((x, y), pre, font=mono, fill=acc)
            x += d.textlength(pre, font=mono)
        d.text((x, y), txt, font=mono, fill=cor)
        y += 30
    d.rectangle([18, y + 2, 32, y + 24], fill=acc)
    return img


def cena_antes_depois(acc, rng):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    img = ig._grad(bw, bh, (14, 18, 26), (10, 14, 20))
    d = ImageDraw.Draw(img)
    metade = bw // 2
    d.line([(metade, 20), (metade, bh - 20)], fill=(40, 48, 60), width=2)
    for lado, (titulo, nota, cor, itens) in enumerate((
        ("PADRÃO", 38, (255, 90, 80), ["SMBv1 ligado", "Admin local p/ todos", "Sem BitLocker", "Sem log de auditoria"]),
        ("ENDURECIDO", 92, (70, 220, 140), ["SMBv1 desligado", "Menor privilégio + MFA", "BitLocker ativo", "Logs centralizados"]),
    )):
        x0 = lado * metade
        d.text((x0 + metade // 2, 40), titulo, font=bebas(40), fill=cor, anchor="mm")
        cx, cy, r = x0 + metade // 2, 160, 70
        d.arc([cx - r, cy - r, cx + r, cy + r], 0, 360, fill=(36, 44, 58), width=16)
        d.arc([cx - r, cy - r, cx + r, cy + r], -90, -90 + 3.6 * nota, fill=cor, width=16)
        d.text((cx, cy), f"{nota}%", font=bebas(54), fill=(240, 244, 250), anchor="mm")
        for i, t in enumerate(itens):
            yy = 268 + i * 48
            d.ellipse([x0 + 22, yy, x0 + 44, yy + 22], fill=cor)
            mx, my, k = x0 + 33, yy + 11, (10, 14, 20)
            if lado == 0:
                d.line([(mx - 5, my - 5), (mx + 5, my + 5)], fill=k, width=3)
                d.line([(mx - 5, my + 5), (mx + 5, my - 5)], fill=k, width=3)
            else:
                d.line([(mx - 6, my), (mx - 2, my + 5), (mx + 6, my - 5)], fill=k, width=3)
            d.text((x0 + 56, yy + 11), t, font=rob(18, 600), fill=(210, 218, 228), anchor="lm")
    d.text((18, bh - 26), "NOTA FICTÍCIA, SÓ PARA ILUSTRAR", font=rob(14, 400), fill=(130, 140, 152))
    return img


def cena_foto(acc, rng):
    bw, bh = SCENE[2] - SCENE[0], SCENE[3] - SCENE[1]
    foto = Image.open(ROOT / "fotos" / "baltic-servers.jpg").convert("L")
    k = max(bw / foto.width, bh / foto.height)
    foto = foto.resize((int(foto.width * k) + 1, int(foto.height * k) + 1))
    foto = foto.crop((foto.width // 2 - bw // 2, 0, foto.width // 2 + bw // 2, bh)).convert("RGB")
    img = Image.blend(foto, Image.new("RGB", (bw, bh), acc), 0.38)
    d = ImageDraw.Draw(img)
    d.rectangle([0, bh - 40, bw, bh], fill=(8, 12, 20))
    d.text((14, bh - 28), CRED, font=rob(14, 400), fill=(170, 180, 192))
    return img


ig.CENAS.update({"escudo": cena_escudo, "terminal": cena_terminal,
                 "antes_depois": cena_antes_depois, "foto": cena_foto})

BASE = {
    "titulo_branco": "Windows de fábrica não é Windows seguro.",
    "titulo_destaque": "Hardening fecha as portas.",
    "historia": "Hardening é reduzir a superfície de ataque: desligar o que não se usa, restringir acessos e ligar as proteções que já vêm no sistema. A maioria dos ataques explora configuração padrão, não falha rara.",
    "licoes": [
        ("Desligue o legado", "SMBv1, protocolos antigos e serviços sem uso são portas abertas para ransomware."),
        ("Menor privilégio + MFA", "Ninguém de administrador no dia a dia. Acesso privilegiado só com segundo fator."),
        ("Cifre, atualize e registre", "BitLocker, Defender, atualizações em dia e logs que alguém realmente consulta."),
    ],
    "pergunta": "Os seus computadores estão no padrão de fábrica ou endurecidos?",
    "hashtags": ["#HARDENING", "#WINDOWS", "#CIBERSEGURANÇA", "#TI", "#TECHDIM"],
}

VARIANTES = [
    ("A-escudo-vetorial", {"cena": "escudo", "cor": "#4DA3FF"}),
    ("B-foto-real-na-moldura", {"cena": "foto", "cor": "#4DA3FF"}),
    ("C-terminal-powershell", {"cena": "terminal", "cor": "#2EE59D"}),
    ("D-foto-de-fundo", {"cena": "foto", "fundo": "baltic-servers.jpg", "credito": CRED, "cor": "#FFB000"}),
    ("E-antes-e-depois", {"cena": "antes_depois", "cor": "#FF8A00"}),
]


def main():
    saida = ROOT / "exemplos" / "hardening-windows"
    for nome, extra in VARIANTES:
        p = dict(BASE, slug=nome, **extra)
        print(ig.desenhar(p, saida / f"{nome}.png"))


if __name__ == "__main__":
    sys.exit(main())
