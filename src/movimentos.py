"""Diário de movimentações: tudo que a automação (ou alguém) faz, em ordem.

Cada movimento é uma linha de registros/AAAA-MM-DD/movimentos.jsonl no branch
assets; movimentos.md é a tabela do dia, regenerada a cada gravação. Inclui
testes e ensaios — a coluna "Teste" os marca — e também ações manuais
(comentou, apagou, editou), registradas pelo workflow "Registrar movimento".
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys

ICONE = {
    "planejado": "🗓️", "iniciado": "▶️", "gerado": "🖼️", "publicado": "✅",
    "story": "📱", "comentou": "💬", "apagou": "🗑️", "editou": "✏️",
    "falhou": "❌", "ensaio": "🧪", "pulado": "⚠️", "observacao": "📝",
}
_CREDENCIAL = re.compile(r"\bEAA[A-Za-z0-9]{20,}|\bAQ[A-Za-z0-9_-]{40,}|\bWPL_AP\d\.[\w./=+-]+")


def agora_brasilia() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)


def _limpo(t: str) -> str:
    return _CREDENCIAL.sub("[REDIGIDO]", t or "")


def _cel(t: str) -> str:
    return re.sub(r"\s+", " ", _limpo(t)).replace("|", "/").strip()


def registrar(destino: pathlib.Path, eventos: list[dict], dia: str | None = None) -> pathlib.Path:
    """Acrescenta eventos ao dia e regenera movimentos.md."""
    agora = agora_brasilia()
    dia = dia or f"{agora:%Y-%m-%d}"
    pasta = destino / "registros" / dia
    pasta.mkdir(parents=True, exist_ok=True)
    jsonl = pasta / "movimentos.jsonl"
    with jsonl.open("a", encoding="utf-8") as fh:
        for e in eventos:
            e = {"hora": f"{agora:%H:%M:%S}", "teste": False, **e}
            e = {k: (_limpo(v) if isinstance(v, str) else v) for k, v in e.items()}
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    todos = [json.loads(l) for l in jsonl.read_text(encoding="utf-8").splitlines() if l.strip()]
    todos.sort(key=lambda e: e["hora"])
    linhas = [
        f"# Movimentações de {dia}", "",
        "Tudo que foi planejado, gerado, publicado, comentado, apagado, editado ou testado.",
        "", "| Hora | Movimento | Tema | Rede | Detalhe | Origem | Teste | Link |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for e in todos:
        mov = f"{ICONE.get(e['tipo'], '•')} {e['tipo']}"
        det = _cel(e.get("detalhe", ""))
        if e.get("retroativo"):
            det += " _(reconstituído do histórico)_"
        link = f"[abrir]({e['link']})" if e.get("link") else ""
        linhas.append(
            f"| {e['hora'][:5]} | {mov} | {_cel(e.get('tema', ''))} | {_cel(e.get('rede', ''))} | {det} "
            f"| {_cel(e.get('origem', ''))} | {'🧪' if e.get('teste') else ''} | {link} |"
        )
    (pasta / "movimentos.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return pasta / "movimentos.md"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Registra um movimento no diário do dia")
    ap.add_argument("--dest", required=True)
    ap.add_argument("--tipo", required=True, choices=sorted(ICONE))
    ap.add_argument("--detalhe", required=True)
    ap.add_argument("--tema", default=""); ap.add_argument("--rede", default="")
    ap.add_argument("--link", default=""); ap.add_argument("--origem", default="manual")
    ap.add_argument("--teste", action="store_true")
    a = ap.parse_args(argv)
    registrar(pathlib.Path(a.dest), [{
        "tipo": a.tipo, "detalhe": a.detalhe, "tema": a.tema, "rede": a.rede,
        "link": a.link, "origem": a.origem, "teste": a.teste,
    }])
    return 0


if __name__ == "__main__":
    sys.exit(main())
