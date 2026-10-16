"""Cliente mínimo do Gemini (API REST) para a reserva de pauta.

Pede resposta em JSON com esquema, repete em erro transitório e passa ao próximo modelo quando o atual está
sem cota ou sobrecarregado: o plano gratuito tem cotas pequenas, que mudam sem aviso, e os modelos novos
ficam indisponíveis por alguns minutos nos picos de demanda. A chave vem de GEMINI_API_KEY e nunca entra em
log nem em mensagem de erro.

  GEMINI_API_KEY        chave do Google AI Studio (sem ela, nada aqui roda e o resto do projeto segue igual)
  GEMINI_MODEL          modelos, em ordem de preferência, separados por vírgula (padrão: MODELOS)
  GEMINI_MAX_CHAMADAS   teto de chamadas por execução (padrão 16), para não estourar a cota do dia

Docs: https://ai.google.dev/gemini-api/docs  ·  preços e cotas: https://ai.google.dev/gemini-api/docs/pricing
"""
from __future__ import annotations

import json
import logging
import os
import re
import time

import requests

log = logging.getLogger(__name__)

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
# Do mais indicado ao último recurso. Os "-latest" acompanham a versão corrente quando um nome é aposentado.
MODELOS = ("gemini-2.5-flash", "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-3.1-flash-lite")
TIMEOUT = (10, 120)  # (conexão, leitura) em segundos
MAX_CHAMADAS = 16      # chamadas que gastam cota (5xx e falha de rede não contam)
MAX_TENTATIVAS = 60    # teto de pedidos HTTP, contando os que falharam
PENSAMENTO = 1024      # tokens de raciocínio nos modelos 2.5 (o padrão deles é bem maior e é lento)
ESPERA_TRANSITORIO = 4  # segundos antes de repetir um 5xx no mesmo modelo

_usadas = 0
_tentativas = 0
_ultimo_modelo = ""
_esgotados: set[str] = set()   # modelos sem cota (429) ou aposentados (404) nesta execução: não insiste neles


class GeminiIndisponivel(RuntimeError):
    """O Gemini não respondeu com algo aproveitável; quem chama segue para a próxima camada de reserva."""


class RespostaCortada(GeminiIndisponivel):
    """A resposta parou no limite de tokens (nos modelos com raciocínio, o raciocínio come o espaço da resposta)."""


def chave() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip()


def disponivel() -> bool:
    return bool(chave())


def modelos() -> list[str]:
    lista = [m.strip() for m in os.environ.get("GEMINI_MODEL", "").split(",") if m.strip()]
    return lista or list(MODELOS)


def chamadas_usadas() -> int:
    return _usadas


def ultimo_modelo() -> str:
    """Modelo que respondeu à última chamada bem-sucedida."""
    return _ultimo_modelo


def zerar_contador() -> None:
    global _usadas, _tentativas
    _usadas = _tentativas = 0
    _esgotados.clear()


def _teto() -> int:
    try:
        return int(os.environ.get("GEMINI_MAX_CHAMADAS", "") or MAX_CHAMADAS)
    except ValueError:
        return MAX_CHAMADAS


def limpar_esquema(esquema):
    """O esquema de resposta do Gemini é um subconjunto do OpenAPI: sem additionalProperties."""
    if isinstance(esquema, dict):
        return {k: limpar_esquema(v) for k, v in esquema.items() if k != "additionalProperties"}
    if isinstance(esquema, list):
        return [limpar_esquema(v) for v in esquema]
    return esquema


def _texto_da_resposta(dados: dict) -> str:
    candidatos = dados.get("candidates") or []
    if not candidatos:
        raise GeminiIndisponivel(f"resposta sem candidatos ({dados.get('promptFeedback') or 'sem detalhe'})")
    cand = candidatos[0]
    fim = cand.get("finishReason")
    if fim == "MAX_TOKENS":
        raise RespostaCortada("resposta interrompida (MAX_TOKENS)")
    if fim not in (None, "STOP"):
        raise GeminiIndisponivel(f"resposta interrompida ({fim})")
    partes = (cand.get("content") or {}).get("parts") or []
    return "".join(p.get("text", "") for p in partes if not p.get("thought"))


def _json(texto: str) -> dict:
    texto = texto.strip()
    if texto.startswith("```"):
        texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto)
    try:
        valor = json.loads(texto)
    except json.JSONDecodeError as exc:
        raise GeminiIndisponivel(f"resposta fora do formato JSON: {exc}") from exc
    if not isinstance(valor, dict):
        raise GeminiIndisponivel("a resposta precisa ser um objeto JSON")
    return valor


def _erro(resp: requests.Response) -> str:
    """Mensagem curta do erro, sem nunca repetir a chave."""
    try:
        msg = (resp.json().get("error") or {}).get("message") or resp.text
    except ValueError:
        msg = resp.text
    texto = f"HTTP {resp.status_code}: {str(msg)[:200]}"
    return texto.replace(chave(), "***") if chave() else texto


def _corpo_do_modelo(corpo: dict, modelo: str) -> dict:
    """Cópia do corpo com o raciocínio limitado nos modelos 2.5 (os demais não aceitam esse campo)."""
    copia = json.loads(json.dumps(corpo))
    if "2.5" in modelo:
        copia["generationConfig"]["thinkingConfig"] = {"thinkingBudget": PENSAMENTO}
    return copia


def gerar_json(prompt: str, esquema: dict, *, sistema: str = "", temperatura: float = 0.6,
               max_tokens: int = 12288, tentativas: int = 2) -> dict:
    """Uma resposta em JSON que obedece ao esquema. Levanta GeminiIndisponivel se nenhum modelo servir."""
    global _usadas, _tentativas, _ultimo_modelo
    if not disponivel():
        raise GeminiIndisponivel("GEMINI_API_KEY não configurada")
    corpo = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperatura,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
            "responseSchema": limpar_esquema(esquema),
        },
    }
    if sistema:
        corpo["systemInstruction"] = {"parts": [{"text": sistema}]}
    cabecalho = {"x-goog-api-key": chave(), "Content-Type": "application/json"}

    ultimo = "nenhum modelo tentado"
    for modelo in modelos():
        if modelo in _esgotados and len(_esgotados) < len(modelos()):
            continue
        pedido = _corpo_do_modelo(corpo, modelo)
        tentativa = 0
        while tentativa < tentativas:
            tentativa += 1
            if _usadas >= _teto() or _tentativas >= MAX_TENTATIVAS:
                raise GeminiIndisponivel(f"limite de chamadas por execução atingido ({_usadas} com cota, {_tentativas} pedidos)")
            _tentativas += 1
            try:
                resp = requests.post(URL.format(modelo=modelo), headers=cabecalho, json=pedido, timeout=TIMEOUT)
            except requests.RequestException as exc:
                ultimo = f"{modelo}: sem resposta ({type(exc).__name__})"
                log.warning("Gemini %s", ultimo)
                break
            if resp.status_code in (500, 502, 503, 504):   # sobrecarga: não gasta cota
                ultimo = f"{modelo}: {_erro(resp)}"
                log.warning("Gemini %s", ultimo)
                if tentativa < tentativas:
                    time.sleep(ESPERA_TRANSITORIO)
                    continue
                break
            _usadas += 1
            if resp.status_code == 200:
                try:
                    valor = _json(_texto_da_resposta(resp.json()))
                except RespostaCortada as exc:
                    ultimo = f"{modelo}: {exc}"
                    log.warning("Gemini %s", ultimo)
                    cfg = pedido["generationConfig"].get("thinkingConfig")
                    if cfg and cfg.get("thinkingBudget"):   # tenta de novo sem raciocínio antes de trocar de modelo
                        cfg["thinkingBudget"] = 0
                        tentativa -= 1
                        continue
                    break
                except GeminiIndisponivel as exc:
                    ultimo = f"{modelo}: {exc}"
                    log.warning("Gemini %s", ultimo)
                    break
                _ultimo_modelo = modelo
                return valor
            ultimo = f"{modelo}: {_erro(resp)}"
            log.warning("Gemini %s", ultimo)
            if resp.status_code in (401, 403):
                raise GeminiIndisponivel(f"a chave não foi aceita ({_erro(resp)})")
            if resp.status_code == 400:
                raise GeminiIndisponivel(f"pedido recusado ({_erro(resp)})")
            if resp.status_code in (404, 429):
                _esgotados.add(modelo)
            break   # 404 (modelo aposentado) ou 429 (cota): próximo modelo
    raise GeminiIndisponivel(f"nenhum modelo respondeu ({ultimo})")
