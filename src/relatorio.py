"""Relatório semanal de resultados: alcance e engajamento de cada post.

Lê registros/AAAA-MM-DD/index.json dos últimos 7 dias (branch assets), busca
as métricas na Meta e grava registros/semanal/AAAA-Sxx.md e .json, com o
ranking dos temas — para saber qual tema traz mais retorno.

Métricas usadas (as clássicas de "impressões" foram descontinuadas pela Meta):
  Facebook  — visualizações únicas (alcance), visualizações, cliques,
              reações, comentários, compartilhamentos
  Instagram — alcance, visualizações, interações, curtidas, comentários,
              compartilhamentos, salvamentos
Stories não entram: a API só guarda as métricas de Story por 24 horas.
O primeiro comentário publicado pela própria automação é descontado.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import pathlib
import re
import sys

import requests

import config
from publishers.meta_auth import page_token

log = logging.getLogger("relatorio")
G = config.GRAPH
TIMEOUT = 30


# ---------------------------------------------------------------- coleta


def _get(path: str, token: str, **params) -> dict:
    try:
        r = requests.get(f"{G}/{path}", params={**params, "access_token": token}, timeout=TIMEOUT)
        return r.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("falha ao consultar %s: %s", path, exc)
        return {}


def _insights(obj_id: str, token: str, metricas: tuple[str, ...]) -> dict:
    """Busca várias métricas; se a chamada em grupo falhar, tenta uma a uma."""
    j = _get(f"{obj_id}/insights", token, metric=",".join(metricas))
    if "data" not in j:
        out = {}
        for m in metricas:
            jj = _get(f"{obj_id}/insights", token, metric=m)
            for d in jj.get("data", []):
                out[d["name"]] = d["values"][0]["value"]
        return out
    return {d["name"]: d["values"][0]["value"] for d in j["data"]}


def metricas_facebook(post_id: str, token: str, comentou: bool) -> dict:
    j = _get(
        post_id, token,
        fields="reactions.summary(total_count).limit(0),"
               "comments.summary(total_count).limit(0),shares",
    )
    reacoes = j.get("reactions", {}).get("summary", {}).get("total_count", 0)
    comentarios = j.get("comments", {}).get("summary", {}).get("total_count", 0)
    comentarios = max(0, comentarios - (1 if comentou else 0))
    compart = j.get("shares", {}).get("count", 0)
    ins = _insights(post_id, token, (
        "post_total_media_view_unique", "post_media_view", "post_clicks",
    ))
    return {
        "alcance": ins.get("post_total_media_view_unique", 0),
        "visualizacoes": ins.get("post_media_view", 0),
        "cliques": ins.get("post_clicks", 0),
        "curtidas": reacoes,
        "comentarios": comentarios,
        "compartilhamentos": compart,
        "salvamentos": 0,
        "interacoes": reacoes + comentarios + compart,
    }


def metricas_instagram(media_id: str, token: str, comentou: bool) -> dict:
    ins = _insights(media_id, token, (
        "reach", "views", "total_interactions", "likes", "comments", "shares", "saved",
    ))
    desconto = 1 if comentou else 0
    return {
        "alcance": ins.get("reach", 0),
        "visualizacoes": ins.get("views", 0),
        "cliques": 0,
        "curtidas": ins.get("likes", 0),
        "comentarios": max(0, ins.get("comments", 0) - desconto),
        "compartilhamentos": ins.get("shares", 0),
        "salvamentos": ins.get("saved", 0),
        "interacoes": max(0, ins.get("total_interactions", 0) - desconto),
    }


def _ig_por_permalink(token: str, ig_user: str) -> dict[str, str]:
    """Posts antigos do registro guardaram só o link: casa link -> id."""
    j = _get(f"{ig_user}/media", token, fields="id,permalink", limit=100)
    return {m.get("permalink", "").rstrip("/"): m["id"] for m in j.get("data", [])}


# ---------------------------------------------------------------- relatório


def coletar(destino: pathlib.Path, inicio: dt.date, fim: dt.date, creds) -> list[dict]:
    token = page_token(creds.meta_token, creds.fb_page_id)
    ig_links: dict[str, str] | None = None
    linhas = []
    dia = inicio
    while dia <= fim:
        indice = destino / "registros" / dia.isoformat() / "index.json"
        try:
            entradas = json.loads(indice.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            entradas = []
        for e in entradas:
            ids = e.get("ids", {})
            comentou = set(e.get("comentou", []))
            for rede in ("facebook", "instagram"):
                if e["redes"].get(rede) != "publicado":
                    continue
                link = e.get("links", {}).get(rede, "")
                ident = ids.get(rede, "")
                if rede == "facebook" and not ident:
                    m = re.search(r"/posts/(\d+)", link)
                    ident = f"{creds.fb_page_id}_{m.group(1)}" if m else ""
                if rede == "instagram" and not ident:
                    if ig_links is None:
                        ig_links = _ig_por_permalink(token, creds.ig_user_id)
                    ident = ig_links.get(link.rstrip("/"), "")
                if not ident:
                    log.warning("sem id para %s de %s %s", rede, dia, e["hora"])
                    continue
                met = (metricas_facebook if rede == "facebook" else metricas_instagram)(
                    ident, token, rede in comentou
                )
                linhas.append({
                    "data": dia.isoformat(), "hora": e["hora"], "tema": e["tema"],
                    "titulo": e["titulo"], "rede": rede, "link": link, **met,
                })
        dia += dt.timedelta(days=1)
    return linhas


def _taxa(inter: float, alcance: float) -> str:
    return f"{100 * inter / alcance:.1f}%" if alcance else "—"


def escrever(linhas: list[dict], destino: pathlib.Path, inicio: dt.date, fim: dt.date) -> pathlib.Path:
    ano, semana, _ = fim.isocalendar()
    pasta = destino / "registros" / "semanal"
    pasta.mkdir(parents=True, exist_ok=True)
    nome = f"{ano}-S{semana:02d}"
    agora = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)
    rot = lambda t: config.THEME_LABELS.get(t, t)  # noqa: E731

    md = [
        f"# Relatório semanal — {nome}",
        "",
        f"Período: {inicio:%d/%m/%Y} a {fim:%d/%m/%Y} · gerado em {agora:%d/%m/%Y %H:%M} (Brasília)",
        "",
    ]
    if not linhas:
        md += ["Nenhum post registrado no período."]
    else:
        md += ["## Resumo por rede", "", "| Rede | Posts | Alcance | Visualizações | Interações | Engajamento |",
               "|---|---|---|---|---|---|"]
        for rede in ("facebook", "instagram"):
            ls = [x for x in linhas if x["rede"] == rede]
            if not ls:
                continue
            a = sum(x["alcance"] for x in ls); v = sum(x["visualizacoes"] for x in ls)
            i = sum(x["interacoes"] for x in ls)
            md.append(f"| {rede.capitalize()} | {len(ls)} | {a} | {v} | {i} | {_taxa(i, a)} |")

        temas = {}
        for x in linhas:
            t = temas.setdefault(x["tema"], {"posts": set(), "alcance": 0, "inter": 0, "n": 0})
            t["posts"].add((x["data"], x["hora"]))
            t["alcance"] += x["alcance"]; t["inter"] += x["interacoes"]; t["n"] += 1
        ranking = sorted(temas.items(), key=lambda kv: (kv[1]["inter"] / kv[1]["n"], kv[1]["alcance"] / kv[1]["n"]), reverse=True)
        md += ["", "## Qual tema traz mais retorno", "",
               "Ordenado pela média de interações por post (cada rede conta como um post).", "",
               "| # | Tema | Posts | Alcance médio | Interações médias | Engajamento |",
               "|---|---|---|---|---|---|"]
        for n, (tema, t) in enumerate(ranking, 1):
            md.append(
                f"| {n} | {rot(tema)} | {len(t['posts'])} | {t['alcance'] / t['n']:.0f} | "
                f"{t['inter'] / t['n']:.1f} | {_taxa(t['inter'], t['alcance'])} |"
            )

        top = sorted(linhas, key=lambda x: (x["interacoes"], x["alcance"]), reverse=True)[:3]
        md += ["", "## Melhores posts", ""]
        for x in top:
            md.append(
                f"- **{x['titulo']}** ({rot(x['tema'])}, {x['rede']}, {x['data'][8:]}/{x['data'][5:7]}) — "
                f"{x['interacoes']} interações, alcance {x['alcance']} · [ver post]({x['link']})"
            )

        md += ["", "## Todos os posts", "",
               "| Data | Hora | Tema | Título | Rede | Alcance | Visual. | Curtidas | Coment. | Compart. | Salvos | Engaj. |",
               "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for x in sorted(linhas, key=lambda x: (x["data"], x["hora"], x["rede"])):
            titulo = x["titulo"].replace("|", "/")
            titulo = titulo if len(titulo) <= 55 else titulo[:54] + "…"
            md.append(
                f"| {x['data'][8:]}/{x['data'][5:7]} | {x['hora']} | {rot(x['tema'])} | [{titulo}]({x['link']}) | "
                f"{x['rede']} | {x['alcance']} | {x['visualizacoes']} | {x['curtidas']} | {x['comentarios']} | "
                f"{x['compartilhamentos']} | {x['salvamentos']} | {_taxa(x['interacoes'], x['alcance'])} |"
            )

    md += ["", "## Observações", "",
           "- Engajamento = interações ÷ alcance. Interações: curtidas/reações, comentários, compartilhamentos e salvamentos.",
           "- O primeiro comentário publicado pela própria automação é descontado.",
           "- Stories não entram: a API da Meta só guarda as métricas de Story por 24 horas.",
           "- Métricas de posts muito recentes ainda estão crescendo; o retrato fiel é a partir de ~48 h.",
           "- LinkedIn entra quando o token estiver configurado."]

    arq = pasta / f"{nome}.md"
    arq.write_text("\n".join(md) + "\n", encoding="utf-8")
    (pasta / f"{nome}.json").write_text(
        json.dumps({"semana": nome, "inicio": inicio.isoformat(), "fim": fim.isoformat(), "posts": linhas},
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    relatorios = sorted((p.stem for p in pasta.glob("*-S*.md")), reverse=True)
    (pasta / "README.md").write_text(
        "# Relatórios semanais\n\n" + "\n".join(f"- [{r}]({r}.md)" for r in relatorios) + "\n",
        encoding="utf-8",
    )
    return arq


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Relatório semanal de resultados")
    ap.add_argument("--dest", required=True, help="raiz do checkout do branch assets")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--incluir-hoje", action="store_true", help="fecha o período hoje, não ontem")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    creds = config.Credentials()
    if not (creds.meta_token and creds.fb_page_id):
        log.error("META_ACCESS_TOKEN e FB_PAGE_ID são necessários")
        return 1

    hoje = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date()
    fim = hoje if args.incluir_hoje else hoje - dt.timedelta(days=1)
    inicio = fim - dt.timedelta(days=args.dias - 1)
    destino = pathlib.Path(args.dest)

    linhas = coletar(destino, inicio, fim, creds)
    arq = escrever(linhas, destino, inicio, fim)
    log.info("relatório gravado em %s (%d linhas)", arq.relative_to(destino), len(linhas))

    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as fh:
            fh.write(arq.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
