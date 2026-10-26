#!/usr/bin/env python3
"""Orquestrador Antigravity Spark para o Publi-midia-Techdim.

Permite que o Antigravity 2.0 e o Host Soberano Debian gerenciem:
1. Geração diária de pautas com Gemini Spark (noticias, hacker, dica, servico).
2. Validação estrita geométrica e textual do infográfico.
3. Pré-visualização e geração local das artes e carrosséis.
4. Sincronização e auditoria das postagens.
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import os
import pathlib
import subprocess
import sys

# Ajusta path para importar src
RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

import config
import content
import gemini
import validar_pauta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("antigravity_spark")


def obter_hoje() -> str:
    return config.hoje().isoformat()


def status_dia(dia_iso: str | None = None) -> dict:
    dia = dia_iso or obter_hoje()
    pasta_dia = RAIZ / "content" / "diario" / dia
    temas = ["noticias", "hacker", "dica", "servico"]
    resumo = {"dia": dia, "pasta_existe": pasta_dia.exists(), "temas": {}}

    data_obj = dt.date.fromisoformat(dia)
    erros_globais, avisos_globais = [], []
    if pasta_dia.exists():
        erros_globais, avisos_globais = validar_pauta.verificar(data_obj)

    for tema in temas:
        arquivo = pasta_dia / f"{tema}.json"
        if arquivo.exists():
            erros_tema = [e for e in erros_globais if tema in e.lower() or f"{tema}.json" in e.lower()]
            resumo["temas"][tema] = {"presente": True, "valido": len(erros_tema) == 0, "erros": erros_tema}
        else:
            resumo["temas"][tema] = {"presente": False, "valido": False, "erros": ["arquivo ausente"]}
    return resumo


def gerar_pauta(dia_iso: str | None = None, forcar: bool = False) -> int:
    dia = dia_iso or obter_hoje()
    log.info("Iniciando geração de pauta com Gemini Spark para %s (forcar=%s)...", dia, forcar)
    cmd = [sys.executable, str(RAIZ / "src" / "pauta_reserva.py"), "--dia", dia, "--gravar"]
    if forcar:
        cmd.append("--forcar")
        cmd.extend(["--tema", "noticias", "--tema", "hacker", "--tema", "dica", "--tema", "servico"])

    env = os.environ.copy()
    env["PYTHONPATH"] = str(RAIZ / "src")
    res = subprocess.run(cmd, env=env, cwd=str(RAIZ))
    if res.returncode != 0:
        log.error("Falha ao gerar pauta com Gemini Spark (código %d)", res.returncode)
        return res.returncode

    # Validação pós-geração
    log.info("Auditando integridade das pautas geradas...")
    st = status_dia(dia)
    tudo_valido = True
    for tema, info in st["temas"].items():
        if not info["presente"] or not info["valido"]:
            log.warning("Tema %s inválido ou ausente: %s", tema, info["erros"])
            tudo_valido = False
        else:
            log.info("Tema %s validado com sucesso!", tema)

    return 0 if tudo_valido else 1


def gerar_arte(tema: str) -> int:
    log.info("Renderizando arte e infográfico para o tema: %s...", tema)
    cmd = [sys.executable, str(RAIZ / "src" / "main.py"), "--theme", tema, "generate"]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(RAIZ / "src")
    res = subprocess.run(cmd, env=env, cwd=str(RAIZ))
    return res.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Orquestrador Antigravity Spark TECHDIM")
    parser.add_argument("--status", action="store_true", help="Audita status da pauta do dia")
    parser.add_argument("--pauta", action="store_true", help="Gera as 4 pautas do dia com Gemini Spark")
    parser.add_argument("--forcar", action="store_true", help="Sobrescreve pautas existentes")
    parser.add_argument("--dia", default="", help="Data AAAA-MM-DD (padrão: hoje em Brasília)")
    parser.add_argument("--gerar-arte", choices=["noticias", "hacker", "dica", "servico"], help="Renderiza imagens de um tema")

    args = parser.parse_args()
    dia = args.dia or obter_hoje()

    if args.status:
        st = status_dia(dia)
        print(f"\n=== Status TECHDIM Spark - Dia: {st['dia']} ===")
        for tema, info in st["temas"].items():
            status_txt = "OK" if (info["presente"] and info["valido"]) else ("ERRO" if info["presente"] else "AUSENTE")
            print(f"  [{status_txt}] {tema:10s} (erros: {info['erros']})")
        return 0

    if args.pauta:
        return gerar_pauta(dia, forcar=args.forcar)

    if args.gerar_arte:
        return gerar_arte(args.gerar_arte)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
