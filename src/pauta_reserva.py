"""Pauta de reserva com o Gemini: o que a Routine do Claude escreve às 07:03, feito pela API gratuita do Google.

Entra quando o arquivo content/diario/AAAA-MM-DD/<tema>.json não existe ou não passa no validar_pauta: o
publicador chama gerar_item() na hora de publicar (content.build) e o workflow "Pauta de reserva" pode gravar os
arquivos antes. Sem GEMINI_API_KEY nada disso roda e o projeto segue como antes.

  noticias e hacker  escolhem uma manchete real (RSS), leem a matéria e escrevem só com o que ela diz;
  dica e servico     escrevem a partir do acervo da TECHDIM e dos assuntos já usados, sem citar fonte externa.

O resultado é o mesmo JSON da Routine (título, pontos, fecho e bloco "infografico") e passa pelo mesmo
validar_pauta; se reprovar, o Gemini recebe os problemas e reescreve (até 2 vezes).

  python src/pauta_reserva.py [--dia AAAA-MM-DD] [--tema noticias ...] [--gravar] [--saida PASTA] [--forcar]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import pathlib
import re
import sys

import config
import content
import curator
import gemini
import infografico
import validar_pauta
from cenas import ELEMENTOS, FUNDOS
from content import FEEDS, PAUTA

log = logging.getLogger("pauta_reserva")

REPAROS = 2          # reescritas pedidas ao Gemini depois da primeira tentativa
MANCHETES = 20       # candidatas enviadas ao Gemini na escolha
DIAS_RECENTES = 14   # assuntos dos últimos dias, para não repetir
TELEFONE = re.compile(r"\(?\b\d{2}\)?[\s.-]?9?\d{4}[\s.-]?\d{4}\b")
# o terminal do hacker descreve ações; comando real inventado (ou perigoso) não pode ir ao ar
COMANDO = re.compile(r"&&|\|\||\bsudo\b|\bapt(-get)?\b|\byum\b|\brm\b|\bchmod\b|\bcurl\b|\bwget\b|\bnmap\b|\bpowershell\b|\s--?\w{2,}")

FOCO = {
    "noticias": "tecnologia e inteligência artificial com impacto em empresas brasileiras "
                "(nuvem, IA corporativa, infraestrutura, software empresarial, regulação de tecnologia)",
    "hacker": "segurança da informação: ataques, vulnerabilidades exploradas, vazamentos, ransomware, "
              "alertas de fabricantes e de órgãos de segurança, relevantes para empresas brasileiras",
    "dica": "ensino prático, passo a passo, para pequenas e médias empresas (segurança, backup, rede, "
            "produtividade, LGPD, IA segura, hardening, phishing, atualizações, senhas)",
    "servico": "propaganda de UM serviço da TECHDIM (infraestrutura e redes; segurança e hardening; backup; "
               "suporte de TI; LGPD; automação com IA; software sob medida)",
}

SISTEMA = f"""Você é o editor de conteúdo da TECHDIM, empresa de infraestrutura de TI, cibersegurança defensiva, \
automação com IA e software sob medida de Campinas-SP. O público é dono de pequena e média empresa e gestor de TI no Brasil.

Regras:
- Escreva em português do Brasil, com tom profissional e direto, sem sensacionalismo nem alarmismo.
- Use somente fatos do material fornecido (nas dicas e nos serviços, só conhecimento consolidado e verificável). \
Não invente números, nomes, datas, CVEs, versões, comandos, citações nem resultados. Preserve as ressalvas do original ("pode", "segundo a empresa").
- Nunca inclua telefone nem e-mail. O único contato é o site {config.SITE}; não cite {config.SITE_FORA_DO_AR}.
- Nunca diga que a TECHDIM é parceira ou revendedora oficial de outra empresa.
- Sem preço, prazo ou resultado garantido.
- Respeite os limites de tamanho de cada campo: texto maior estoura a arte."""

EXEMPLO_BLOCO = """Exemplo do estilo do bloco "infografico" (assunto: backup):
titulo_branco: "Backup que ninguém restaurou"
titulo_destaque: "é extintor sem teste."
historia: "Ter backup não é o mesmo que conseguir voltar. Só a restauração testada mostra se os dados voltam."
licoes: [["Defina o essencial", "Liste sistemas e dados críticos."], ["Copie fora do local", "Mantenha cópias em nuvem ou em outro lugar."], ["Teste a restauração", "Restaure arquivos de verdade em intervalos fixos."]]
pergunta: "Quando foi a última vez que você restaurou um backup?"
hashtags: ["#Backup", "#Continuidade", "#TI", "#TECHDIM"]"""


class ReservaIndisponivel(RuntimeError):
    """Não deu para escrever a pauta com o Gemini; quem chama usa a próxima camada de reserva."""


# ---------------------------------------------------------------- o que já foi publicado


def _palavras(texto: str) -> set[str]:
    return {p for p in re.findall(r"[a-zà-ú0-9]+", texto.lower()) if len(p) > 3}


def titulos_recentes(dia: dt.date, dias: int = DIAS_RECENTES, base: pathlib.Path | None = None) -> list[str]:
    """Títulos dos últimos dias (pauta do diário e destaques), do mais novo ao mais antigo."""
    raiz = base or content.CONTENT_DIR
    achados: list[tuple[str, str]] = []
    for pasta in ("diario", "destaques"):
        for arq in (raiz / pasta).glob("*/*.json" if pasta == "diario" else "*.json"):
            data = arq.parent.name if pasta == "diario" else arq.stem
            if not (dia - dt.timedelta(days=dias)).isoformat() <= data < dia.isoformat():
                continue
            try:
                titulo = json.loads(arq.read_text(encoding="utf-8")).get("titulo", "")
            except (json.JSONDecodeError, OSError):
                continue
            if isinstance(titulo, str) and titulo.strip():
                achados.append((data, titulo.strip()))
    return [t for _, t in sorted(achados, reverse=True)]


def _repetida(titulo: str, recentes: list[str]) -> bool:
    a = _palavras(titulo)
    return any(a and len(a & _palavras(r)) / len(a | _palavras(r)) >= 0.5 for r in recentes)


# ---------------------------------------------------------------- esquema da resposta


def esquema_post(tema: str) -> dict:
    texto = {"type": "string"}
    licao = {"type": "array", "items": texto, "minItems": 2, "maxItems": 2}
    bloco: dict = {
        "titulo_branco": {**texto, "description": "primeira parte do título, até 55 caracteres"},
        "titulo_destaque": {**texto, "description": "segunda parte, em destaque, até 35 caracteres"},
        "historia": {**texto, "description": "contexto ou analogia, até 230 caracteres"},
        "licoes": {"type": "array", "items": licao, "minItems": 3, "maxItems": 3,
                   "description": "3 pares [título até 22 caracteres, texto até 110 caracteres]"},
        "pergunta": {**texto, "description": "pergunta final ao leitor, até 80 caracteres"},
        "hashtags": {"type": "array", "items": texto, "minItems": 4, "maxItems": 5,
                     "description": "CamelCase, sem acento: 2 a 3 do assunto, #TI e #TECHDIM"},
    }
    obrigatorios = ["titulo_branco", "titulo_destaque", "historia", "licoes", "pergunta", "hashtags"]
    if tema == "hacker":
        bloco["cena"] = {"type": "string", "enum": ["painel"]}
        bloco["terminal_titulo"] = {**texto, "description": "título da janela de terminal, até 40 caracteres"}
        bloco["terminal"] = {
            "type": "array", "minItems": 4, "maxItems": 8,
            "items": {"type": "array", "items": texto, "minItems": 3, "maxItems": 3},
            "description": "linhas [prefixo, texto até 46 caracteres, cor], em português corrido; cor: cmd (ação a tomar), "
                           "ok (correção), risco (problema) ou txt; prefixo '$ ' nas ações e '' nas demais. "
                           "As linhas DESCREVEM ações (ex.: '$ aplicar a atualização do fabricante'), com acentuação normal; nunca escreva comandos reais",
        }
        obrigatorios += ["cena", "terminal_titulo", "terminal"]
    else:
        bloco["cena_composta"] = {
            "type": "object",
            "properties": {
                "fundo": {**texto, "enum": list(FUNDOS)},
                "elementos": {"type": "array", "items": {**texto, "enum": list(ELEMENTOS)}, "minItems": 1, "maxItems": 4},
                "legenda": {**texto, "description": "até 45 caracteres, em maiúsculas"},
            },
            "required": ["fundo", "elementos", "legenda"],
        }
        obrigatorios.append("cena_composta")
    return {
        "type": "object",
        "properties": {
            "titulo": {**texto, "description": "manchete específica, até 90 caracteres, com a palavra-chave do assunto no começo"},
            "pontos": {"type": "array", "items": texto, "minItems": 3, "maxItems": 3,
                       "description": "3 pontos de até 170 caracteres; o primeiro traz o fato principal"},
            "fecho": {**texto, "description": "frase ligando o assunto ao trabalho da TECHDIM, até 130 caracteres"},
            "motivo": {**texto, "description": "uma frase: por que este assunto hoje"},
            "infografico": {"type": "object", "properties": bloco, "required": obrigatorios},
        },
        "required": ["titulo", "pontos", "fecho", "motivo", "infografico"],
    }


ESQUEMA_ESCOLHA = {
    "type": "object",
    "properties": {"indice": {"type": "integer", "description": "índice da manchete escolhida, ou -1 se nenhuma serve"},
                   "motivo": {"type": "string"}},
    "required": ["indice", "motivo"],
}


# ---------------------------------------------------------------- verificação

_TAMANHO = re.compile(r"(\d+) caracteres \(recomendado até (\d+)\)")


def _grave(aviso: str) -> bool:
    """Aviso de tamanho com mais de 15% de excesso: a arte aperta e vale pedir reescrita. Pouco acima, só avisa."""
    m = _TAMANHO.search(aviso)
    return bool(m) and int(m.group(1)) > 1.15 * int(m.group(2))


def verificar_item(tema: str, item: dict, estrito: bool = True) -> tuple[list[str], list[str]]:
    """(problemas, avisos) de uma pauta, com as regras do validar_pauta; estrito acrescenta telefone e terminal do hacker."""
    problemas: list[str] = []
    try:
        content._post_do_json(tema, item)
    except ValueError as exc:
        return [f"arquivo inválido: {exc}"], []
    if validar_pauta.cita_dominio_fora_do_ar(item):
        problemas.append(f"cita {config.SITE_FORA_DO_AR}, que está fora do ar; divulgue só {config.SITE}")
    if estrito and any(TELEFONE.search(t) for t in validar_pauta._textos(item)):
        problemas.append("cita telefone; o único contato é o site")
    bloco = item.get("infografico")
    if bloco is None:
        problemas.append("falta o bloco infografico")
    else:
        try:
            p = infografico.validar(bloco, tema)
        except infografico.InfograficoInvalido as exc:
            problemas.append(f"bloco infografico inválido: {exc}")
        else:
            if estrito and tema == "hacker" and (p["cena"] != "painel" or len(p.get("terminal", [])) < 3):
                problemas.append("o tema hacker precisa de cena 'painel' com ao menos 3 linhas de terminal")
            if estrito and any(COMANDO.search(linha[1]) for linha in p.get("terminal", [])):
                problemas.append("o terminal tem comando real; escreva só a descrição da ação, em português")
            if p["cena"] == "composta" and (bloco.get("cena_composta") or {}).get("elementos") != p["cena_composta"]["elementos"]:
                problemas.append("a cena tem elementos que não existem; use só os permitidos")
    return problemas, validar_pauta._avisos_de_tamanho(item)


# ---------------------------------------------------------------- escrita


def _prompt_noticia(tema: str, manchete: dict, materia: str, recentes: list[str]) -> str:
    return (
        f"Escreva o post do tema \"{tema}\" para a TECHDIM a partir desta matéria. Foco: {FOCO[tema]}.\n\n"
        f"Manchete original: {manchete['title']}\nFonte: {manchete['source']}\n\n"
        f"Texto da matéria (a única fonte de fatos):\n{materia}\n\n"
        f"Assuntos já publicados nos últimos dias (não repita): {'; '.join(recentes[:40]) or 'nenhum'}.\n\n"
        + ("O texto acima é curto: escreva só o que ele afirma, sem acrescentar detalhes, números, versões ou nomes.\n\n"
           if len(materia) < 600 else "")
        + "Escolha uma cena que combine com o assunto e escreva todos os campos do esquema.\n\n" + EXEMPLO_BLOCO
    )


def _prompt_autoral(tema: str, ideias: list[str], recentes: list[str], dia: dt.date) -> str:
    return (
        f"Escreva o post do tema \"{tema}\" de hoje ({dia:%d/%m/%Y}). Foco: {FOCO[tema]}.\n\n"
        f"Assuntos do acervo da TECHDIM (inspiração; pode combinar ou ir além): {'; '.join(ideias)}.\n"
        f"Assuntos já publicados nos últimos dias (não repita assunto, analogia nem cena): {'; '.join(recentes[:40]) or 'nenhum'}.\n\n"
        + ("Ensine algo prático e verificável, que o leitor consiga fazer hoje. Prefira uma analogia do dia a dia da empresa.\n"
           if tema == "dica" else
           "Mostre o problema do dia a dia da empresa e como a TECHDIM resolve; convide a pedir um diagnóstico. "
           "Sem preço, prazo ou resultado garantido.\n")
        + "\nEscolha uma cena que combine com o assunto e escreva todos os campos do esquema.\n\n" + EXEMPLO_BLOCO
    )


def _escolher_manchete(tema: str, candidatas: list[dict]) -> dict:
    lista = "\n".join(f"[{i}] {c['title']} ({c['source']})\n    {c['summary']}" for i, c in enumerate(candidatas))
    escolha = gemini.gerar_json(
        f"Foco do post: {FOCO[tema]}.\n\nEscolha a manchete mais relevante e útil para empresas brasileiras que dependem de TI. "
        "Descarte consumo pessoal, games, celulares, entretenimento, política e promoções. Prefira fontes em português quando "
        f"a relevância for parecida. Se nenhuma servir, devolva indice -1.\n\nManchetes de hoje:\n{lista}",
        ESQUEMA_ESCOLHA, sistema=SISTEMA, temperatura=0.2, max_tokens=1024)
    i = escolha.get("indice")
    if not isinstance(i, int) or not 0 <= i < len(candidatas):
        raise ReservaIndisponivel(f"nenhuma manchete serviu ({escolha.get('motivo', 'sem motivo')})")
    return candidatas[i]


def _candidatas(tema: str, recentes: list[str]) -> list[dict]:
    achadas = [e for e in content._fetch_entries(FEEDS[tema])
               if not any(ruim in f"{e['title']} {e['summary']}".lower() for ruim in content.BLOCK)
               and not _repetida(e["title"], recentes)]
    return achadas[:MANCHETES]


def _normalizar(tema: str, item: dict, fonte: tuple[str, str] | None) -> dict:
    """Só os campos da pauta, com a fonte citada vinda do material e as hashtags obrigatórias."""
    bloco = dict(item.get("infografico") or {})
    tags = [t for t in bloco.get("hashtags", []) if isinstance(t, str)]
    for obrigatoria in ("#TI", "#TECHDIM"):
        if obrigatoria.lower() not in [t.lower() for t in tags]:
            tags.append(obrigatoria)
    bloco["hashtags"] = tags
    if isinstance(bloco.get("terminal"), list):   # o prefixo de ação é "$ " (com espaço), como nas pautas do Claude
        bloco["terminal"] = [[("$ " if str(linha[0]).strip() == "$" else linha[0]), *linha[1:]] if isinstance(linha, list) and linha else linha
                             for linha in bloco["terminal"]]
    return {
        "titulo": item.get("titulo", ""),
        "pontos": item.get("pontos", []),
        "fecho": item.get("fecho", ""),
        "motivo": item.get("motivo", ""),
        "fontes": [list(fonte)] if fonte else [],
        "infografico": bloco,
        "gerado_por": f"gemini ({gemini.ultimo_modelo() or 'modelo não informado'}), pauta de reserva",
    }


def gerar_item(tema: str, dia: dt.date, *, recentes: list[str] | None = None) -> dict:
    """A pauta de um tema, validada. Levanta ReservaIndisponivel se o Gemini não entregar algo que passe."""
    if tema not in PAUTA:
        raise ReservaIndisponivel(f"tema sem pauta de reserva: {tema}")
    if not gemini.disponivel():
        raise ReservaIndisponivel("GEMINI_API_KEY não configurada")
    recentes = titulos_recentes(dia) if recentes is None else recentes
    esquema = esquema_post(tema)
    try:
        if tema in FEEDS:
            candidatas = _candidatas(tema, recentes)
            if not candidatas:
                raise ReservaIndisponivel("nenhuma manchete recente disponível nos feeds")
            manchete = _escolher_manchete(tema, candidatas)
            log.info("Gemini escolheu: %s (%s)", manchete["title"], manchete["source"])
            materia = curator._texto_da_materia(manchete["link"]) or manchete["summary"]
            prompt = _prompt_noticia(tema, manchete, materia, recentes)
            fonte = (manchete["source"], manchete["link"])
        else:
            pool = "dicas.json" if tema == "dica" else "servicos.json"
            ideias = [x["titulo"] for x in json.loads((content.CONTENT_DIR / pool).read_text(encoding="utf-8"))]
            prompt = _prompt_autoral(tema, ideias, recentes, dia)
            fonte = None

        item = _normalizar(tema, gemini.gerar_json(prompt, esquema, sistema=SISTEMA), fonte)
        for tentativa in range(REPAROS + 1):
            problemas, avisos = verificar_item(tema, item)
            graves = [a for a in avisos if _grave(a)]
            if not problemas and not graves:
                if avisos:
                    log.info("pauta de %s com avisos leves de tamanho: %s", tema, "; ".join(avisos))
                return item
            if tentativa == REPAROS:
                if problemas:
                    raise ReservaIndisponivel("a pauta do Gemini ainda reprova: " + "; ".join(problemas))
                log.warning("pauta de %s com avisos de tamanho que sobraram: %s", tema, "; ".join(graves))
                return item
            log.info("pauta de %s precisa de ajuste (%d problema(s), %d aviso(s) grave(s)); pedindo reescrita",
                     tema, len(problemas), len(graves))
            pedido = (f"Corrija a pauta abaixo e devolva o JSON completo. Problemas: {'; '.join(problemas) or 'nenhum'}. "
                      f"Textos grandes demais (reduza): {'; '.join(graves) or 'nenhum'}.\n\n"
                      + json.dumps({k: v for k, v in item.items() if k not in ("fontes", "gerado_por")}, ensure_ascii=False))
            item = _normalizar(tema, gemini.gerar_json(pedido, esquema, sistema=SISTEMA), fonte)
    except gemini.GeminiIndisponivel as exc:
        raise ReservaIndisponivel(f"Gemini indisponível: {exc}") from exc
    raise ReservaIndisponivel("a pauta do Gemini não ficou pronta")


# ---------------------------------------------------------------- o que falta no dia


def precisa(tema: str, dia: dt.date, pasta: pathlib.Path | None = None) -> str:
    """Motivo pelo qual o tema precisa da reserva, ou "" se a pauta do dia está de pé."""
    arq = (pasta or content.CONTENT_DIR / "diario") / dia.isoformat() / f"{tema}.json"
    if not arq.exists():
        return "sem arquivo"
    try:
        item = json.loads(arq.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return f"JSON inválido ({exc})"
    problemas, _ = verificar_item(tema, item, estrito=False)
    return "; ".join(problemas)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pauta de reserva com o Gemini")
    ap.add_argument("--dia", default="", help="AAAA-MM-DD (padrão: hoje, em Brasília)")
    ap.add_argument("--tema", action="append", choices=PAUTA, help="só estes temas (padrão: os que faltam ou reprovam)")
    ap.add_argument("--forcar", action="store_true", help="gera mesmo que a pauta do dia esteja de pé (nunca sobrescreve sem --gravar)")
    ap.add_argument("--gravar", action="store_true", help="grava os arquivos; sem isso é só ensaio")
    ap.add_argument("--saida", type=pathlib.Path, default=None, help="pasta de destino (padrão: content/diario)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    dia = dt.date.fromisoformat(args.dia) if args.dia else config.hoje()
    destino = (args.saida or content.CONTENT_DIR / "diario") / dia.isoformat()
    if not gemini.disponivel():
        print("sem GEMINI_API_KEY: a reserva com Gemini está desligada (nada a fazer)")
        return 0

    pendentes = []
    for tema in args.tema or PAUTA:
        motivo = "forçado" if args.forcar else precisa(tema, dia, args.saida)
        if motivo:
            pendentes.append((tema, motivo))
        else:
            print(f"{tema}: pauta de {dia} de pé, nada a fazer")
    falhas = 0
    for tema, motivo in pendentes:
        print(f"{tema}: reserva necessária ({motivo})")
        try:
            item = gerar_item(tema, dia)
        except ReservaIndisponivel as exc:
            print(f"{tema}: FALHOU — {exc}")
            falhas += 1
            continue
        if args.gravar:
            destino.mkdir(parents=True, exist_ok=True)
            (destino / f"{tema}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"{tema}: gravado em {destino / (tema + '.json')} — {item['titulo']}")
        else:
            print(f"{tema}: ensaio ok — {item['titulo']}\n{json.dumps(item, ensure_ascii=False, indent=2)}")
    print(f"chamadas ao Gemini: {gemini.chamadas_usadas()}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
