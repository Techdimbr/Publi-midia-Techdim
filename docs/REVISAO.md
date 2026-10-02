# Revisão do código — 02/10/2026

Revisão de todos os módulos e workflows, sem mudar o que o sistema faz. A prova
de que nada visual mudou: 85 imagens geradas antes e depois da refatoração
(infográficos, cenas, arte antiga, Stories) são **idênticas pixel a pixel**; as
únicas diferenças são as hashtags das legendas, que agora incluem as do assunto.

## O que foi encontrado e corrigido

| Risco | Antes | Agora |
|---|---|---|
| Post duplicado | o `cron` atrasado e a Routine podiam publicar o mesmo tema | o diário do dia é consultado: só sai o que ainda não saiu, e só a rede que falhou é repetida |
| Retry duplicando post | timeout ou HTTP 5xx na hora de publicar era repetido às cegas | chamada que cria algo (post, comentário) só repete em 429/503 e falha de conexão |
| Pauta ruim derrubava o horário | bloco `infografico` malformado dava erro na geração | validação: corta texto longo, corrige o que dá, e cai na arte antiga se não der |
| Texto cortado em silêncio | história e títulos longos eram truncados sem aviso | reticências e limites por área; hashtags que não cabem saem |
| Feed RSS lento | `feedparser` esperava sem limite | tempo limite de 5 s (conexão) e 15 s (leitura) |
| Curadoria por IA | erro fora da lista (ex.: parâmetro novo do SDK) derrubava a geração | qualquer erro cai no filtro por palavra-chave |
| Imagem velha no CDN | republicar o mesmo tema no mesmo dia reutilizava a URL | nome da imagem leva um resumo do conteúdo |
| `apagou` sem apagar | o DELETE aceito (HTTP 200) já valia como apagado | confere que o post sumiu; senão registra falha |
| Hora de Brasília | 4 cópias de `UTC-3` espalhadas | uma só, em `config.agora()` (com fuso real) |
| Credenciais no diário | 2 listas de padrões diferentes | uma lista só (`seguranca.py`), com GitHub e Anthropic |
| Injeção em workflow | `inputs` interpolados direto no shell | passam por variáveis de ambiente |
| Permissões | workflows de leitura com permissão padrão | `contents: read` onde basta |
| Crescimento do branch `assets` | ~1,6 MB/dia sem limite (o README dizia 2 MB/mês) | poda de imagens com mais de 45 dias |
| Imagem renderizada 3× | LinkedIn, Facebook e Instagram geravam o mesmo PNG | desenha uma vez e reaproveita |
| `infografico.py` com 1000 linhas | cenas, exemplos e estado global (`ATUAL`) misturados | `desenho.py`, `cenas.py`, `cenas_historicas.py`, `exemplos_infograficos.py` |

## Testes

`pytest` (109 testes) e `ruff` rodam a cada mudança em `src/`, `tests/` ou `content/`
(workflow **Testes**). Cobrem: retry de rede, validação do infográfico, desenho de
todas as cenas e combinações de fundo e elemento, leitura da pauta e fallback,
legendas e hashtags, anti-duplicidade, geração do dia, exclusão de posts e a
integridade de **todas** as pautas já commitadas.

## Pontos que continuam em aberto

- Os Stories ainda usam a arte antiga (NOC); refazê-los no padrão novo é uma melhoria, não uma correção.
- No LinkedIn as hashtags saem escapadas (`\#`), como texto; trocar pelo formato de hashtag
  da API exige teste real de publicação.
- As Routines rodam na sessão de código que as criou. Se ela estiver indisponível, vale o `cron` de reserva.
- `GRAPH_VERSION` vale até 21/01/2027 e `LINKEDIN_VERSION` até ~09/2027.
