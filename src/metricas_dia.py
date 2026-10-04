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

Dado que a API não devolveu fica EM BRANCO (None no JSON, vazio no CSV), nunca
zero: um zero falso é indistinguível de um zero verdadeiro e estraga a curva. Só
o número de seguidores é obrigatório; sem ele a execução termina com erro, para
o GitHub avisar em vez de gravar um ponto vazio em silêncio.
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

# Métricas de Story (documentação oficial do IG Media Insights). "impressions"
# foi descontinuada. "follows" e "profile_visits" são por Story: dizem quantos
# seguidores e visitas ao perfil cada Story trouxe. Os insights de Story só
# existem por 24 horas e dão erro com menos de 5 visualizadores — numa conta nova
# isso vai acontecer, e o resultado correto é "sem dado", não zero.
METRICAS_STORY = ("reach", "views", "replies", "follows", "profile_visits", "shares")

# Métricas da conta com period=day e metric_type=total_value, listadas como
# válidas na documentação atual do IG User Insights.
METRICAS_CONTA = ("reach", "views", "accounts_engaged", "total_interactions", "profile_links_taps")
# Existiam em versões anteriores da API e a documentação atual não as lista. Se a
# API as recusar, ficam em branco.
METRICAS_CONTA_OPCIONAIS = ("profile_views", "website_clicks")


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
    """Retrato das contas. O que a API não devolveu vem como None."""
    out: dict = {}

    if creds.ig_user_id:
        perfil = _get(
            creds.ig_user_id, creds.meta_token, fields="followers_count,follows_count,media_count"
        )
        ins = _insights(
            creds.ig_user_id, creds.meta_token, METRICAS_CONTA + METRICAS_CONTA_OPCIONAIS,
            period="day", metric_type="total_value",
        )
        out["instagram"] = {
            "seguidores": perfil.get("followers_count"),
            "seguindo": perfil.get("follows_count"),
            "publicacoes": perfil.get("media_count"),
            "alcance": ins.get("reach"),
            "visualizacoes": ins.get("views"),
            "contas_engajadas": ins.get("accounts_engaged"),
            "interacoes": ins.get("total_interactions"),
            "toques_nos_links": ins.get("profile_links_taps"),
            "visitas_ao_perfil": ins.get("profile_views"),
            "cliques_no_site": ins.get("website_clicks"),
        }

    if creds.fb_page_id:
        try:
            token = page_token(creds.meta_token, creds.fb_page_id)
        except Exception as exc:  # noqa: BLE001 — medir nunca derruba o job
            log.warning("sem page token: %s", exc)
        else:
            pagina = _get(creds.fb_page_id, token, fields="followers_count,fan_count")
            out["facebook"] = {
                "seguidores": pagina.get("followers_count", pagina.get("fan_count")),
                "curtidas_da_pagina": pagina.get("fan_count"),
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
            "alcance": met.get("reach"),
            "visualizacoes": met.get("views"),
            "respostas": met.get("replies"),
            "seguidores_novos": met.get("follows"),
            "visitas_ao_perfil": met.get("profile_visits"),
            "compartilhamentos": met.get("shares"),
        })
    return out


# ---------------------------------------------------------------- gravação


COLUNAS = [
    "data", "ig_seguidores", "ig_alcance", "ig_visitas_perfil", "ig_cliques_site",
    "fb_seguidores", "stories", "stories_alcance", "stories_seguidores_novos",
]


def _vazio(v) -> object:
    """Dado ausente vai em branco para o CSV; zero verdadeiro continua zero."""
    return "" if v is None else v


def _soma(valores: list) -> int | str:
    """Soma o que existe. Se nenhum Story trouxe o dado, devolve "" em vez de 0."""
    presentes = [v for v in valores if v is not None]
    return sum(presentes) if presentes else ""


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
        "ig_seguidores": _vazio(ig.get("seguidores")),
        "ig_alcance": _vazio(ig.get("alcance")),
        "ig_visitas_perfil": _vazio(ig.get("visitas_ao_perfil")),
        "ig_cliques_site": _vazio(ig.get("cliques_no_site")),
        "fb_seguidores": _vazio(fb.get("seguidores")),
        "stories": len(sts),
        "stories_alcance": _soma([x.get("alcance") for x in sts]),
        "stories_seguidores_novos": _soma([x.get("seguidores_novos") for x in sts]),
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


def _mostrar(v) -> str:
    return "sem dado" if v is None or v == "" else str(v)


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
    fb = dados["contas"].get("facebook", {})
    sts = dados["stories"]
    log.info(
        "gravado em %s — %s seguidores no Instagram, %d Story(ies)",
        arq, _mostrar(ig.get("seguidores")), len(sts),
    )

    resumo = os.environ.get("GITHUB_STEP_SUMMARY")
    if resumo:
        with open(resumo, "a", encoding="utf-8") as fh:
            fh.write(
                f"### Métricas de {dia:%d/%m}\n\n"
                f"- Instagram: {_mostrar(ig.get('seguidores'))} seguidores, "
                f"alcance {_mostrar(ig.get('alcance'))}, "
                f"visitas ao perfil {_mostrar(ig.get('visitas_ao_perfil'))}, "
                f"cliques no site {_mostrar(ig.get('cliques_no_site'))}\n"
                f"- Facebook: {_mostrar(fb.get('seguidores'))} seguidores\n"
                f"- Stories do dia: {len(sts)} "
                f"(alcance somado {_mostrar(_soma([x.get('alcance') for x in sts]))}, "
                f"seguidores novos {_mostrar(_soma([x.get('seguidores_novos') for x in sts]))})\n"
            )

    # O número de seguidores é o que a curva existe para registrar. Sem ele o
    # arquivo do dia sai incompleto e a execução falha de propósito: é o que faz o
    # GitHub avisar, em vez de a curva ganhar um buraco que ninguém vê.
    if creds.ig_user_id and ig.get("seguidores") is None:
        log.error("não consegui ler o número de seguidores do Instagram (token, permissão ou API)")
        return 1
    if creds.fb_page_id and fb and fb.get("seguidores") is None:
        log.error("não consegui ler o número de seguidores do Facebook")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
