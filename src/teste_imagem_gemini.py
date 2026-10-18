"""Teste: gera uma imagem com a API do Gemini a partir de uma notícia da pauta.

Roda no GitHub Actions (.github/workflows/teste-imagem-gemini.yml), onde existe o segredo GEMINI_API_KEY.
A chave vai só no cabeçalho do pedido: não entra em log nem no resultado. Grava em teste-gemini/ a imagem
e resultado.json com o que cada modelo respondeu (é assim que se sabe se o plano libera imagem).

  python3 src/teste_imagem_gemini.py [AAAA-MM-DD] [tema]   (padrão: último dia da pauta, tema noticias)
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
MODELOS = ("gemini-2.5-flash-image", "gemini-3-pro-image-preview", "gemini-2.5-flash-image-preview")
SAIDA = pathlib.Path("teste-gemini")
DIARIO = pathlib.Path("content/diario")


def prompt_da_noticia(post: dict) -> str:
    pontos = " ".join(post.get("pontos", [])[:2])
    return (
        "Crie uma ilustração editorial, sem texto, para a capa de uma notícia no blog de uma empresa brasileira "
        "de cibersegurança e TI (TECHDIM).\n"
        f"Notícia: {post['titulo']}\n"
        f"Fatos: {pontos}\n"
        "Mostre a ideia central da notícia de forma visual e clara para donos de pequenas empresas. "
        "Estilo TECHDIM: fundo azul-marinho quase preto, luzes neon ciano (#00F0FF) e magenta, ar de centro de "
        "operações de rede, iluminação cinematográfica, alto detalhe, composição horizontal 16:9. "
        "Não use logotipos de empresas reais, bandeiras, rostos de pessoas reais nem letras ou números legíveis."
    )


def pedir(modelo: str, prompt: str, chave: str, com_proporcao: bool) -> requests.Response:
    config: dict = {"responseModalities": ["TEXT", "IMAGE"]}
    if com_proporcao:
        config["imageConfig"] = {"aspectRatio": "16:9"}
    corpo = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}
    return requests.post(URL.format(modelo=modelo), headers={"x-goog-api-key": chave}, json=corpo, timeout=(10, 180))


def erro(resp: requests.Response) -> str:
    """Mensagem e, em erro de cota, qual métrica/limite estourou (não contém a chave)."""
    try:
        e = resp.json().get("error", {})
    except ValueError:
        return resp.text[:300]
    cotas = [f"{v.get('quotaId', '')} ({v.get('quotaValue', '?')})"
             for d in e.get("details", []) for v in d.get("violations", []) if v.get("quotaId")]
    msg = str(e.get("message", "")).split("\n")[0][:200]
    return msg + (" | cotas: " + "; ".join(cotas) if cotas else "")


def main() -> int:
    dia = sys.argv[1] if len(sys.argv) > 1 else sorted(p.name for p in DIARIO.iterdir() if p.is_dir())[-1]
    tema = sys.argv[2] if len(sys.argv) > 2 else "noticias"
    post = json.loads((DIARIO / dia / f"{tema}.json").read_text(encoding="utf-8"))
    prompt = prompt_da_noticia(post)
    SAIDA.mkdir(exist_ok=True)
    resultado = {"dia": dia, "tema": tema, "noticia": post["titulo"], "fontes": post.get("fontes", []),
                 "prompt": prompt, "tentativas": [], "imagem": None}

    chave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not chave:
        resultado["tentativas"].append({"modelo": "-", "status": "sem GEMINI_API_KEY no ambiente"})
    for modelo in MODELOS if chave else ():
        resp = pedir(modelo, prompt, chave, com_proporcao=True)
        if resp.status_code == 400 and "imageConfig" in erro(resp):
            resp = pedir(modelo, prompt, chave, com_proporcao=False)
        tentativa = {"modelo": modelo, "status": resp.status_code}
        if resp.ok:
            partes = (resp.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
            imagens = [p["inlineData"] for p in partes if "inlineData" in p]
            textos = [p["text"] for p in partes if "text" in p]
            if textos:
                tentativa["texto"] = " ".join(textos)[:300]
            if imagens:
                ext = "png" if "png" in imagens[0].get("mimeType", "") else "jpg"
                arquivo = SAIDA / f"imagem-{dia}-{tema}.{ext}"
                arquivo.write_bytes(base64.b64decode(imagens[0]["data"]))
                resultado["imagem"] = arquivo.name
                tentativa["imagem"] = arquivo.name
                resultado["tentativas"].append(tentativa)
                break
            tentativa["erro"] = "resposta sem imagem"
        else:
            tentativa["erro"] = erro(resp)
        resultado["tentativas"].append(tentativa)

    (SAIDA / "resultado.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
    for t in resultado["tentativas"]:
        print(t.get("modelo"), t.get("status"), t.get("imagem") or t.get("erro", ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
