"""Orquestrador. Roda em duas fases dentro do mesmo job do GitHub Actions:

    generate  — monta o conteúdo, renderiza as imagens e grava o manifesto
    publish   — lê o manifesto e publica nas redes

Entre as duas, o workflow faz commit das imagens no branch de assets, para que
elas tenham URL pública (o Instagram exige buscar a imagem por URL).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import pathlib
import sys

import config
import content
import movimentos
import registro
import render
from publishers import facebook, instagram, linkedin
from publishers.common import PublishError, redact

log = logging.getLogger("techdim")

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
MANIFEST = OUT / "manifest.json"
RESULTADO = OUT / "resultado.json"


def _today() -> dt.date:
    """Data no fuso de São Paulo (o runner do GitHub roda em UTC)."""
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date()


# ---------------------------------------------------------------- generate


def _curadoria(post) -> str:
    if getattr(post, "origem", "") == "routine":
        return "Claude (Routine) — pauta do dia"
    if post.theme == "especial":
        return "publicação especial, escrita sob demanda"
    if post.theme == "destaque":
        return "Claude (Routine) — notícia pesquisada e conferida em 2 fontes"
    if post.curado_por_ia:
        return "IA (API da Anthropic)"
    if post.theme in ("dica", "servico"):
        return "acervo autoral"
    return "filtro por palavra-chave"


def generate(theme: str, networks: list[str]) -> dict:
    today = _today()
    post = content.build(theme, today)
    log.info("tema=%s titulo=%r curadoria=%s", theme, post.titulo, _curadoria(post))

    stamp = today.isoformat()
    manifest = {
        "theme": theme,
        "date": stamp,
        "titulo": post.titulo,
        "curadoria": _curadoria(post),
        "motivo": post.motivo,
        "fontes": [list(f) for f in post.fontes],
        "networks": {},
    }

    for network in networks:
        rel_dir = pathlib.Path("posts") / stamp / theme / network
        paths = render.render_post(post, network, OUT / rel_dir, seed=today.toordinal())
        manifest["networks"][network] = {
            "caption": post.caption(network),
            "comentario": post.comentario(network),
            "files": [str(rel_dir / p.name) for p in paths],
        }
        log.info("%s: %d imagem(ns)", network, len(paths))

    OUT.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), "utf-8")
    return manifest


# ---------------------------------------------------------------- publish


def publish(creds: config.Credentials) -> int:
    if not MANIFEST.exists():
        log.error("manifesto ausente — a fase generate não rodou")
        return 1

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    base = creds.asset_base_url.rstrip("/")
    falhas: list[str] = []
    sucessos: list[str] = []
    sem_credencial: list[str] = []
    resultados: dict[str, dict] = {}
    segredos = (creds.meta_token, creds.linkedin_token)

    for network, data in manifest["networks"].items():
        caption = data["caption"]
        files = [pathlib.Path(f) for f in data["files"]]
        urls = [f"{base}/{f.as_posix()}" for f in files]
        local = [OUT / f for f in files]

        try:
            if network == "facebook":
                if not creds.has_facebook:
                    log.warning("Facebook: não configurado, pulando")
                    sem_credencial.append("facebook")
                    continue
                if not base:
                    raise PublishError("ASSET_BASE_URL não definido")
                ident = facebook.publish(creds, caption, urls)

            elif network == "instagram":
                if not creds.has_instagram:
                    log.warning("Instagram: não configurado, pulando")
                    sem_credencial.append("instagram")
                    continue
                if not base:
                    raise PublishError("ASSET_BASE_URL não definido")
                ident = instagram.publish(creds, caption, urls)

            elif network == "instagram_stories":
                if not creds.has_instagram:
                    log.warning("Instagram Stories: não configurado, pulando")
                    sem_credencial.append("instagram_stories")
                    continue
                if not base:
                    raise PublishError("ASSET_BASE_URL não definido")
                ident = instagram.publish_story(creds, urls[0])

            elif network == "linkedin":
                if not creds.has_linkedin:
                    log.warning("LinkedIn: não configurado, pulando")
                    sem_credencial.append("linkedin")
                    continue
                ident = linkedin.publish(creds, caption, local, alt=manifest["titulo"])

            else:
                log.warning("rede desconhecida: %s", network)
                continue

        except PublishError as exc:
            log.error("%s falhou: %s", network, exc)
            falhas.append(f"{network}: {exc}")
            resultados[network] = {"status": "falhou", "erro": redact(str(exc), *segredos)[:300]}
        except Exception as exc:  # não deixa uma rede derrubar as outras
            log.exception("%s falhou com erro inesperado", network)
            falhas.append(f"{network}: {exc}")
            resultados[network] = {"status": "falhou", "erro": redact(str(exc), *segredos)[:300]}
        else:
            sucessos.append(f"{network} ({ident})")
            resultados[network] = {
                "status": "publicado", "id": ident, "link": _link(network, creds, ident),
            }
            if data.get("comentario"):
                resultados[network]["comentario"] = _comentar(
                    network, creds, ident, data["comentario"], segredos
                )

    for rede in sem_credencial:
        resultados[rede] = {"status": "não configurado"}
    OUT.mkdir(parents=True, exist_ok=True)
    RESULTADO.write_text(
        json.dumps({"redes": resultados}, ensure_ascii=False, indent=2), "utf-8"
    )

    # Rede nunca configurada (ex.: LinkedIn sem token) não é falha: senão todo
    # dia o job ficaria vermelho e o vermelho deixaria de significar algo.
    # Mas nenhuma rede publicada é sempre falha — ver abaixo.
    avisos = [f"{r}: não configurado (pulado)" for r in sem_credencial]
    avisos += [
        f"{r}: primeiro comentário {v['comentario']}"
        for r, v in resultados.items()
        if str(v.get("comentario", "")).startswith("falhou")
    ]

    log.info("publicado em: %s", ", ".join(sucessos) or "nenhuma rede")
    _summary(manifest, sucessos, falhas, avisos)

    if not sucessos:
        # Um job verde sem nenhuma publicação é a pior falha possível: ninguém
        # percebe. Falhar aqui é o que faz o GitHub notificar.
        log.error("NENHUMA rede recebeu a publicação — encerrando com erro")
        return 1

    if falhas:
        log.error("falhas: %s", " | ".join(falhas))
        return 1

    return 0


def _comentar(network: str, creds, ident: str, texto: str, segredos) -> str:
    """Primeiro comentário com fontes e site.

    Falhar aqui não derruba a publicação — o post já está no ar —, mas fica
    registrado e aparece no resumo da execução.
    """
    try:
        if network == "facebook":
            facebook.comment(creds, ident, texto)
        elif network == "instagram":
            instagram.comment(creds, ident, texto)
        elif network == "linkedin":
            linkedin.comment(creds, ident, texto)
        else:
            return ""
    except Exception as exc:
        msg = redact(str(exc), *segredos)[:200]
        log.warning("%s: primeiro comentário falhou: %s", network, msg)
        return f"falhou: {msg}"
    log.info("%s: primeiro comentário publicado", network)
    return "ok"


def _link(network: str, creds, ident: str) -> str:
    """Link público do post; falhar aqui não pode derrubar a publicação."""
    try:
        if network == "facebook":
            return facebook.permalink(creds, ident)
        if network in ("instagram", "instagram_stories"):
            return instagram.permalink(creds, ident)
        if network == "linkedin":
            return linkedin.permalink(ident)
    except Exception as exc:
        log.warning("não consegui o link do post no %s: %s", network, exc)
    return ""


def _summary(
    manifest: dict, sucessos: list[str], falhas: list[str], avisos: list[str] = ()
) -> None:
    """Escreve o resumo no painel do GitHub Actions, se houver."""
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    linhas = [
        f"### {config.THEME_LABELS.get(manifest['theme'], manifest['theme'])}",
        "",
        f"**{manifest['titulo']}** — {manifest['date']} — curadoria: {manifest.get('curadoria', '-')}",
        "",
    ]
    for ok in sucessos:
        linhas.append(f"- ✅ {ok}")
    for erro in falhas:
        linhas.append(f"- ❌ {erro}")
    for aviso in avisos:
        linhas.append(f"- ⚠️ {aviso}")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write("\n".join(linhas) + "\n")


# ---------------------------------------------------------------- cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publicador diário TECHDIM")
    parser.add_argument("phase", choices=["generate", "publish", "preview", "registrar"])
    parser.add_argument("--theme", required=True, choices=list(config.THEME_LABELS))
    parser.add_argument(
        "--networks",
        default="",
        help="lista separada por vírgula; padrão vem de config.THEME_TARGETS",
    )
    parser.add_argument(
        "--dest", default=".", help="registrar: raiz do checkout do branch assets"
    )
    parser.add_argument("--ensaio", action="store_true", help="registrar: execução de teste")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    networks = (
        [n.strip() for n in args.networks.split(",") if n.strip()]
        or config.THEME_TARGETS[args.theme]
    )

    if args.phase in {"generate", "preview"}:
        manifest = generate(args.theme, networks)
        if args.phase == "preview":
            for network, data in manifest["networks"].items():
                print(f"\n===== {network} =====")
                print(data["caption"])
                print("imagens:", *data["files"], sep="\n  ")
        return 0

    if args.phase == "registrar":
        return registrar(pathlib.Path(args.dest), args.theme, args.ensaio)

    return publish(config.Credentials())


def _eventos(theme, manifest, resultado, ensaio, run_url) -> list[dict]:
    """Movimentos desta execução, para o diário do dia."""
    evento = os.environ.get("EVENTO", "")
    origem = {"schedule": "agendamento automático", "workflow_dispatch": "disparo manual"}.get(evento, evento or "execução")
    base = {"tema": config.THEME_LABELS.get(theme, theme), "origem": origem, "link": run_url, "teste": ensaio}
    ev = [{**base, "tipo": "iniciado", "detalhe": "ensaio: nada será publicado" if ensaio else "execução iniciada"}]
    if not manifest:
        return ev + [{**base, "tipo": "falhou", "detalhe": "a geração do conteúdo não terminou"}]
    ev.append({**base, "tipo": "planejado", "link": "",
               "detalhe": f"pauta: {manifest['titulo']} — curadoria: {manifest.get('curadoria', '-')}"})
    redes = resultado.get("redes", {})
    for rede, dados in manifest["networks"].items():
        b = {**base, "rede": rede, "link": ""}
        if ensaio:
            ev.append({**b, "tipo": "ensaio", "detalhe": f"{len(dados['files'])} imagem(ns) geradas; nada publicado"})
            continue
        ev.append({**b, "tipo": "gerado", "detalhe": f"{len(dados['files'])} imagem(ns)"})
        r = redes.get(rede, {})
        st = r.get("status", "não executado")
        if st == "publicado":
            tipo = "story" if rede == "instagram_stories" else "publicado"
            ev.append({**b, "tipo": tipo, "detalhe": f"id {r.get('id', '')}", "link": r.get("link", "")})
            if r.get("comentario") == "ok":
                ev.append({**b, "tipo": "comentou", "detalhe": "primeiro comentário com fontes e site", "link": r.get("link", "")})
            elif str(r.get("comentario", "")).startswith("falhou"):
                ev.append({**b, "tipo": "falhou", "detalhe": f"primeiro comentário: {r['comentario']}"})
        elif st == "falhou":
            ev.append({**b, "tipo": "falhou", "detalhe": r.get("erro", "")})
        else:
            ev.append({**b, "tipo": "pulado", "detalhe": st})
    return ev


def registrar(destino: pathlib.Path, theme: str, ensaio: bool = False) -> int:
    run_url = os.environ.get("RUN_URL", "")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else None
    try:
        resultado = json.loads(RESULTADO.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        resultado = {"redes": {}}  # a publicação não chegou a rodar
    if manifest and not ensaio:
        arquivo = registro.escrever(manifest, resultado, destino, run_url)
        log.info("registro gravado em %s", arquivo.relative_to(destino))
    movimentos.registrar(destino, _eventos(theme, manifest, resultado, ensaio, run_url))
    log.info("movimentos gravados no diário do dia")
    return 0


if __name__ == "__main__":
    sys.exit(main())
