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
import render
from publishers import facebook, instagram, linkedin
from publishers.common import PublishError

log = logging.getLogger("techdim")

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "out"
MANIFEST = OUT / "manifest.json"


def _today() -> dt.date:
    """Data no fuso de São Paulo (o runner do GitHub roda em UTC)."""
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=3)).date()


# ---------------------------------------------------------------- generate


def generate(theme: str, networks: list[str]) -> dict:
    today = _today()
    post = content.build(theme, today)
    log.info("tema=%s titulo=%r", theme, post.titulo)

    stamp = today.isoformat()
    manifest = {
        "theme": theme,
        "date": stamp,
        "titulo": post.titulo,
        "networks": {},
    }

    for network in networks:
        rel_dir = pathlib.Path("posts") / stamp / theme / network
        paths = render.render_post(post, network, OUT / rel_dir, seed=today.toordinal())
        manifest["networks"][network] = {
            "caption": post.caption(network),
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
        except Exception as exc:  # não deixa uma rede derrubar as outras
            log.exception("%s falhou com erro inesperado", network)
            falhas.append(f"{network}: {exc}")
        else:
            sucessos.append(f"{network} ({ident})")

    # Rede nunca configurada (ex.: LinkedIn sem token) não é falha: senão todo
    # dia o job ficaria vermelho e o vermelho deixaria de significar algo.
    # Mas nenhuma rede publicada é sempre falha — ver abaixo.
    avisos = [f"{r}: não configurado (pulado)" for r in sem_credencial]

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
        f"**{manifest['titulo']}** — {manifest['date']}",
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
    parser.add_argument("phase", choices=["generate", "publish", "preview"])
    parser.add_argument("--theme", required=True, choices=list(config.THEME_LABELS))
    parser.add_argument(
        "--networks",
        default="",
        help="lista separada por vírgula; padrão vem de config.THEME_TARGETS",
    )
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

    return publish(config.Credentials())


if __name__ == "__main__":
    sys.exit(main())
