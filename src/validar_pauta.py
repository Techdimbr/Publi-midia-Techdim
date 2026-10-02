"""Confere a pauta de um dia antes de ela ir para o ar.

  python src/validar_pauta.py [AAAA-MM-DD]      (padrão: hoje, em Brasília)

Sai com código 1 se algum arquivo da pauta não vira post ou perde o bloco
"infografico" (o post sairia com a arte antiga). Textos acima do tamanho
recomendado e cenas repetidas entre os posts do dia viram avisos, que não
reprovam. É o que a Routine roda antes de gravar a pauta.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import sys

import config
import content
import infografico

# Tamanho recomendado de cada campo (o desenho aguenta mais, mas fica apertado).
RECOMENDADO = {
    "titulo": 90, "fecho": 130, "titulo_branco": 55, "titulo_destaque": 35,
    "historia": 230, "pergunta": 80,
}
RECOMENDADO_PONTO, RECOMENDADO_LICAO_TITULO, RECOMENDADO_LICAO_TEXTO = 170, 22, 110


def _avisos_de_tamanho(item: dict) -> list[str]:
    avisos = []

    def checar(nome: str, valor: object, limite: int) -> None:
        if isinstance(valor, str) and len(valor.strip()) > limite:
            avisos.append(f"{nome}: {len(valor.strip())} caracteres (recomendado até {limite})")

    for campo in ("titulo", "fecho"):
        checar(campo, item.get(campo), RECOMENDADO[campo])
    for i, ponto in enumerate(item.get("pontos") or [], 1):
        checar(f"pontos[{i}]", ponto, RECOMENDADO_PONTO)
    bloco = item.get("infografico")
    if isinstance(bloco, dict):
        for campo in ("titulo_branco", "titulo_destaque", "historia", "pergunta"):
            checar(f"infografico.{campo}", bloco.get(campo), RECOMENDADO[campo])
        for i, par in enumerate(bloco.get("licoes") or [], 1):
            if isinstance(par, (list, tuple)) and len(par) == 2:
                checar(f"infografico.licoes[{i}] título", par[0], RECOMENDADO_LICAO_TITULO)
                checar(f"infografico.licoes[{i}] texto", par[1], RECOMENDADO_LICAO_TEXTO)
    return avisos


def verificar(dia: dt.date, pasta: pathlib.Path | None = None) -> tuple[list[str], list[str]]:
    """(problemas, avisos) da pauta do dia. Problema = o post perderia algo; aviso = só atenção."""
    base = (pasta or content.CONTENT_DIR / "diario") / dia.isoformat()
    problemas: list[str] = []
    avisos: list[str] = []
    combinacoes: dict[str, str] = {}

    for tema in content.PAUTA:
        arq = base / f"{tema}.json"
        if not arq.exists():
            avisos.append(f"{tema}: sem arquivo — aquele horário usará o conteúdo de reserva")
            continue
        try:
            item = json.loads(arq.read_text(encoding="utf-8"))
            content._post_do_json(tema, item)
        except (json.JSONDecodeError, ValueError) as exc:
            problemas.append(f"{tema}: arquivo inválido ({exc}) — usará o conteúdo de reserva")
            continue

        bloco = item.get("infografico")
        if bloco is None:
            problemas.append(f"{tema}: sem bloco infografico — sairia com a arte antiga")
        else:
            try:
                p = infografico.validar(bloco, tema)
            except infografico.InfograficoInvalido as exc:
                problemas.append(f"{tema}: bloco infografico inválido ({exc}) — sairia com a arte antiga")
                p = None
            if p:
                if tema == "hacker" and p["cena"] != "painel":
                    avisos.append("hacker: sem 'cena': 'painel' e 'terminal' — o painel de terminal é o padrão do tema")
                if p["cena"] == "composta":
                    c = p["cena_composta"]
                    combinacoes[tema] = f"{c['fundo']}+{'+'.join(c['elementos'])}"
                    if (bloco.get("cena_composta") or {}).get("elementos") != c["elementos"]:
                        avisos.append(f"{tema}: elementos de cena inválidos foram descartados")
                else:
                    combinacoes[tema] = p["cena"]
        avisos += [f"{tema}: {a}" for a in _avisos_de_tamanho(item)]

    repetidas = {v for v in combinacoes.values() if list(combinacoes.values()).count(v) > 1}
    for r in sorted(repetidas):
        temas = ", ".join(t for t, v in combinacoes.items() if v == r)
        avisos.append(f"cena repetida entre {temas}: {r}")
    return problemas, avisos


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    dia = dt.date.fromisoformat(argv[0]) if argv else config.hoje()
    problemas, avisos = verificar(dia)
    for p in problemas:
        print(f"PROBLEMA  {p}")
    for a in avisos:
        print(f"aviso     {a}")
    if not problemas and not avisos:
        print(f"pauta de {dia.isoformat()} ok")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
