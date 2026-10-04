"""Curadoria de notícias por IA (Claude).

Duas chamadas por post:
  1. escolher, entre as manchetes do dia, a mais relevante para empresas que
     dependem de infraestrutura de TI — ou nenhuma, se nada servir;
  2. ler o texto da matéria escolhida e escrever o post TECHDIM: título,
     dois fatos e uma recomendação prática ("o que sua empresa deve fazer").

O texto do post é escrito só a partir do conteúdo da matéria passado na
chamada, para não inventar fato. Sem ANTHROPIC_API_KEY, ou se qualquer etapa
falhar, quem chama cai no filtro por palavra-chave.
"""
from __future__ import annotations

import html
import json
import logging
import os
import re

import anthropic
import requests

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

Quem lê é dono de empresa de 10 a 200 funcionários, não administrador de sistemas. Ele não sabe o que é CVE, sandbox ou gateway, e não liga para número de versão. Ele quer saber três coisas: isso me afeta? qual o prejuízo se eu ignorar? o que eu faço hoje?

Regras:
- Escreva em português do Brasil, tom profissional e direto, sem sensacionalismo.
- Use somente fatos presentes no material fornecido. Não invente números, nomes, datas ou citações.
- Preserve ressalvas do texto original (por exemplo, "pode ter", "segundo a empresa").
- Traduza o jargão. Em vez de "escapa do sandbox de templates e executa comandos", escreva "o invasor consegue rodar comandos no servidor da empresa".
- Número de versão e código de vulnerabilidade só entram quando o leitor precisa deles para agir, e sempre depois do impacto, nunca antes.
- Diga sempre quem é afetado em palavras do dia a dia ("empresas que usam o Office 365", "quem tem servidor próprio"), para o leitor saber em dois segundos se é com ele.
- Não cite telefone; o único contato é www.techdim.com.br."""

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
        "pergunta": {
            "type": "string",
            "description": "pergunta curta e concreta sobre a realidade da empresa do leitor, "
            "que ele consiga responder em uma linha, até 90 caracteres. Fecha a legenda e "
            "serve para puxar comentário. Nada de pergunta retórica.",
        },
    },
    "required": ["titulo", "fatos", "recomendacao", "fecho", "pergunta"],
    "additionalProperties": False,
}


class CuradoriaIndisponivel(RuntimeError):
    """A curadoria não pôde produzir um post; usar o caminho sem IA."""


def disponivel() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


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


def curar(theme: str, candidatos: list[dict]) -> dict:
    """Devolve {titulo, pontos, fecho, fonte} ou levanta CuradoriaIndisponivel."""
    if not disponivel():
        raise CuradoriaIndisponivel("ANTHROPIC_API_KEY não configurada")
    if not candidatos:
        raise CuradoriaIndisponivel("nenhuma manchete candidata")

    client = anthropic.Anthropic()
    lista = "\n".join(
        f"[{i}] {c['title']} — {c['source']}\n    {c['summary']}" for i, c in enumerate(candidatos)
    )
    try:
        escolha = _chamar(
            client,
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
        log.info("IA escolheu [%d] %s — %s", i, item["title"], escolha["motivo"])

        materia = _texto_da_materia(item["link"]) or item["summary"]
        post = _chamar(
            client,
            ESQUEMA_POST,
            f"Escreva o post da TECHDIM sobre esta matéria.\n\n"
            f"Manchete original: {item['title']}\nFonte: {item['source']}\n\n"
            f"Texto da matéria:\n{materia}",
        )
    except anthropic.APIError as exc:
        raise CuradoriaIndisponivel(f"erro na API da Anthropic: {exc}") from exc
    except (json.JSONDecodeError, KeyError) as exc:
        raise CuradoriaIndisponivel(f"resposta fora do formato: {exc}") from exc

    fatos = [f.strip() for f in post["fatos"] if f.strip()][:2]
    if len(fatos) < 2 or not post["titulo"].strip():
        raise CuradoriaIndisponivel("post incompleto")
    return {
        "titulo": post["titulo"].strip(),
        "pontos": fatos + [post["recomendacao"].strip()],
        "fecho": post["fecho"].strip(),
        "pergunta": post.get("pergunta", "").strip(),
        "fonte": (item["source"], item["link"]),
        "motivo": escolha.get("motivo", ""),
    }
