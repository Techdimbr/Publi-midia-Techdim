"""Coleta diária de métricas — o que o relatório semanal não consegue ver depois.

Duas coisas se perdem se ninguém olhar no mesmo dia:

  Stories — a API da Meta guarda as métricas de Story por 24 horas. O relatório
            de segunda-feira nunca vê o Story de terça.
  Seguidores — o número de seguidores é um retrato do instante. Sem uma foto por
            dia não existe curva de crescimento, e crescimento de seguidor é a
            meta que importa nos primeiros meses de uma conta.

Grava dois arquivos no branch assets:
  registros/AAAA-MM-DD/metricas.json  — retrato do dia (contas + Stories)
  registros/seguidores.csv            — uma linha por dia, para a curva

Nada aqui pode derrubar o workflow: sem credencial ou com a API fora do ar, o
que der para medir é gravado e o resto fica em branco.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import logging
import os
import pathlib
import sys

import requests

import config
from publishers.meta_auth import page_token

log = logging.getLogger("metricas")
TIMEOUT = 30

# Métricas de Story. "impressions" foi descontinuada pela Meta; "reach" e
# "views" são as que restaram, e "replies" é a interação própria do formato.
METRICAS_STORY = ("reach", "views", "replies")


def _get(path: str, token: str, **params) -> dict:
    try:
        r = requests.get(
            f"{config.GRAPH}/{path}", params={**params, "access_token": token}, timeout=TIMEOUT
        )
        return r.json()
    except (requests.RequestException, ValueError) as exc:
        log.warning("falha ao consultar %s: %s", path, exc)
        return {}


def _insights(obj_id: str, token: str, metricas: tuple[str, ...], **extra) -> dict:
    """Métricas de um objeto; se a chamada em grupo falhar, tenta uma a uma."""
    j = _get(f"{obj_id}/insights", token, metric=",".join(metricas), **extra)
    if "data" not in j:
        out: dict = {}
        for m in metricas:
            for d in _get(f"{obj_id}/insights", token, metric=m, **extra).get("data", []):
                out[d["name"]] = _valor(d)
        return out
    return {d["name"]: _valor(d) for d in j["data"]}


def _valor(d: dict):
    """Último valor da série; a Meta ora devolve "values", ora "total_value"."""
    vals = d.get("values")
    if vals:
        return vals[-1].get("value", 0)
    return d.get("total_value", {}).get("value", 0)


# ---------------------------------------------------------------- contas


def contas(creds) -> dict:
    """Retrato das contas: seguidores, visitas ao perfil e cliques no site."""
    out: dict = {}

    if creds.ig_user_id:
        perfil = _get(
            creds.ig_user_id, creds.meta_token, fields="followers_count,follows_count,media_count"
        )
        ins = _insights(
            creds.ig_user_id, creds.meta_token, ("profile_views", "website_clicks"),
            period="day", metric_type="total_value",
        )
        out["instagram"] = {
            "seguidores": perfil.get("followers_count", 0),
            "seguindo": perfil.get("follows_count", 0),
            "publicacoes": perfil.get("media_count", 0),
            "visitas_ao_perfil": ins.get("profile_views", 0),
            "cliques_no_site": ins.get("website_clicks", 0),
        }

    if creds.fb_page_id:
        try:
            token = page_token(creds.meta_token, creds.fb_page_id)
        except Exception as exc:  # noqa: BLE001 — medir nunca derruba o job
            log.warning("sem page token: %s", exc)
        else:
            pagina = _get(creds.fb_page_id, token, fields="followers_count,fan_count")
            out["facebook"] = {
                "seguidores": pagina.get("followers_count", pagina.get("fan_count", 0)),
                "curtidas_da_pagina": pagina.get("fan_count", 0),
            }

    return out


# ---------------------------------------------------------------- stories


def stories(creds, dia: dt.date) -> list[dict]:
    """Métricas dos Stories do dia. Precisa rodar no mesmo dia: expiram em 24 h."""
    if not creds.ig_user_id:
        return []
    j = _get(f"{creds.ig_user_id}/stories", creds.meta_token, fields="id,timestamp,permalink")
    out = []
    for item in j.get("data", []):
        quando = (item.get("timestamp") or "")[:10]
        if quando and quando != dia.isoformat():
            continue
        met = _insights(item["id"], creds.meta_token, METRICAS_STORY)
        out.append({
            "id": item["id"],
            "link": item.get("permalink", ""),
            "hora": (item.get("timestamp") or "")[11:16],
            "alcance": met.get("reach", 0),
            "visualizacoes": met.get("views", 0),
            "respostas": met.get("replies", 0),
        })
    return out


# ---------------------------------------------------------------- gravação


COLUNAS = [
    "data", "ig_seguidores", "ig_visitas_perfil", "ig_cliques_site",
    "fb_seguidores", "stories", "stories_alcance",
]


def gravar(destino: pathlib.Path, dia: dt.date, dados: dict) -> pathlib.Path:
    pasta = destino / "registros" / dia.isoformat()
    pasta.mkdir(parents=True, exist_ok=True)
    arq = pasta / "metricas.json"
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    ig = dados.get("contas", {}).get("instagram", {})
    fb = dados.get("contas", {}).get("facebook", {})
    sts = dados.get("stories", [])
    linha = {
        "data": dia.isoformat(),
        "ig_seguidores": ig.get("seguidores", ""),
        "ig_visitas_perfil": ig.get("visitas_ao_perfil", ""),
        "ig_cliques_site": ig.get("cliques_no_site", ""),
        "fb_seguidores": fb.get("seguidores", ""),
        "stories": len(sts),
        "stories_alcance": sum(s["alcance"] for s in sts),
    }

    csv_path = destino / "registros" / "seguidores.csv"
    anteriores: list[dict] = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8", newline="") as fh:
            anteriores = [r for r in csv.DictReader(fh) if r.get("data") != linha["data"]]
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUNAS)
        w.writeheader()
        for r in sorted(anteriores + [linha], key=lambda r: r["data"]):
            w.writerow({c: r.get(c, "") for c in COLUNAS})
    return arq


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Coleta diária de métricas (Stories e seguidores)")
    ap.add_argument("--dest", required=True, help="raiz do checkout do branch assets")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    creds = config.Credentials()
    if not creds.has_meta:
        log.error("META_ACCESS_TOKEN e FB_PAGE_ID/IG_USER_ID são necessários")
        return 1

    dia = config.hoje()
    dados = {
        "data": dia.isoformat(),
        "coletado_em": config.agora().isoformat(timespec="minutes"),
        "contas": contas(creds),
        "stories": stories(creds, dia),
    }
    arq = gravar(pathlib.Path(args.dest), dia, dados)
    ig = dados["contas"].get("instagram", {})
    log.info(
        "gravado em %s — %s seguidores no Instagram, %d Story(ies)",
        arq, ig.get("seguidores", "?"), len(dados["stories"]),
    )

    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as fh:
            fh.write(
                f"### Métricas de {dia:%d/%m}\n\n"
                f"- Instagram: {ig.get('seguidores', '?')} seguidores, "
                f"{ig.get('visitas_ao_perfil', 0)} visitas ao perfil, "
                f"{ig.get('cliques_no_site', 0)} cliques no site\n"
                f"- Facebook: {dados['contas'].get('facebook', {}).get('seguidores', '?')} seguidores\n"
                f"- Stories do dia: {len(dados['stories'])} "
                f"(alcance somado {sum(s['alcance'] for s in dados['stories'])})\n"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
