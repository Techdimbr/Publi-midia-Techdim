# Publi-midia-Techdim

Publicação diária automática da TECHDIM no **LinkedIn**, **Facebook** e
**Instagram**, rodando inteiramente no GitHub Actions — sem depender de nenhum
computador ligado.

## Como funciona

Quatro temas, uma publicação de cada por dia, em todas as redes:

| Horário (Brasília) | Tema | Conteúdo |
|---|---|---|
| 08:07 | Notícias de Tecnologia & IA | manchetes reais do dia, de feeds em português |
| 11:07 | Tecnologia Hacker | vulnerabilidades, ataques e alertas de segurança |
| 14:23 | Dica / Conhecimento | conteúdo educativo autoral |
| 17:23 | Anúncio de Serviço | divulgação dos serviços TECHDIM |

Os minutos são deslocados de propósito: cron no minuto 0 concentra a fila do
GitHub e costuma atrasar vários minutos.

Cada execução:

1. **monta o conteúdo** — temas 1 e 2 buscam manchetes reais em feeds RSS
   (priorizando fontes em português) e filtram o que não é pauta técnica;
   temas 3 e 4 giram um acervo autoral em `content/`;
   Com `ANTHROPIC_API_KEY` configurada, os temas de notícia passam pela
   **curadoria por IA**: o Claude escolhe a manchete mais útil para empresas,
   lê a matéria e escreve dois fatos e uma recomendação prática. Sem a chave,
   ou se a API falhar, vale o filtro por palavra-chave. O resumo da execução
   no Actions mostra qual curadoria foi usada;
2. **renderiza as imagens** no formato ideal de cada rede, com arte generativa
   própria do tema;
3. **publica as imagens** num branch `assets`, que lhes dá URL pública (o
   Instagram só aceita buscar imagem por URL, não aceita upload de arquivo);
4. **publica nas três redes** via chamada direta às APIs oficiais.

### Formato por rede

| Rede | Formato | Dimensão | Mecanismo |
|---|---|---|---|
| Instagram | carrossel de 4 | 1080 × 1350 (4:5) | containers + `CAROUSEL` |
| Facebook | álbum de 4 | 1200 × 1500 (4:5) | `attached_media` |
| LinkedIn | imagem única | 1200 × 1200 (1:1) | Images API + Posts API |

O LinkedIn não aceita carrossel de imagens soltas pela API: o "carrossel"
nativo é um PDF enviado pela Documents API, com permissão própria. Por isso
cada tema sai lá como imagem única — a capa.

As legendas são escritas **diferentes para cada rede** (tom institucional no
LinkedIn, direto no Facebook, visual no Instagram), porque texto idêntico
replicado nas três costuma ter alcance pior.

### Identidade visual por tema

| Tema | Acento | Motivo gráfico |
|---|---|---|
| Notícias | azul `#4DA3FF` | ondas de transmissão + espectro |
| Hacker | vermelho `#FF3B30` | scanlines, hexdump e glitch |
| Dica | verde `#39FF14` | grade de rede com nós e enlaces |
| Serviço | âmbar `#FFB000` | trilhas de circuito |

A arte é determinística: a mesma data e o mesmo tema geram sempre a mesma
imagem, o que torna qualquer falha reproduzível.

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

## Agendamento

| Quem agenda | O quê | Quando (Brasília) |
|---|---|---|
| Routine do Claude "TECHDIM — Destaque do Dia" | pesquisa a notícia, confere em 2 fontes, grava `content/destaques/AAAA-MM-DD.json` e dispara este workflow | 07:52 |
| GitHub Actions (`publicar.yml`) | Tecnologia Hacker | 11:07 |
| GitHub Actions (`publicar.yml`) | Dica / Conhecimento | 14:23 |
| GitHub Actions (`publicar.yml`) | Anúncio de Serviço | 17:23 |

Os dois rodam na nuvem (Anthropic e GitHub): nenhum computador precisa
estar ligado. Os horários do GitHub Actions costumam atrasar alguns
minutos — às vezes mais de uma hora em dias de fila cheia.

## Manutenção

- **Validade do token**: o workflow **Verificar token** roda toda segunda-feira
  e falha de propósito quando faltam 10 dias ou menos para expirar, para o
  GitHub te notificar por e-mail antes que a publicação quebre em silêncio.
  Token de longa duração da Meta vale ~60 dias.
- **Mudar horário**: edite os `cron` em `.github/workflows/publicar.yml`
  (estão em UTC; Brasília é UTC−3).
- **Mudar em quais redes cada tema sai**: `THEME_TARGETS` em `src/config.py`.
- **Acrescentar dica ou serviço**: edite `content/dicas.json` e
  `content/servicos.json`. O acervo gira por dia, então quanto mais itens,
  menos repetição.
- **Ajustar o filtro de notícias**: as listas `BLOCK` e `ALLOW` em
  `src/content.py` decidem o que é pauta. É heurística por palavra-chave —
  vale revisar o que saiu nas primeiras semanas e ajustar.
- **Branch `assets`**: guarda só as imagens publicadas, sem o histórico do
  código. Cresce ~2 MB por mês; dá para limpar periodicamente sem afetar os
  posts já no ar (as redes já baixaram a imagem).

## Rodar na sua máquina

```bash
pip install -r requirements.txt

# só gera e mostra, não publica
PYTHONPATH=src python src/main.py preview --theme dica

# gera as imagens em out/
PYTHONPATH=src python src/main.py generate --theme hacker --networks instagram
```

## Estrutura

```
.github/workflows/
  publicar.yml       as 4 publicações diárias + execução manual
  token.yml          verificação semanal da validade do token
  descobrir-ids.yml  imprime FB_PAGE_ID e IG_USER_ID
content/
  dicas.json         acervo do tema "Dica / Conhecimento"
  servicos.json      acervo do tema "Anúncio de Serviço"
src/
  config.py          marca, paleta por tema, formatos, credenciais
  content.py         montagem do conteúdo (RSS + acervo) e legendas por rede
  render.py          renderização das imagens e arte generativa
  main.py            orquestrador (generate / publish / preview)
  discover.py        descoberta dos ids a partir do token
  token_check.py     verificação de validade do token
  publishers/        facebook.py, instagram.py, linkedin.py
```
