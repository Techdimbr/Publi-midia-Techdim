# Publi-midia-Techdim

Publicação diária automática da TECHDIM no **LinkedIn**, **Facebook** e
**Instagram**, rodando inteiramente no GitHub Actions — sem depender de nenhum
computador ligado.

## Como funciona

Quatro temas, uma publicação de cada por dia, em todas as redes:

| Horário (Brasília) | Tema | Conteúdo |
|---|---|---|
| 08:00 | Notícias de Tecnologia & IA | notícia do dia relevante para empresas, conferida em 2 fontes |
| 11:07 | Cibersegurança · IA · Hacker | alerta ou notícia de segurança, conferida em 2 fontes |
| 14:23 | Conhecimento | ensino prático, passo a passo, com a documentação oficial como fonte |
| 17:23 | TECHDIM · Serviços | divulgação de um serviço (ou de uma ideia de software sob medida) |

Quem escreve a pauta é a Routine do Claude (ver "Agendamento e pauta do dia");
quem publica é o workflow **Publicar**, no GitHub Actions. Nada depende de
computador ou celular ligado.

Cada execução do workflow:

1. **confere o que já saiu hoje** (diário do dia no branch `assets`) e só
   publica o que falta — é o que impede post duplicado quando a Routine e o
   agendador do GitHub disputam o mesmo horário;
2. **monta o conteúdo**: a pauta do dia (`content/diario/`), ou, se faltar ou
   estiver malformada, uma reserva — RSS com filtro (notícias, e curadoria por IA
   se `ANTHROPIC_API_KEY` existir) ou o acervo autoral (conhecimento e serviços);
3. **desenha as imagens** (ver "Padrão visual");
4. **publica as imagens** num branch `assets`, que lhes dá URL pública (o
   Instagram só aceita buscar imagem por URL, não aceita upload de arquivo);
5. **publica nas redes** via chamada direta às APIs oficiais, comenta com as
   fontes e **registra tudo** no diário do dia.

### Padrão visual

Cada post sai como **um infográfico 1080 × 1350** (título em duas cores, texto
curto, "3 lições táticas", pergunta final e chamada "Vamos conversar?"), igual
em LinkedIn, Facebook e Instagram, com uma **cena ilustrada** própria do assunto:
a Routine escolhe o fundo e os elementos (notebook, rack, nuvem, escudo...) e a
imagem sai única, desenhada por código — sem banco de imagem e sem direito
autoral de terceiros. Catálogo de cenas e elementos: [docs/ESTILOS.md](docs/ESTILOS.md).

O texto do infográfico vem do bloco `infografico` da pauta e passa por
validação: textos longos são cortados com reticências e, se o bloco estiver
inválido ou o desenho falhar, o post sai com a **arte antiga** (carrossel de 4
imagens no Instagram e no Facebook, capa no LinkedIn) em vez de não sair.

Os Stories do Instagram (temas de notícia) usam arte própria 9:16.

As legendas são escritas **diferentes para cada rede** (tom institucional no
LinkedIn, direto no Facebook, visual no Instagram), com as hashtags do assunto
do post primeiro e as do tema depois.

## Configuração

### 1. Secrets (dados sigilosos)

Em **Settings → Secrets and variables → Actions → Secrets**:

| Secret | O que é |
|---|---|
| `META_ACCESS_TOKEN` | token de longa duração da Página do Facebook (serve também para o Instagram) |
| `LINKEDIN_ACCESS_TOKEN` | token do app LinkedIn |
| `ANTHROPIC_API_KEY` | chave da API da Anthropic, para a curadoria das notícias por IA (opcional) |

### 2. Variables (não são sigilosos)

Na aba **Variables** da mesma tela:

| Variable | O que é |
|---|---|
| `FB_PAGE_ID` | id da Página do Facebook |
| `IG_USER_ID` | id da conta comercial do Instagram |
| `LINKEDIN_URN` | `urn:li:organization:123456` (Página) ou `urn:li:person:abc` (perfil) |
| `WHATSAPP_NUMERO` | WhatsApp comercial só com dígitos, DDI+DDD (ex.: `5519999998888`) — opcional |

Sem `WHATSAPP_NUMERO` nada quebra: o convite para conversar cai no site. Com
ele, o primeiro comentário do Facebook passa a trazer um link que abre a
conversa com a mensagem já escrita, citando o post que trouxe a pessoa — que é
a única atribuição de origem que a Meta não entrega sozinha.

Depois de cadastrar o `META_ACCESS_TOKEN`, rode o workflow **Descobrir IDs**
uma vez: ele imprime o `FB_PAGE_ID` e o `IG_USER_ID` prontos para colar.

### 3. Permissões necessárias

**Meta** (app em modo Development basta, já que são as suas próprias contas —
não exige App Review nem Business Verification):
`pages_show_list`, `pages_read_engagement`, `pages_manage_posts`,
`instagram_basic`, `instagram_content_publish`.

**LinkedIn**: `w_member_social` para publicar como perfil pessoal, ou
`w_organization_social` para publicar como Página — este último exige o
programa Community Management API, com aprovação da própria LinkedIn.

### 4. Teste antes de ligar o automático

Actions → **Publicar** → *Run workflow*, escolha o tema e marque **ensaio**.
Com ensaio marcado nada é publicado: o workflow só gera as imagens e as
legendas, e você baixa tudo no artifact da execução para conferir.

Tirando o ensaio, a mesma tela publica de verdade — é o jeito de testar uma
rede de cada vez antes de deixar os horários rodarem sozinhos.

Para provar o caminho inteiro **sem publicar**, marque **sem_publicar**: o workflow
gera as imagens, envia ao branch `assets` e confere a URL pública (o que o ensaio
não faz), mas não chama nenhuma rede. O diário registra como ensaio.

## Pasta diária de registros

Cada publicação real grava um registro no branch `assets`, em
`registros/AAAA-MM-DD/` — ao lado das imagens daquele dia:

- `README.md` — índice do dia: hora, tema, título e o status em cada rede,
  com link para o post no ar;
- `HHhMM-<tema>.md` — o registro completo: curadoria usada, motivo da
  pauta, fontes, texto de cada rede, as imagens e o link da execução;
- `index.json` — os mesmos dados, para consulta automática.

O registro é gravado também quando a publicação falha, com o erro de cada
rede. Credenciais nunca entram no registro (o branch é público).

Link direto do dia: `https://github.com/Techdimbr/Publi-midia-Techdim/tree/assets/registros/AAAA-MM-DD`

## Agendamento e pauta do dia

O agendador do GitHub Actions **atrasa de 1h30 a 3h** (já se viu mais), então ele
não serve de relógio. Os horários são cumpridos por **Routines do Claude**, que
disparam o workflow no minuto certo; os `cron` do GitHub ficam como **reserva**:

| Horário (Brasília) | Quem | O que faz |
|---|---|---|
| 07:03 | Routine "TECHDIM — Pauta do Dia" | pesquisa e escreve os 4 posts em `content/diario/AAAA-MM-DD/`, valida, renderiza e grava num commit |
| 07:58 | Routine "Publicar notícias" | dispara `tema=noticias` (post às ~08:00) |
| 11:06 | Routine "Publicar hacker" | dispara `tema=hacker` (~11:07) |
| 14:22 | Routine "Publicar conhecimento" | dispara `tema=dica` (~14:23) |
| 17:22 | Routine "Publicar serviços" | dispara `tema=servico` (~17:23) |
| 08:07 · 11:07 · 14:23 · 17:23 | `cron` do GitHub | reserva: publica (atrasado) só se a Routine não publicou |

As Routines disparam com `evitar_duplicado=true` e o `cron` sempre confere o
diário do dia: um tema só sai de novo nas redes em que **ainda não saiu**. Se só
uma rede falhou, só ela é repetida. A execução ignorada fica registrada como
"pulado" no diário.

Se o arquivo do dia faltar ou estiver malformado, aquele horário usa o
conteúdo de reserva — RSS com filtro (notícias) ou o acervo autoral
(conhecimento e serviços) — e nunca fica vazio.

Formato de cada arquivo de pauta (`noticias.json`, `hacker.json`, `dica.json`, `servico.json`):

```json
{
  "titulo": "até 90 caracteres",
  "pontos": ["até 170 caracteres", "...", "..."],
  "fecho": "até 130 caracteres",
  "motivo": "por que esta pauta foi escolhida",
  "fontes": [["dominio.com.br", "https://..."]],
  "infografico": {
    "cena_composta": {"fundo": "datacenter", "elementos": ["rack", "nuvem"], "legenda": "BACKUP QUE RESTAURA"},
    "titulo_branco": "até 55 caracteres", "titulo_destaque": "até 35 caracteres",
    "historia": "até 230 caracteres",
    "licoes": [["Título curto", "texto até 110 caracteres"], ["...", "..."], ["...", "..."]],
    "pergunta": "até 80 caracteres",
    "hashtags": ["#IAGenerativa", "#Governanca", "#TI", "#TECHDIM"]
  }
}
```

O post de cibersegurança usa `"cena": "painel"` com `terminal_titulo` e `terminal`
no lugar de `cena_composta` (detalhes em [docs/ESTILOS.md](docs/ESTILOS.md)).

**As Routines rodam na sessão de código que as criou** (é ela que tem acesso ao
repositório). Se a sessão estiver indisponível, a Routine não roda — e o `cron`
de reserva publica no horário (atrasado) do GitHub.

**Publicação sob demanda:** `content/especiais/AAAA-MM-DD.json` e o workflow
disparado manualmente com `tema=especial` (o mesmo formato, com bloco `infografico`).

## Stories, primeiro comentário e relatório semanal

**Stories (Instagram):** **todos** os temas saem nos Stories, numa arte 9:16
com o título, "o que fazer", a chamada para o post no perfil e, encostado no
campo de resposta do Instagram, o pedido "responde aqui embaixo" com a pergunta
do post. Responder um Story é mandar uma DM: conta como interação para o
alcance e abre conversa com quem pode virar cliente — é a única conversão que a
API de Stories permite, porque o adesivo de link só é publicável à mão. Story
não disputa alcance com o feed e some em 24 horas.

**Pedido de interação:** toda legenda fecha com uma pergunta concreta sobre a
empresa de quem lê. Comentário é a única interação que começa uma conversa com
quem pode virar cliente — é onde nasce o lead. A pergunta vem da pauta do dia;
quando não vem, a curadoria por IA escreve uma; se nem isso, usa-se a reserva do
tema. No Instagram a legenda pede também para **mandar para quem cuida da TI** e
para seguir: os três sinais que o próprio Instagram diz pesar mais no ranking
são tempo de exibição, envios por DM e curtidas, cada um medido por alcance
(Adam Mosseri, jan/2025, reafirmado em 2026) — comentário não está na lista.

**Hashtags:** o Instagram limita cada post a **5 hashtags** (anunciado em
18/12/2025) e diz que poucas específicas rendem mais que muitas genéricas, então
cada rede tem vagas contadas em vez de uma lista longa: no Instagram, 2 de
assunto + 2 de praça (`#ticampinas`, `#campinas`) + a marca; no Facebook, 2 + 1
+ marca; no LinkedIn, 3 + 1 + marca. O assunto vem da pauta do dia e, se faltar,
da reserva do tema; `#TI` não gasta vaga (é genérica demais) e a marca fecha a
lista. Conta nova não é achada por hashtag de marca (`#TECHDIM` só alcança quem
já conhece) nem por hashtag gigante: quem compra é dono de PME de Campinas, e é
ele que procura por praça. Segundo o chefe do Instagram, hashtag ajuda a busca,
mas não aumenta o alcance.

**Janela de publicação:** nada sai entre 22h e 7h (Brasília). Em 02/10/2026
quatro posts saíram entre 00h22 e 01h11, quando quase ninguém do público está na
rede. É uma premissa, não uma medição: o relatório semanal traz "qual horário
rende mais" e é ele que deve ajustar a janela (`JANELA_PUBLICACAO` em
`src/config.py`). Para um teste proposital fora de hora, marque
**forcar_fora_de_hora** ao disparar o workflow.

**Links rastreáveis:** todo link clicável (Facebook e LinkedIn) sai com UTM que
diz rede, tema e dia, então o Google Analytics do site mostra qual post trouxe
visita. No Instagram o link não é clicável em lugar nenhum, então lá vai o
endereço limpo e o clique de verdade acontece pela bio.

**Primeiro comentário:** link no corpo do post reduz o alcance no Facebook e
no LinkedIn. As fontes e o site vão para o primeiro comentário, publicado logo
depois do post; a legenda avisa "fontes e site no primeiro comentário". No
Instagram, onde link não é clicável, o site continua na legenda e o comentário
traz as fontes. Se o comentário falhar, o post continua no ar e a falha fica no
registro do dia.

**Relatório semanal:** toda segunda às 08:17 o workflow "Relatório semanal"
lê os registros dos últimos 7 dias, busca alcance e engajamento de cada post
na Meta e grava `registros/semanal/AAAA-Sxx.md` no branch `assets`: resumo por
rede, **ranking dos temas** (qual traz mais retorno), melhores posts e a tabela
completa. Métricas usadas: Facebook — visualizações únicas (alcance),
visualizações, cliques, reações, comentários e compartilhamentos; Instagram —
alcance, visualizações, interações, curtidas, comentários, compartilhamentos e
salvamentos. O relatório traz ainda **qual horário rende mais** e a **curva de
seguidores** da semana.

**Métricas do dia:** toda noite, por volta das 21h, o workflow "Métricas do dia"
grava `registros/AAAA-MM-DD/metricas.json` e acumula `registros/seguidores.csv`
no branch `assets`. Ele existe porque duas coisas somem se ninguém olhar no
mesmo dia: a métrica de Story, que a Meta guarda por apenas 24 horas, e o número
de seguidores, que é um retrato do instante — sem uma foto por dia não existe
curva de crescimento, que é a meta principal da conta hoje.

## Diário de movimentações

`registros/AAAA-MM-DD/movimentos.md` (branch `assets`) lista, em ordem, tudo
que aconteceu no dia: planejado, iniciado, gerado, publicado, Story, comentou,
falhou, pulado e **ensaios/testes** (marcados com 🧪). Ações feitas à mão
(apagou, editou, comentou) entram pelo workflow **Registrar movimento**.
Credenciais nunca entram no diário.

## LinkedIn

Guia completo, com links: [docs/LINKEDIN.md](docs/LINKEDIN.md).

1. No app do LinkedIn (developer.linkedin.com), aba **Products**: ative
   "Share on LinkedIn" e "Sign In with LinkedIn using OpenID Connect" (para
   publicar como perfil). Para publicar como **página da empresa** é preciso o
   "Community Management API", que passa por aprovação do LinkedIn.
2. Gere o token em **Developer tools → OAuth 2.0 tools → Create token**:
   escolha o app, marque `openid`, `profile` e `w_member_social`
   (ou `w_organization_social` para página) e faça login.
3. Cadastre o token no Secret `LINKEDIN_ACCESS_TOKEN`.
4. Rode **Actions → Descobrir IDs**: ele imprime o `LINKEDIN_URN` do perfil e
   das páginas. Cadastre-o na Variable `LINKEDIN_URN`.

O token do LinkedIn vale 60 dias e não se renova sozinho em apps comuns: o
workflow "Verificar token" testa toda segunda e falha (avisando por e-mail)
quando ele vencer.

**Prazos de versão:** Graph API da Meta `v21.0` até 21/01/2027;
LinkedIn `202609` até ~09/2027 (`GRAPH_VERSION` e `LINKEDIN_VERSION` em
`src/config.py`).

## Manutenção

- **Validade do token**: o workflow **Verificar token** roda toda segunda-feira
  e falha de propósito quando faltam 10 dias ou menos para expirar, para o
  GitHub te notificar por e-mail antes que a publicação quebre em silêncio.
  Token de longa duração da Meta vale ~60 dias.
- **Mudar horário**: o horário real é o das Routines (ajuste o `cron` de cada
  uma); os `cron` do `publicar.yml` são só a reserva e estão em UTC (Brasília é UTC−3).
- **Mudar em quais redes cada tema sai**: `THEME_TARGETS` em `src/config.py`.
- **Acrescentar dica ou serviço**: edite `content/dicas.json` e
  `content/servicos.json`. O acervo gira por dia, então quanto mais itens,
  menos repetição.
- **Ajustar o filtro de notícias**: as listas `BLOCK` e `ALLOW` em
  `src/content.py` decidem o que é pauta. É heurística por palavra-chave —
  vale revisar o que saiu nas primeiras semanas e ajustar.
- **Branch `assets`**: guarda as imagens publicadas e os registros em texto,
  sem o histórico do código. As imagens têm nome com um resumo do conteúdo
  (`arte-1a2b3c4d.png`), para a URL mudar quando a imagem muda. Cada execução
  apaga as imagens com mais de 45 dias (`DIAS_IMAGENS` em `publicar.yml`); os
  registros em texto ficam para sempre, com as imagens antigas indisponíveis.

## Rodar na sua máquina

```bash
pip install -r requirements-dev.txt

# só gera e mostra, não publica
PYTHONPATH=src python src/main.py preview --theme dica

# gera as imagens em out/
PYTHONPATH=src python src/main.py generate --theme hacker --networks instagram

# o que ainda falta publicar hoje, dado o index.json do dia
PYTHONPATH=src python src/main.py pendentes --theme hacker --indice index.json

# testes e análise estática (rodam a cada push no workflow "Testes")
ruff check src tests && pytest

# confere a pauta de um dia (o que a Routine roda antes de gravar)
PYTHONPATH=src python src/validar_pauta.py 2026-10-02

# regenera os exemplos de padrão visual
python src/exemplos_infograficos.py historias
```

## Estrutura

```
.github/workflows/
  publicar.yml          publicação (Routine + reserva por cron) e execução manual
  testes.yml            ruff + pytest a cada mudança em código ou conteúdo
  token.yml             verificação semanal da validade dos tokens
  relatorio.yml         relatório semanal de alcance e engajamento
  metricas.yml          coleta diária: seguidores e Stories (expiram em 24 h)
  apagar-posts.yml      exclusão de posts, com conferência e registro
  registrar-movimento.yml  anotações manuais no diário
  descobrir-ids.yml     imprime FB_PAGE_ID, IG_USER_ID e LINKEDIN_URN
content/
  diario/AAAA-MM-DD/    pauta do dia escrita pela Routine
  destaques/ especiais/ posts escritos sob demanda
  dicas.json servicos.json   acervo autoral (reserva)
docs/                   ESTILOS.md (cenas), LINKEDIN.md, REVISAO.md
fonts/ fotos/ exemplos/ fontes OFL, foto de exemplo e imagens de exemplo
src/
  config.py             marca, praça, formatos, credenciais, janela de horário
  links.py              UTM e link de WhatsApp (de onde veio cada visita)
  metricas_dia.py       coleta diária de seguidores e Stories
  content.py            pauta, RSS, acervo e legendas por rede
  infografico.py        validação do bloco e desenho do infográfico
  cenas.py              biblioteca de cenas (composta, notícias, ensino, rede, dev, painel)
  cenas_historicas.py   cinco cenas de exemplo (Titanic, Maginot...)
  desenho.py            fontes, cores e primitivas de desenho
  render.py             arte antiga (carrossel/capa) e Stories
  main.py               generate / publish / preview / pendentes / registrar
  registro.py movimentos.py relatorio.py   diário, movimentos e relatório
  validar_pauta.py     confere a pauta do dia antes de ela ir para o ar
  apagar.py token_check.py discover.py linkedin_ids.py curator.py
  seguranca.py texto.py utilitários (redação de credenciais, corte de texto)
  publishers/           facebook.py, instagram.py, linkedin.py, common.py
tests/                  pytest
```
