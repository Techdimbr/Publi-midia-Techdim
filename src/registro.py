"""Pasta diária de registros: registros/AAAA-MM-DD/ no branch assets.

Cada publicação grava um arquivo com o texto de cada rede, as imagens, as
fontes, o motivo da pauta e o resultado (link do post no ar, ou o erro).
O README.md da pasta é o índice do dia. Grava também quando a publicação
falha — é aí que o registro mais importa.

O branch assets é público: tudo que parece credencial é removido antes
de gravar.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re

import config

# Token de usuário/página da Meta (EAA...) e token do LinkedIn (AQ...).
_CREDENCIAL = re.compile(r"\bEAA[A-Za-z0-9]{20,}|\bAQ[A-Za-z0-9_-]{40,}")

ICONE = {"publicado": "✅", "falhou": "❌", "não configurado": "⚠️", "não executado": "⏸️"}
REDES = ("facebook", "instagram", "linkedin")


def _limpo(texto: str) -> str:
    return _CREDENCIAL.sub("[REDIGIDO]", texto or "")


def _celula(texto: str) -> str:
    """Texto seguro para uma célula de tabela Markdown."""
    return re.sub(r"\s+", " ", texto or "").replace("|", "/").strip()


def _agora_brasilia() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)


def escrever(
    manifest: dict, resultado: dict, destino: pathlib.Path, run_url: str = ""
) -> pathlib.Path:
    """Grava o registro desta publicação e atualiza o índice do dia."""
    agora = _agora_brasilia()
    dia = manifest["date"]
    pasta = destino / "registros" / dia
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = pasta / f"{agora:%Hh%M}-{manifest['theme']}.md"
    n = 2
    while arquivo.exists():  # duas execuções do mesmo tema no mesmo minuto
        arquivo = pasta / f"{agora:%Hh%M}-{manifest['theme']}-{n}.md"
        n += 1
    redes = resultado.get("redes", {})
    rotulo = config.THEME_LABELS.get(manifest["theme"], manifest["theme"])

    linhas = [
        f"# {rotulo} — {manifest['titulo']}",
        "",
        f"- **Data:** {dia}, {agora:%H:%M} (horário de Brasília)",
        f"- **Curadoria:** {manifest.get('curadoria', '-')}",
    ]
    if run_url:
        linhas.append(f"- **Execução no Actions:** {run_url}")
    if manifest.get("motivo"):
        linhas.append(f"- **Por que esta pauta:** {manifest['motivo']}")

    linhas += ["", "## Resultado", "", "| Rede | Status | Link |", "|---|---|---|"]
    for rede in manifest["networks"]:
        r = redes.get(rede, {"status": "não executado"})
        status = f"{ICONE.get(r['status'], '')} {r['status']}"
        if r.get("erro"):
            status += f" — {r['erro']}"
        linhas.append(f"| {rede} | {_celula(status)} | {r.get('link', '')} |")

    fontes = manifest.get("fontes") or []
    if fontes:
        linhas += ["", "## Fontes", ""]
        linhas += [f"- [{nome}]({url})" for nome, url in fontes]

    for rede, dados in manifest["networks"].items():
        linhas += ["", f"## {rede.capitalize()}", "", "```text", dados["caption"], "```", ""]
        # caminho relativo: registros/<dia>/arquivo.md -> posts/<dia>/...
        linhas += [f"![{rede} {i}](../../{f})" for i, f in enumerate(dados["files"], 1)]

    arquivo.write_text(_limpo("\n".join(linhas)) + "\n", encoding="utf-8")
    _indice(pasta, dia, arquivo.name, manifest, redes, agora)
    return arquivo


def _indice(pasta, dia, nome, manifest, redes, agora) -> None:
    """Mantém index.json (dados) e README.md (o que o GitHub mostra na pasta)."""
    indice_json = pasta / "index.json"
    try:
        entradas = json.loads(indice_json.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        entradas = []

    entradas.append({
        "hora": f"{agora:%H:%M}",
        "tema": manifest["theme"],
        "titulo": manifest["titulo"],
        "curadoria": manifest.get("curadoria", "-"),
        "arquivo": nome,
        "redes": {
            r: redes.get(r, {}).get(
                "status", "não executado" if r in manifest["networks"] else "-"
            )
            for r in REDES
        },
        "links": {r: redes.get(r, {}).get("link", "") for r in REDES},
    })
    indice_json.write_text(
        _limpo(json.dumps(entradas, ensure_ascii=False, indent=2)) + "\n", encoding="utf-8"
    )

    linhas = [
        f"# Registros de {dia}",
        "",
        "Tudo que a automação publicou (ou tentou publicar) neste dia.",
        "",
        "| Hora | Tema | Título | Facebook | Instagram | LinkedIn |",
        "|---|---|---|---|---|---|",
    ]
    for e in entradas:
        celulas = []
        for r in REDES:
            st = e["redes"].get(r, "-")
            link = e["links"].get(r, "")
            icone = ICONE.get(st, "—")
            celulas.append(f"[{icone}]({link})" if link else icone)
        rotulo = config.THEME_LABELS.get(e["tema"], e["tema"])
        linhas.append(
            f"| {e['hora']} | {rotulo} | [{_celula(e['titulo'])}]({e['arquivo']}) | "
            + " | ".join(celulas) + " |"
        )
    linhas += ["", "✅ publicado · ❌ falhou · ⚠️ rede não configurada · ⏸️ não executado · — não se aplica"]
    (pasta / "README.md").write_text(_limpo("\n".join(linhas)) + "\n", encoding="utf-8")
