"""Curadoria de notícias por IA (Claude; o Gemini entra se a chave da Anthropic faltar ou falhar).

Duas chamadas por post:
  1. escolher, entre as manchetes do dia, a mais relevante para empresas que
     dependem de infraestrutura de TI — ou nenhuma, se nada servir;
  2. ler o texto da matéria escolhida e escrever o post TECHDIM: título,
     dois fatos e uma recomendação prática ("o que sua empresa deve fazer").

O texto do post é escrito só a partir do conteúdo da matéria passado na
chamada, para não inventar fato. Provedores, nesta ordem: Claude (ANTHROPIC_API_KEY) e Gemini
(GEMINI_API_KEY, plano gratuito). Sem chave, ou se qualquer etapa falhar nos dois, quem chama
cai no filtro por palavra-chave.
"""
from __future__ import annotations

import html
import json
import logging
import os
import re

import anthropic
import requests

import config
import gemini

log = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
FALLBACK_BETA = "server-side-fallback-2026-07-01"

FOCO = {
    "noticias": "tecnologia e inteligência artificial com impacto em empresas "
    "(nuvem, IA corporativa, infraestrutura, software empresarial, regulação de tecnologia)",
    "hacker": "segurança da informação: ataques, vulnerabilidades exploradas, "
    "vazamentos, ransomware, alertas de fabricantes e órgãos de segurança",
}

SISTEMA = """Você é o editor de conteúdo da TECHDIM, empresa de infraestrutura de TI, \
segurança e automação com IA que atende pequenas e médias empresas em Campinas (SP). \
O público é dono de empresa e gestor de TI no Brasil.

Regras:
- Escreva em português do Brasil, tom profissional e direto, sem sensacionalismo.
- Use somente fatos presentes no material fornecido. Não invente números, nomes, datas ou citações.
- Preserve ressalvas do texto original (por exemplo, "pode ter", "segundo a empresa").
- Não cite telefone; o único contato é """ + config.SITE + "."

ESQUEMA_ESCOLHA = {
    "type": "object",
    "properties": {
        "indice": {"type": "integer", "description": "índice da manchete escolhida, ou -1 se nenhuma serve"},
        "motivo": {"type": "string"},
    },
    "required": ["indice", "motivo"],
    "additionalProperties": False,
}

ESQUEMA_POST = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string", "description": "manchete em português, até 90 caracteres"},
        "fatos": {
            "type": "array",
            "items": {"type": "string", "description": "um fato da matéria, até 160 caracteres"},
            "description": "exatamente 2 itens",
        },
        "recomendacao": {
            "type": "string",
            "description": "o que uma empresa deve fazer diante disso, prático, até 170 caracteres",
        },
        "fecho": {"type": "string", "description": "uma frase ligando o tema ao trabalho da TECHDIM, até 130 caracteres"},
    },
    "required": ["titulo", "fatos", "recomendacao", "fecho"],
    "additionalProperties": False,
}


class CuradoriaIndisponivel(RuntimeError):
    """A curadoria não pôde produzir um post; usar o caminho sem IA."""


def _tem_anthropic() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def disponivel() -> bool:
    return _tem_anthropic() or gemini.disponivel()


def _chamar(client: anthropic.Anthropic, esquema: dict, prompt: str) -> dict:
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=4000,
        betas=[FALLBACK_BETA],
        fallbacks="default",
        output_config={"effort": "medium", "format": {"type": "json_schema", "schema": esquema}},
        system=SISTEMA,
        messages=[{"role": "user", "content": prompt}],
    )
    if resp.stop_reason == "refusal":
        raise CuradoriaIndisponivel("modelo recusou a curadoria")
    if resp.stop_reason == "max_tokens":
        raise CuradoriaIndisponivel("resposta cortada por max_tokens")
    texto = next((b.text for b in resp.content if b.type == "text"), "")
    return json.loads(texto)


_TAG = re.compile(r"<[^>]+>")


def _texto_da_materia(url: str, limite: int = 12000) -> str:
    """Baixa a matéria e devolve só o texto dos parágrafos."""
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0 (TECHDIM bot)"})
        r.raise_for_status()
    except requests.RequestException as exc:
        log.warning("não consegui ler a matéria %s: %s", url, exc)
        return ""
    paragrafos = re.findall(r"<p[^>]*>(.*?)</p>", r.text, flags=re.S | re.I)
    texto = "\n".join(
        re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", p))).strip() for p in paragrafos
    )
    return texto[:limite]


def _curar(theme: str, candidatos: list[dict], chamar, erros_da_api: tuple, provedor: str) -> dict:
    """Escolha da manchete + texto do post, com o provedor dado: chamar(esquema, prompt) -> dict."""
    lista = "\n".join(
        f"[{i}] {c['title']} — {c['source']}\n    {c['summary']}" for i, c in enumerate(candidatos)
    )
    try:
        escolha = chamar(
            ESQUEMA_ESCOLHA,
            f"Foco deste post: {FOCO[theme]}.\n\n"
            "Escolha a manchete mais relevante e útil para empresas brasileiras que dependem de TI. "
            "Descarte consumo pessoal, games, celular, entretenimento, política e promoções. "
            "Prefira fontes em português quando a relevância for parecida. "
            "Se nenhuma servir, devolva indice -1.\n\n"
            f"Manchetes de hoje:\n{lista}",
        )
        i = escolha["indice"]
        if not 0 <= i < len(candidatos):
            raise CuradoriaIndisponivel(f"nenhuma manchete relevante ({escolha['motivo']})")
        item = candidatos[i]
        log.info("IA (%s) escolheu [%d] %s — %s", provedor, i, item["title"], escolha["motivo"])

        materia = _texto_da_materia(item["link"]) or item["summary"]
        post = chamar(
            ESQUEMA_POST,
            f"Escreva o post da TECHDIM sobre esta matéria.\n\n"
            f"Manchete original: {item['title']}\nFonte: {item['source']}\n\n"
            f"Texto da matéria:\n{materia}",
        )
    except erros_da_api as exc:
        raise CuradoriaIndisponivel(f"erro na API do {provedor}: {exc}") from exc
    except (json.JSONDecodeError, KeyError) as exc:
        raise CuradoriaIndisponivel(f"resposta fora do formato: {exc}") from exc

    fatos = [f.strip() for f in post["fatos"] if f.strip()][:2]
    if len(fatos) < 2 or not post["titulo"].strip():
        raise CuradoriaIndisponivel("post incompleto")
    return {
        "titulo": post["titulo"].strip(),
        "pontos": fatos + [post["recomendacao"].strip()],
        "fecho": post["fecho"].strip(),
        "fonte": (item["source"], item["link"]),
        "motivo": escolha.get("motivo", ""),
        "provedor": provedor,
    }


def curar(theme: str, candidatos: list[dict]) -> dict:
    """Devolve {titulo, pontos, fecho, fonte, motivo, provedor} ou levanta CuradoriaIndisponivel.

    Tenta o Claude (se há chave da Anthropic) e, se faltar ou falhar, o Gemini (se há chave)."""
    if not disponivel():
        raise CuradoriaIndisponivel("ANTHROPIC_API_KEY e GEMINI_API_KEY não configuradas")
    if not candidatos:
        raise CuradoriaIndisponivel("nenhuma manchete candidata")

    falhas: list[str] = []
    if _tem_anthropic():
        client = anthropic.Anthropic()
        try:
            return _curar(theme, candidatos, lambda esquema, prompt: _chamar(client, esquema, prompt),
                          (anthropic.APIError,), "Anthropic")
        except CuradoriaIndisponivel as exc:
            falhas.append(f"Claude: {exc}")
    if gemini.disponivel():
        try:
            return _curar(theme, candidatos,
                          lambda esquema, prompt: gemini.gerar_json(prompt, esquema, sistema=SISTEMA, temperatura=0.3, max_tokens=4096),
                          (gemini.GeminiIndisponivel,), "Gemini")
        except CuradoriaIndisponivel as exc:
            falhas.append(f"Gemini: {exc}")
    raise CuradoriaIndisponivel("; ".join(falhas))
