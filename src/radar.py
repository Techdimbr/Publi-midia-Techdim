"""Radar: confere contas do Instagram pela API da Meta e lê os perfis da TECHDIM (só leitura).

Serve ao plano de crescimento: monta uma lista de contas para uma PESSOA seguir e interagir, com dados reais
(existe, é profissional, quantos seguidores, quando postou por último), e mostra o texto que os perfis da TECHDIM
exibem hoje. Não segue, não curte nem comenta: a API da Meta não oferece isso para contas de terceiros, e fazê-lo
por robô viola as regras das redes e arrisca o bloqueio da conta.

  python src/radar.py --dest /tmp/assets --acao validar-lista [--lista content/perfis_alvo.json]
  python src/radar.py --dest /tmp/assets --acao diagnostico

Grava em <dest>/registros/radar/ (o branch assets, pelo workflow radar.yml) e imprime um resumo.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import pathlib
import re
import sys
import time

import config
from publishers import instagram
from publishers.common import PublishError, request
from publishers.meta_auth import page_token
from seguranca import redigir

log = logging.getLogger("radar")

LISTA_PADRAO = pathlib.Path(__file__).resolve().parent.parent / "content" / "perfis_alvo.json"
PAUSA = 1.0  # segundos entre consultas: a Business Discovery tem limite de uso
HANDLE = re.compile(r"^[a-z0-9._]{1,30}$")
GRUPOS = ("global", "brasil")
CAMPOS_CONTA = "username,name,biography,website,followers_count,follows_count,media_count"
CAMPOS_MIDIA = "timestamp,like_count,comments_count"
DIAS_ATIVA = 45  # conta que não posta há mais que isso não vale o "seguir"

# o corpo do erro da Graph API traz "code":N; estes marcam limite de uso, aqueles conta que não existe/não é profissional
MARCAS_LIMITE = ('"code":4,', '"code":17,', '"code":32,', '"code":613,', "HTTP 429")
MARCAS_INEXISTENTE = ('"code":110', '"code":24,', "invalid user", "does not exist", "not found", "2207013",
                      "unsupported get request")

PAGINA = ("name", "username", "link", "category", "about", "description", "website", "emails", "phone",
          "single_line_address", "hours", "company_overview", "mission", "general_info", "founded",
          "followers_count", "fan_count", "verification_status", "is_published")
INSTAGRAM = ("username", "name", "biography", "website", "followers_count", "follows_count", "media_count")


# ---------------------------------------------------------------- lista de contas


def carregar_lista(caminho: pathlib.Path = LISTA_PADRAO) -> list[dict]:
    """Lê e confere a lista: handle em minúsculas (sem @), sem repetição, grupo e categoria preenchidos."""
    itens = json.loads(caminho.read_text(encoding="utf-8"))
    vistos: set[str] = set()
    for item in itens:
        handle = item.get("handle", "")
        if not HANDLE.match(handle):
            raise ValueError(f"handle inválido na lista: {handle!r}")
        if handle in vistos:
            raise ValueError(f"handle repetido na lista: {handle!r}")
        vistos.add(handle)
        if item.get("grupo") not in GRUPOS or not item.get("nome") or not item.get("categoria"):
            raise ValueError(f"item incompleto na lista: {item!r}")
    return itens


# ---------------------------------------------------------------- consulta


def consultar(creds, handle: str) -> dict:
    """Dados públicos de uma conta profissional (Business Discovery); {} se a Meta não devolver nada."""
    campos = f"business_discovery.username({handle}){{{CAMPOS_CONTA},media.limit(6){{{CAMPOS_MIDIA}}}}}"
    resp = request("GET", f"{config.GRAPH}/{creds.ig_user_id}",
                   params={"fields": campos, "access_token": instagram._token(creds)}, attempts=2)
    return resp.json().get("business_discovery") or {}


def _situacao_do_erro(exc: PublishError) -> str:
    texto = str(exc)
    if any(m in texto for m in MARCAS_LIMITE):
        return "limite"
    if "HTTP 400" in texto and any(m in texto.lower() for m in MARCAS_INEXISTENTE):
        return "não encontrada"   # handle errado ou conta pessoal (a API só mostra contas profissionais)
    return "erro"


def _quando(texto: object) -> dt.datetime | None:
    try:
        return dt.datetime.strptime(str(texto), "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        return None


def resumir(handle: str, dados: dict, agora: dt.datetime) -> dict:
    """O que interessa de uma conta: identidade, tamanho, quando postou por último e média de curtidas."""
    midias = (dados.get("media") or {}).get("data") or []
    datas = sorted((d for d in (_quando(m.get("timestamp")) for m in midias) if d), reverse=True)
    curtidas = [m["like_count"] for m in midias if isinstance(m.get("like_count"), int)]
    dias = (agora - datas[0]).days if datas else None
    return {
        "handle": dados.get("username") or handle,
        "nome_na_conta": dados.get("name") or "",
        "seguidores": dados.get("followers_count"),
        "posts": dados.get("media_count"),
        "site": dados.get("website") or "",
        "bio": " ".join((dados.get("biography") or "").split())[:140],
        "ultimo_post": datas[0].date().isoformat() if datas else "",
        "dias_sem_postar": dias,
        "ativa": dias is not None and dias <= DIAS_ATIVA,
        "curtidas_medias": round(sum(curtidas) / len(curtidas)) if curtidas else None,
    }


def validar(creds, lista: list[dict], pausa: float = PAUSA, agora: dt.datetime | None = None) -> list[dict]:
    """Consulta cada conta. Ao bater no limite de uso da API, para e marca o resto como não consultado."""
    agora = agora or dt.datetime.now(dt.timezone.utc)
    resultados: list[dict] = []
    parou = False
    for item in lista:
        base = {c: item.get(c, "") for c in ("handle", "nome", "grupo", "categoria")}
        if parou:
            resultados.append({**base, "situacao": "não consultada (limite de uso da API)"})
            continue
        try:
            dados = consultar(creds, item["handle"])
        except PublishError as exc:
            situacao = _situacao_do_erro(exc)
            parou = situacao == "limite"
            resultados.append({**base, "situacao": situacao, "erro": redigir(str(exc))[:160]})
        else:
            if dados:
                resultados.append({**base, "situacao": "ok", **resumir(item["handle"], dados, agora)})
            else:
                resultados.append({**base, "situacao": "não encontrada"})
        if not parou:
            time.sleep(pausa)
    return resultados


# ---------------------------------------------------------------- relatório


def relatorio_md(resultados: list[dict], dia: str) -> str:
    """Tabela por categoria (mais seguidores primeiro) e, no fim, o que não foi possível conferir."""
    ok = [r for r in resultados if r["situacao"] == "ok"]
    linhas = [f"# Radar de contas — {dia}", "",
              f"{len(ok)} de {len(resultados)} contas conferidas pela API da Meta (Business Discovery).", ""]
    categorias = dict.fromkeys((r["grupo"], r["categoria"]) for r in resultados)
    for grupo, categoria in categorias:
        do_grupo = sorted((r for r in ok if (r["grupo"], r["categoria"]) == (grupo, categoria)),
                         key=lambda r: r.get("seguidores") or 0, reverse=True)
        if not do_grupo:
            continue
        linhas += [f"## {categoria} ({grupo})", "", "| Conta | Nome na conta | Seguidores | Último post | Ativa |", "|---|---|---|---|---|"]
        for r in do_grupo:
            linhas.append(f"| @{r['handle']} | {r['nome_na_conta']} | {r.get('seguidores') or '—'} | "
                          f"{r.get('ultimo_post') or '—'} | {'sim' if r.get('ativa') else 'não'} |")
        linhas.append("")
    falhas = [r for r in resultados if r["situacao"] != "ok"]
    if falhas:
        linhas += ["## Não conferidas", ""]
        linhas += [f"- @{r['handle']} ({r['nome']}): {r['situacao']}" for r in falhas]
    return "\n".join(linhas) + "\n"


# ---------------------------------------------------------------- diagnóstico dos perfis da TECHDIM


def _campos_um_a_um(obj_id: str, token: str, campos: tuple[str, ...]) -> dict:
    """Um campo por chamada: se a API recusar um (permissão, campo que mudou), os outros ainda saem."""
    lidos: dict = {}
    indisponiveis: list[str] = []
    for campo in campos:
        try:
            valor = request("GET", f"{config.GRAPH}/{obj_id}", params={"fields": campo, "access_token": token},
                            attempts=2).json().get(campo)
        except PublishError:
            indisponiveis.append(campo)
            continue
        if valor not in (None, "", [], {}):
            lidos[campo] = valor
    return {"campos": lidos, "indisponiveis": indisponiveis}


def diagnostico(creds) -> dict:
    """Texto e contadores que a Página do Facebook e o Instagram da TECHDIM exibem agora."""
    saida: dict = {}
    if creds.has_facebook:
        saida["facebook"] = _campos_um_a_um(creds.fb_page_id, page_token(creds.meta_token, creds.fb_page_id), PAGINA)
    if creds.has_instagram:
        saida["instagram"] = _campos_um_a_um(creds.ig_user_id, instagram._token(creds), INSTAGRAM)
    return saida


# ---------------------------------------------------------------- saída


def _gravar(dest: pathlib.Path, nome: str, dia: str, dados: object, texto: str | None = None) -> pathlib.Path:
    pasta = dest / "registros" / "radar"
    pasta.mkdir(parents=True, exist_ok=True)
    caminho = pasta / f"{nome}-{dia}.json"
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if texto is not None:
        (pasta / f"{nome}-{dia}.md").write_text(texto, encoding="utf-8")
    return caminho


def _resumo_validacao(resultados: list[dict]) -> str:
    contagem: dict[str, int] = {}
    for r in resultados:
        contagem[r["situacao"]] = contagem.get(r["situacao"], 0) + 1
    return ", ".join(f"{n} {s}" for s, n in sorted(contagem.items(), key=lambda x: -x[1]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Radar de contas e perfis (só leitura)")
    parser.add_argument("--dest", required=True, type=pathlib.Path, help="onde gravar registros/radar (o branch assets)")
    parser.add_argument("--acao", required=True, choices=("validar-lista", "diagnostico"))
    parser.add_argument("--lista", type=pathlib.Path, default=LISTA_PADRAO)
    parser.add_argument("--pausa", type=float, default=PAUSA, help="segundos entre consultas")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    creds = config.Credentials()
    if not creds.has_instagram:
        print("sem META_ACCESS_TOKEN/IG_USER_ID: nada a consultar", file=sys.stderr)
        return 1
    dia = f"{config.hoje():%Y-%m-%d}"

    if args.acao == "diagnostico":
        dados = diagnostico(creds)
        for rede, bloco in dados.items():
            print(f"== {rede}")
            for campo, valor in bloco["campos"].items():
                print(f"  {campo}: {redigir(json.dumps(valor, ensure_ascii=False))[:300]}")
            if bloco["indisponiveis"]:
                print(f"  (a API não devolveu: {', '.join(bloco['indisponiveis'])})")
        _gravar(args.dest, "diagnostico", dia, dados)
        return 0

    resultados = validar(creds, carregar_lista(args.lista), pausa=args.pausa)
    _gravar(args.dest, f"radar-{args.lista.stem}", dia, resultados, relatorio_md(resultados, dia))   # uma por lista: não sobrescreve
    print(f"validação: {_resumo_validacao(resultados)}")
    for r in resultados:
        if r["situacao"] == "ok":
            print(f"ok      @{r['handle']:<24} {r.get('seguidores') or 0:>10}  {r.get('ultimo_post') or '—':<10}  {r['nome_na_conta'][:40]}")
        else:
            print(f"{r['situacao'][:7]:<7} @{r['handle']:<24} {r['nome']}")
    return 0 if any(r["situacao"] == "ok" for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
