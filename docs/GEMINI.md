# Reserva com o Gemini

Se a Routine do Claude falhar ou for pausada, as publicações continuam: o **Gemini** (API gratuita do Google)
escreve a pauta do tema na hora de publicar, com o mesmo infográfico, e ela passa pelo mesmo `validar_pauta`.

## Camadas, da principal à última

| # | Quem | Quando |
|---|---|---|
| 1 | Routine do Claude: pauta às 07:03 (`content/diario/AAAA-MM-DD/`) e disparo dos 4 posts | 07:03, 07:58, 11:06, 14:22, 17:22 |
| 2 | Cron do GitHub (`publicar.yml`) publica o tema que faltar | 08:07, 11:07, 14:23, 17:23 |
| 3 | **Pauta do Gemini** (`src/pauta_reserva.py`), chamada por `content.build` quando o JSON do dia falta ou reprova | na hora de publicar |
| 4 | **Curadoria do Gemini** (`src/curator.py`) se a chave da Anthropic faltar ou falhar | idem |
| 5 | Filtro por palavra-chave e acervo autoral (`content/dicas.json`, `servicos.json`) | último recurso |

Sem `GEMINI_API_KEY` as camadas 3 e 4 ficam desligadas e o projeto se comporta como antes.

## Como ligar (2 minutos)

1. Crie uma chave em https://aistudio.google.com/apikey (plano gratuito).
2. No GitHub: **Settings → Secrets and variables → Actions → Secrets → New repository secret**, nome
   `GEMINI_API_KEY`. Nunca cole a chave em chat, issue, commit ou workflow input (o repositório é público).
3. Opcional, em **Variables**: `GEMINI_MODEL` com os modelos em ordem de preferência
   (padrão: `gemini-2.5-flash, gemini-flash-lite-latest, gemini-flash-latest, gemini-3.1-flash-lite`).

## Como testar sem publicar

Actions → **Pauta de reserva** → Run workflow, sem marcar "gravar": mostra no log a pauta que o Gemini escreveria
para os temas que faltam (ou para os informados em "temas"). Marcando "gravar", ele grava em `content/diario/` só o
que falta ou reprova (com "forcar" e "temas", sobrescreve). Localmente:

    GEMINI_API_KEY=... PYTHONPATH=src python src/pauta_reserva.py --dia 2026-10-16 --saida /tmp/pauta --gravar
    PYTHONPATH=src python src/validar_pauta.py 2026-10-16        # com a pasta no lugar de content/diario

## Como funciona

- **noticias e hacker:** o Gemini escolhe uma manchete dos feeds RSS (sem repetir os últimos 14 dias), o código baixa
  a matéria e o Gemini escreve só com o texto dela. A fonte citada vem da matéria, nunca do modelo. Se a matéria
  bloquear o download, vale o resumo do feed e o prompt manda não acrescentar detalhes.
- **dica e servico:** o Gemini escreve a partir do acervo e dos assuntos recentes, sem citar fonte externa.
- A resposta segue um esquema JSON (fundos e elementos de cena só dos que existem). Se reprovar no
  `validar_pauta`, tem telefone, cita o domínio fora do ar ou traz comando de shell no terminal do hacker, o Gemini
  recebe os problemas e reescreve (até 2 vezes); se ainda reprovar, a próxima camada assume.
- **Cotas:** o plano gratuito é "melhor esforço" e as cotas mudam sem aviso. O cliente (`src/gemini.py`) troca de
  modelo em 429 (cota) e 404, repete 503 (sobrecarga, comum nos modelos novos) e limita a 16 chamadas por execução.

## Privacidade e riscos

- No plano gratuito a Google pode usar entradas e saídas para melhorar produtos, com revisão humana
  (https://ai.google.dev/gemini-api/terms). Só vão ao Gemini notícias públicas e o acervo da TECHDIM.
- Texto de IA pode errar: o Gemini vê só o material fornecido e o `validar_pauta` barra o que quebra a arte, mas
  confira os posts de reserva (o manifesto e o diário marcam "Gemini (reserva)").
- **Chave exposta em chat deve ser trocada**: crie outra no AI Studio, apague a antiga e atualize o segredo.
