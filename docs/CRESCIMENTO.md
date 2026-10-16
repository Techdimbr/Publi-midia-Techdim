# Plano de crescimento da TECHDIM — 90 dias

**Descrições otimizadas · 100 perfis para seguir · interação diária · relatório por e-mail · reserva com Gemini · metas**

Preparado em 16/10/2026 · Situação: **aguardando a sua aprovação** (responda "começar") · Dados lidos da API da Meta em 16/10/2026

Legenda: 🤖 Claude faz · 👤 só você consegue (nos apps) · ⚙️ roda sozinho

---

## 1. Resumo em um minuto

- **Hoje:** 47 seguidores no Facebook e 20 no Instagram. Cada post do Instagram chega a cerca de 1 pessoa. Os perfis não explicam o que a TECHDIM faz (Facebook com "Sobre" igual ao endereço do site e categoria genérica "Company"; Instagram com "Em construção 🚧" e sem link) e o site não mede visitas.
- **Causa:** a plateia de partida é pequena demais para o algoritmo testar os posts, e quem chega ao perfil não encontra uma promessa clara nem um caminho até o contato.
- **Estratégia:** (1) perfis que explicam e vendem em 3 segundos; (2) semear 100 a 200 pessoas reais e relevantes; (3) conteúdo feito para ser enviado e salvo; (4) interação diária com contas-alvo; (5) canais que acumulam (site e blog, Google, LinkedIn do fundador); (6) medir todo dia e toda segunda-feira.
- **Os três pedidos novos, em uma linha cada:**
  - **Seguir, curtir e comentar todo dia em todas as redes:** as APIs não permitem fazer isso em contas de terceiros, e robô para isso derruba a conta (seção 6). O que eu automatizo é a **Mesa de interação do dia**: todo dia você recebe por e-mail as contas a seguir, os posts a comentar e o comentário já rascunhado; são 15 a 20 minutos de cliques seus.
  - **Relatório diário por e-mail:** sim, com publicações, interações, seguidores, desempenho e erros (seção 7).
  - **Reserva com Gemini:** sim. Se o Claude parar, a pauta e a publicação continuam com a API gratuita do Gemini (seção 8). Precisa de uma chave grátis sua.
- **Meta em 90 dias (estimativa minha):** Instagram 20 → 250 a 400; Facebook 47 → 150 a 250; mais 300 conexões relevantes no LinkedIn; 10 ou mais avaliações no Google; 8 a 12 contatos qualificados por mês.
- **Para começar:** responda **"começar"**. Eu começo pelo Pacote 0 (relatório e reserva com Gemini) e pelo Pacote 1 (itens 🤖 da seção 11). O que só você faz nos aplicativos está marcado 👤 e vem com o texto pronto.

## 2. Onde estamos hoje (dados reais, 16/10/2026)

| | Facebook "Techdim" | Instagram @techdimbr |
|---|---|---|
| Seguidores | 47 | 20 (seguindo 92; 81 posts) |
| Categoria | "Company" (genérica) | — |
| Texto do perfil | "Sobre" = só `techdimbr.github.io/techdimbr`; descrição vazia | "Em construção 🚧 / Techdim Inova Simples (I.S)" |
| Link | Site: `http://www.techdim.com.br/` (antigo, fora do ar) e o novo | vazio |
| Contato | e-mail e telefone preenchidos; endereço "Brasil"; sem horário | — |
| Endereço da página | `facebook.com/1167193706481148` (sem nome de usuário) | `instagram.com/techdimbr` |
| Verificação | não verificada | — |

**Semana 05–11/10 (relatório semanal):** Instagram, 28 posts, alcance total 32 (cerca de 1 por post), 62 visualizações, 13 interações, nenhum comentário e nenhum salvamento. Facebook, 28 posts, 149 visualizações, 6 interações. Os 2 posts do Facebook que foram compartilhados tiveram 50 e 29 visualizações, contra uma média de cerca de 3 nos outros 26.

**Temas:** Serviços 0,6 interação por post; Notícias 0,5; Conhecimento e Hacker 0,1 (7 a 8 posts por tema: é indício, não prova).

**Publicação hoje:** Routines do Claude escrevem a pauta às 07:03 e disparam os 4 posts do dia; o cron do GitHub (08:07, 11:07, 14:23 e 17:23) é a reserva e publica sozinho se a Routine não rodou, usando RSS e o acervo autoral. A curadoria por IA do `curator.py` usa a API da Anthropic quando há chave.

**Site:** sem ferramenta de medição de visitas; `seo.json` sem os códigos do Google e do Bing (Search Console ainda não verificado). **LinkedIn:** os posts saem pelo perfil pessoal que autorizou o app (o do fundador, se for o mesmo); a API não deixa ler métricas, e publicar como Página da empresa depende da aprovação da "Community Management API" pelo LinkedIn (`docs/LINKEDIN.md`, passo 7).

## 3. Decisões que dependem de você

| # | Decisão | Minha recomendação |
|---|---|---|
| D1 | Mostrar o WhatsApp (19) 99615-3276 nos perfis (bio, Google, LinkedIn)? | Sim. O site já publica o número, e o WhatsApp é onde o negócio fecha. |
| D2 | Usar a mensagem única "Cibersegurança defensiva, infraestrutura e IA local para empresas · Campinas-SP e todo o Brasil" em todos os perfis? | Sim. Hoje o site fala "Doutrina Kether_1, GCP, IA soberana" e os posts falam "TI para pequena e média empresa": quem chega vê duas empresas. |
| D3 | O fundador (Eng. Deivis Irio Mayer, conforme o site) aparece em foto, vídeo ou voz? | Sim. Pessoas seguem pessoas, e no LinkedIn o perfil pessoal costuma alcançar bem mais que a página da empresa (dado de mercado). |
| D4 | Quem faz os 15 a 20 minutos diários da Mesa de interação (você ou alguém da equipe)? | Uma pessoa fixa, sempre no mesmo horário. |
| D5 | Anúncios pagos (R$ 0, 300 ou 600 por mês)? | R$ 0 nas 4 primeiras semanas; depois decidimos com os números. |
| D6 | Manter 28 posts por semana em cada rede ou testar menos e melhor por 2 semanas? | Testar: o alcance de 1 por post sugere que o volume não está sendo recompensado. |
| D7 | Citar nos perfis o prazo "resposta em até 15 minutos para emergências" que está no site? | Só se for cumprido sempre. |
| D8 | Onde receber o relatório diário? | `reparafacilcampinas@gmail.com` (o e-mail desta conta); diga se quiser outro ou mais de um. |
| D9 | Criar a chave grátis do Gemini e a senha de app do Gmail (seções 7 e 8)? | Sim: são 5 minutos e destravam o relatório e a reserva independentes do Claude. |

## 4. Fase 0 — Descrições e perfis (1 dia)

### 4.1 Mensagem-base (use em todo lugar)

> **Cibersegurança defensiva, infraestrutura e IA local para empresas. Campinas-SP e todo o Brasil.**

Três pilares: **Proteger** (hardening, resposta a incidentes 24/7, backup e recuperação) · **Organizar** (Google Cloud, redes, servidores, LGPD) · **Automatizar** (IA local, com os dados dentro da empresa). Prova: liderança do Eng. Deivis Irio Mayer e 10 projetos abertos no GitHub. Chamada: **"Peça um diagnóstico técnico"**. Todos os fatos vêm do site e do llms.txt da TECHDIM; confira antes de publicar.

### 4.2 Instagram (@techdimbr) — 👤 no app (a API não edita o perfil)

**Nome (até 30 caracteres):**

```
Techdim | Cibersegurança e TI
```

**Bio (até 150 caracteres):**

```
Cibersegurança, infraestrutura e IA local para empresas 🛡️
Campinas-SP e todo o Brasil
👇 Peça um diagnóstico técnico
```

- **Link:** `https://techdimbr.github.io/techdimbr/` (depois da Fase 0, troque pela página de links com medição: `.../links/`).
- **Categoria:** a mais próxima de "Empresa de tecnologia da informação".
- **Contato:** e-mail `techdimbrasil@gmail.com` e, se D1 for sim, o WhatsApp.
- **Destaques (4):** Serviços · Segurança · IA local · Contato.
- **Posts fixados (3):** "Modelo de IA aberto pode rodar dentro da empresa", "Acesso remoto sem abrir a porta" e "Hardening de servidores e estações" (os 3 de maior alcance da semana de 05 a 11/10).
- Passo a passo: Perfil → Editar perfil → Nome · Bio · Links · Categoria · Opções de contato.

### 4.3 Facebook (Página "Techdim")

Estado lido pela API: categoria "Company", "Sobre" só com o endereço do site, endereço "Brasil", sem horário e sem nome de usuário.

**"Sobre" (curto) — 🤖 aplico pela API após o seu "começar":**

```
Cibersegurança, infraestrutura e IA local para empresas. Campinas-SP e todo o Brasil.
```

**Descrição longa — 🤖 aplico pela API se o campo aceitar; senão você cola:**

```
A TECHDIM é uma empresa de tecnologia de Campinas-SP, liderada pelo engenheiro Deivis Irio Mayer. Protegemos, organizamos e automatizamos a TI de empresas: cibersegurança defensiva (hardening, resposta a incidentes 24/7, backup e recuperação), nuvem no Google Cloud, redes e servidores, e IA local, com os dados da sua empresa dentro de casa e em conformidade com a LGPD. Atendimento em Campinas e todo o Brasil. Peça um diagnóstico técnico: techdimbr.github.io/techdimbr
```

**👤 No app (Página → Editar informações):**

- **Nome de usuário:** `@techdimbr` (igual ao Instagram, se estiver livre), para o endereço ficar `facebook.com/techdimbr`.
- **Categoria:** "Empresa de tecnologia da informação" (e, se existir, "Serviço de segurança de computadores").
- **Endereço:** cidade Campinas, SP. **Horário:** "Sempre aberto" ou plantão 24 h, conforme o que a TECHDIM cumpre.
- **Site:** apague `http://www.techdim.com.br/` e deixe só `https://techdimbr.github.io/techdimbr/`.
- **Botão da Página:** "Enviar mensagem" ou WhatsApp. **Serviços:** os 6 do catálogo (seção 4.7).

### 4.4 LinkedIn

**Perfil do fundador (é o canal de maior alcance para B2B) — 👤**

Título (até 220 caracteres; ajuste ao cargo real, o site cita "Lead Cyber Defense Engineer & CTO"):

```
Engenheiro de Cibersegurança Defensiva e CTO na TECHDIM | Hardening Linux, Google Cloud e IA local para empresas | Campinas-SP
```

Sobre (até 2.600 caracteres):

```
Ajudo empresas a manter a operação de pé quando a tecnologia falha ou é atacada.

Sou engenheiro de cibersegurança defensiva e fundador da TECHDIM, em Campinas-SP. Trabalho em três frentes:
• Proteger: hardening de servidores e estações, resposta a incidentes 24/7, backup com restauração testada.
• Organizar: arquitetura em Google Cloud (Terraform, Zero Trust), redes, servidores e adequação à LGPD sem travar a operação.
• Automatizar: IA local (on-premise), com os dados dentro da empresa, para atendimento, análise de contratos e processos.

Publico o que aprendo: 10 projetos abertos no GitHub (hardening, landing zone em GCP, triagem forense, scanner de dados pessoais) e um radar diário de ameaças e vulnerabilidades no blog da TECHDIM.

Quer saber onde a sua empresa está exposta? Peça um diagnóstico técnico: techdimbr.github.io/techdimbr
```

Em "Destaques": o site, o blog, o ThreatScanner e o GitHub da organização.

**Página da empresa (criar, se ainda não existir) — 👤**

- **Nome:** TECHDIM · **Setor:** Serviços e consultoria de TI · **Tamanho:** o da equipe real · **Site:** `https://techdimbr.github.io/techdimbr/`
- **Slogan (até 120 caracteres):**

```
Cibersegurança defensiva, infraestrutura e IA local para empresas | Campinas-SP
```

- **Sobre (até 1.500 caracteres, para caber no menor limite informado):**

```
A TECHDIM é uma empresa brasileira de tecnologia, sediada em Campinas-SP, que protege, organiza e automatiza a TI de empresas.

O que fazemos
• Cibersegurança defensiva: hardening de servidores e estações, resposta a incidentes 24/7, backup e recuperação de desastres.
• Nuvem e infraestrutura: arquitetura em Google Cloud (Terraform, Zero Trust), redes, servidores e migrações sem parar a empresa.
• IA local (on-premise): modelos que rodam dentro da sua empresa, sem enviar dados para fora, para atendimento, análise de documentos e automação de processos.
• Conformidade: adequação à LGPD e boas práticas ISO/IEC 27001 sem travar a operação.

Como trabalhamos
Começamos por um diagnóstico técnico e priorizamos primeiro o que mais reduz o risco. Mantemos 10 projetos abertos no GitHub e publicamos um radar diário de ameaças no blog.

Atendimento em Campinas e todo o Brasil. Peça um diagnóstico: techdimbr.github.io/techdimbr
```

- Depois de criar: ligue o cargo do fundador à Página e convide as conexões a seguir (ajuda oficial no Anexo D).

### 4.5 Perfil da Empresa no Google — 👤

- **Nome:** o nome real da empresa (TECHDIM), sem palavras-chave extras: o Google suspende perfis com nome inflado.
- **Categoria principal:** a mais próxima de "empresa de serviços de TI"; **adicionais:** serviço de segurança de computadores, consultoria de informática, desenvolvimento de software. Digite no campo e escolha as opções que aparecerem em português.
- **Área de atendimento:** Campinas e região (e "todo o Brasil" para o atendimento remoto). Se não recebe clientes no local, oculte o endereço.
- **Descrição (menos de 750 caracteres, sem links e sem promoções, segundo o Google):**

```
A TECHDIM é uma empresa de tecnologia de Campinas-SP, especializada em cibersegurança defensiva, infraestrutura e inteligência artificial local para empresas. Fazemos hardening de servidores e estações, resposta a incidentes 24 horas, backup com recuperação testada, arquitetura em Google Cloud, redes e servidores, adequação à LGPD e automação com IA que roda dentro da sua empresa, sem enviar seus dados para fora. Atendemos empresas de Campinas e região e também de todo o Brasil, de forma remota. O time é liderado pelo engenheiro Deivis Irio Mayer e mantém projetos abertos no GitHub. Comece por um diagnóstico técnico da sua infraestrutura.
```

- **Site:** `https://techdimbr.github.io/techdimbr/` · **Telefone:** o WhatsApp, se D1 for sim · **Serviços:** os 6 do catálogo · **Fotos:** logotipo e capa.
- **Avaliações:** peça a clientes satisfeitos (modelo no Anexo C) e responda todas. Meta: 10 em 90 dias.
- **Postagens:** uma por semana, reaproveitando o melhor artigo do blog.

### 4.6 WhatsApp Business — 👤

- **Descrição:** `Cibersegurança defensiva, infraestrutura e IA local para empresas. Campinas-SP e todo o Brasil. Diagnóstico técnico e plantão para emergências.` (o limite de caracteres desse campo não foi confirmado; o texto tem 143.)
- **Mensagem de saudação:** `Olá! Aqui é a TECHDIM. Para agilizar, conte em uma mensagem: 1) o que está acontecendo ou o que você precisa; 2) quantos computadores e servidores a empresa tem; 3) se é uma emergência (algo parado agora).`
- **Mensagem de ausência (só se o plantão existir de fato):** `Estamos fora do horário comercial. Se for emergência (sistema parado ou suspeita de ataque), responda URGENTE que acionamos o plantão. Caso contrário, retornamos no próximo dia útil.`
- **Etiquetas:** novo · orçamento · cliente · emergência. **Catálogo:** os 6 serviços.

### 4.7 Catálogo de serviços (para Facebook, Google e WhatsApp)

1. Diagnóstico de infraestrutura e segurança
2. Hardening de servidores e estações
3. Backup gerenciado e recuperação testada
4. Resposta a incidentes e plantão 24/7
5. Nuvem Google Cloud, redes e servidores
6. IA local e automação de processos

### 4.8 Site (techdimbr.github.io/techdimbr) — 🤖 após o seu "começar"

O título atual (76 caracteres) e a descrição atual (279 caracteres) passam do que o Google costuma mostrar e saem cortados. Proposta:

- **Título (58 caracteres):** `TECHDIM | Cibersegurança e TI para Empresas em Campinas-SP`
- **Descrição (139 caracteres):** `Cibersegurança defensiva, hardening Linux, Google Cloud e IA local para empresas. Campinas-SP e todo o Brasil. Peça um diagnóstico técnico.`
- **Open Graph e Twitter** com o mesmo texto; **JSON-LD** com `sameAs` (Instagram, Facebook, LinkedIn, GitHub) e "Campinas" na descrição.
- **Medição de visitas sem cookies** (por exemplo, Cloudflare Web Analytics): hoje não dá para saber quantas visitas vêm de cada rede. 👤 Você cria a conta gratuita e me passa o código do snippet.
- **Página de links** (`/links/`) para a bio do Instagram, com WhatsApp, diagnóstico, blog, ThreatScanner e Calculadora de ROI, tudo com UTM.
- **Rodapé "Siga a TECHDIM"** em cada página do blog, para a busca virar seguidor.
- **Search Console e Bing Webmaster:** 👤 dez minutos, passo a passo em `docs/SEO.md`.

### 4.9 GitHub (canal técnico) — 👤

Preencha o perfil da organização e, nos 10 repositórios, a descrição, o site e os tópicos (`cybersecurity`, `hardening`, `debian`, `terraform`, `gcp`, `lgpd`, `rag`, `dfir`), com o link do site no README.

## 5. Fase 1 — Semeadura (semana 1)

**Objetivo:** dar ao algoritmo uma plateia real e relevante. Os sinais mais pesados do Instagram são tempo de exibição, curtidas e envios; com 20 seguidores não há quem gere esses sinais.

1. 👤 **Lista de 100 pessoas:** clientes e ex-clientes, fornecedores, parceiros, contadores e advogados que atendem empresas, colegas de TI, contatos do LinkedIn em Campinas e a equipe. Só quem já tem relação com você (vale para a LGPD e para as regras do WhatsApp).
2. 👤 **Convite individual por WhatsApp** (modelo no Anexo C). Meta: 100 convites rendem 30 a 50 novos seguidores por rede.
3. 👤 **Facebook:** Página → ⋯ Opções → Convidar amigos → escolha os perfis → Enviar convites.
4. 👤 **Instagram:** Perfil → ☰ → Código QR. Ponha o QR em propostas, cartão e assinatura de e-mail.
5. 👤 **LinkedIn:** publique o post de lançamento (Anexo C) pelo perfil do fundador e peça a 10 pessoas comentários reais na primeira hora.
6. 👤 **Círculo de compartilhamento:** 10 pessoas (clientes e parceiros) que compartilham 1 post de Serviços por semana. Foram compartilhamentos que levaram posts do Facebook de cerca de 3 para 29 a 50 visualizações.
7. 👤 **Assinatura de e-mail e status do WhatsApp Business** com o site e o `@techdimbr`.

**Meta da semana:** Instagram 20 → 80 ou mais; Facebook 47 → 90 ou mais; 10 pessoas no círculo; 70 contas-alvo seguidas (10 por dia).

## 6. Seguir, curtir e comentar todos os dias — o que dá para automatizar

### 6.1 O que cada rede permite (conferido em 16/10/2026)

| Ação | Instagram | Facebook (Página) | LinkedIn |
|---|---|---|---|
| Ler posts de contas de terceiros, para sugerir | **Sim**, só contas profissionais (Business Discovery) | Só com a função "Page Public Content Access", que exige análise da Meta | Não: a API do projeto não lê nem os posts da própria conta |
| Seguir contas de terceiros | Não existe na API | Não existe na API | Não existe na API |
| Curtir posts de terceiros | Não existe na API | Não existe na API | Automação proibida pelo LinkedIn |
| Comentar em posts de terceiros | Não existe na API | Não existe na API | Automação proibida pelo LinkedIn |
| **Responder comentários dos seus posts** | **Sim** (permissão de comentários) | **Sim** (permissão de engajamento da Página) | Sim, nos seus posts |
| Curtir comentários dos seus posts | Não existe na API | A confirmar em teste (a documentação não mostra o caminho) | A confirmar |

### 6.2 Por que não usar robô para o resto

- **Instagram:** aplicativos de terceiros que geram curtidas, seguidas e comentários violam as Diretrizes e os Termos de Uso; a Meta remove as ações, avisa a conta e pede troca de senha. Entregar login e senha a um aplicativo é um dos gatilhos de restrição. Fontes no Anexo D.
- **LinkedIn:** o Acordo de Usuário proíbe robôs que comentem, curtam ou compartilhem posts ou "gerem engajamento não autêntico"; a conta pode ser restringida ou encerrada.
- **Meta, no geral:** a política de comportamento inautêntico trata engajamento automatizado como violação.
- Para o robô funcionar eu precisaria da senha das contas guardada num servidor: risco alto e ganho pequeno. **Não vou construir isso.** O que sobra é uma ação de pessoa, no app, e é ela que eu torno rápida.

### 6.3 O que eu automatizo de verdade: a Mesa de interação do dia (⚙️ + 👤)

Todo dia às 08:30 chega um e-mail curto, pronto para clicar (Pacote 2):

1. **Seguir hoje (10 contas):** 7 globais e 3 do Brasil ou de Campinas, em sequência, com o link de cada perfil.
2. **Comentar hoje (5 posts):** posts recentes das contas da lista (lidos pela API oficial, só contas profissionais do Instagram), com um **rascunho de comentário em português ou inglês** feito pela IA a partir da legenda. Você edita se quiser e posta no app.
3. **Curtir hoje (10 posts):** os links dos posts mais recentes das mesmas contas.
4. **LinkedIn (3 perfis):** perfis de decisores da lista de empresas-alvo de Campinas, para comentar o post mais recente de cada um.
5. **Facebook:** 3 grupos ou Páginas locais para participar, com uma sugestão de resposta útil.

Tempo: 15 a 20 minutos. O comentário só entra na rede quando uma pessoa clica em "publicar" no app: é isso que mantém a conta segura.

Limite de uso da API: ao conferir 330 contas em cerca de 30 minutos, a API da Meta chegou ao limite e a conferência parou sozinha (3 contas ficaram para a próxima rodada). A Mesa de interação faz cerca de 15 consultas por dia, longe desse limite.

### 6.4 Interação nos seus próprios posts (⚙️, permitida)

- **Primeiro comentário:** já é automático.
- **Alerta de lead:** comentário com pergunta ou pedido de contato vira e-mail imediato.
- **Rascunho de resposta** para cada comentário recebido, no relatório do dia (você aprova e posta, ou autoriza respostas automáticas só de agradecimento depois de 2 semanas de rascunhos aprovados). Depende de o token ter a permissão de comentários do Instagram e do Facebook.

### 6.5 Programa "Seguir e interagir" (as 100 contas globais e as do Brasil)

- **Por que:** as 100 contas do Anexo A reúnem laboratórios de IA, big techs e nuvem, empresas de segurança, ferramentas de desenvolvimento, mídia e líderes de tecnologia; todas estão ativas e foram conferidas pela API da Meta em 16/10/2026. Elas **não seguem de volta**. Servem para curar fontes, aparecer em "contas semelhantes" e comentar com qualidade (o comentário aparece para a base delas). O ganho de seguidores **locais** vem mais das contas do Brasil e de Campinas (Anexo B).
- **Ritmo:** 10 contas por dia (7 globais e 3 do Brasil ou de Campinas) por cerca de 15 dias, na ordem da coluna "Dia" dos anexos. A Meta não publica um limite diário; o teto absoluto é de 7.500 contas seguidas. Se o app mostrar "Ação bloqueada", pare por 24 a 48 horas.
- **Rotina de 20 minutos (a partir do dia 5):**

| Quando | Tempo | O que fazer |
|---|---|---|
| Manhã | 5 min | Responder comentários e mensagens recebidos (quanto mais rápido, melhor). |
| 08:30 | 10 min | Mesa de interação: seguir, comentar 3 a 5 posts e curtir 10. |
| Fim da tarde | 5 min | Responder 2 Stories com uma opinião; ver quem interagiu com você. |

- **Regras dos comentários:** pelo menos 12 palavras, acrescentando um dado, uma experiência ou uma pergunta; sem link e sem "segue de volta"; português nas contas do Brasil e inglês curto nas globais; nunca repita o mesmo comentário. Modelos no Anexo C.
- **O que NÃO fazer:** comprar seguidores; usar robôs de curtir, seguir ou comentar; entrar em grupos de engajamento; seguir e deixar de seguir em massa; mandar mensagens em massa para desconhecidos.

## 7. Relatório diário por e-mail (Pacote 0)

**O que vai no e-mail das 21:30:**

1. **Publicações do dia:** tema, título, redes, horário, link e situação (publicado, falhou, pulado), com a origem (Claude, reserva por cron ou reserva Gemini).
2. **Blog:** páginas criadas e aviso enviado aos buscadores.
3. **Seguidores:** Facebook e Instagram hoje, ontem e há 7 dias. O LinkedIn é manual (a API não lê).
4. **Desempenho:** alcance, visualizações, curtidas, comentários, compartilhamentos e salvamentos dos posts de hoje e de ontem (a Meta entrega com 24 a 48 horas de atraso).
5. **Interações:** comentários recebidos, com rascunho de resposta; perguntas e pedidos de contato destacados; menções; e o que a Mesa de interação sugeriu no dia.
6. **Erros e alertas:** falhas e tentativas, token perto de vencer, cota da API do Gemini, reserva acionada e por quê.
7. **Amanhã:** posts previstos e as contas a seguir.

**Como o e-mail chega:**

- **A. Hoje, sem configurar nada:** uma Routine do Claude monta o relatório às 21:30 e envia pelo Gmail que já está conectado (de `techdimbrasil2@gmail.com` para o seu e-mail). Depende de a sessão do Claude estar ativa.
- **B. Independente do Claude (recomendado):** um workflow do GitHub (`log-diario`) monta e envia por SMTP. 👤 Você cria 3 segredos em Settings → Secrets and variables → Actions: `SMTP_USER` (o Gmail que envia), `SMTP_PASSWORD` (senha de app do Google: Conta Google → Segurança → Verificação em duas etapas → Senhas de app) e `EMAIL_TO` (quem recebe). Com o B ativo, a Routine A deixa de enviar, para não duplicar.
- O relatório também fica salvo no branch `assets`, em `registros/AAAA-MM-DD/log-diario.md`, e o diário de seguidores passa a ser gravado todo dia (hoje só há o relatório semanal).

## 8. Contingência: se o Claude parar, o Gemini assume (Pacote 0)

**Resposta curta:** dá. E já existe uma reserva sem IA; falta a camada do Gemini.

| Camada | Quem | Quando | Situação |
|---|---|---|---|
| 1 | Routine do Claude: pauta às 07:03 e disparo dos 4 posts | 07:03, 07:58, 11:06, 14:22, 17:22 | existe |
| 2 | Cron do GitHub publica o que faltar, com RSS e acervo | 08:07, 11:07, 14:23, 17:23 | existe |
| 3 | **Pauta de reserva com Gemini:** se faltar algum dos 4 JSONs do dia ou se algum reprovar no `validar_pauta`, gera os que faltam a partir das manchetes reais (RSS) e do acervo, valida (até 3 tentativas) e grava em `content/diario/AAAA-MM-DD/` | 07:40 | **novo** |
| 4 | **Curadoria com Gemini:** se a chave da Anthropic faltar ou falhar, o `curator.py` tenta o Gemini antes do filtro por palavra-chave | na hora da publicação | **novo** |
| 5 | Filtro por palavra-chave e acervo autoral (dicas e serviços) | último recurso | existe |

- **Mesma qualidade visual:** a pauta do Gemini inclui o bloco do infográfico e passa pelo mesmo `validar_pauta`; se reprovar, o post sai na arte antiga em vez de não sair.
- **Dormente até ter a chave:** sem `GEMINI_API_KEY` nada muda. 👤 Você cria a chave grátis no Google AI Studio (https://aistudio.google.com/apikey) e a coloca em Settings → Secrets and variables → Actions → `GEMINI_API_KEY`. O modelo é configurável (`GEMINI_MODEL`), porque os nomes e as cotas mudam.
- **Limites confirmados:** o plano gratuito é "melhor esforço"; as cotas mudam sem aviso (houve relatos de queda de 250 para 20 pedidos por dia no Flash) e valem por projeto. Por isso o desenho gasta no máximo 8 chamadas por dia e tenta outro modelo se a cota acabar.
- **Privacidade:** no plano gratuito a Google pode usar entradas e saídas para melhorar produtos, com revisão humana. Só enviamos notícias públicas e o acervo da TECHDIM, nunca dados de clientes.
- **Teste sem risco:** modo ensaio do `pauta-reserva`, que mostra o que o Gemini escreveria sem publicar.
- **Aviso no e-mail:** quando a reserva for acionada, o relatório do dia mostra "pauta feita pelo Gemini" e o motivo.
- **O que continua só com o Claude:** a pesquisa profunda da pauta e os ajustes pontuais. O que continua sem o Claude: pauta de reserva, publicação, relatório e Mesa de interação.

## 9. Fase 2 — Conteúdo que gera envio e salvamento (semanas 2 a 4)

- **O que o Instagram pesa:** tempo de exibição, curtidas e envios; curtidas pesam um pouco mais para quem já segue você, e envios pesam mais para quem não segue (Adam Mosseri, janeiro de 2025). Escreva para ser **enviado** ("mande para quem cuida da TI da sua empresa") e **salvo** ("salve esta checklist").
- **Formato:** carrosséis de 6 a 8 slides (capa-gancho, 5 passos, chamada final) e Reels de 15 a 30 segundos com gancho nos 3 primeiros segundos. O infográfico atual continua como post-âncora 3 vezes por semana. Os Trial Reels mostram o vídeo primeiro a quem não segue e podem ser liberados aos seguidores depois.
- **Temas:** manter os 4, mas priorizar Serviços e Notícias no feed do Instagram (0,6 e 0,5 interação por post, contra 0,1) por 2 semanas; Hacker e Conhecimento seguem no LinkedIn e no blog. A comparação decide.
- **Iscas (lead magnets):** o ThreatScanner e a Calculadora de ROI de downtime, que o site já tem, e uma checklist de uma página, "10 sinais de que sua empresa está exposta", entregue pelo WhatsApp. Chamada na legenda: "Comente QUERO ou chame no WhatsApp".
- **Busca:** desde 10/07/2025 posts públicos de contas profissionais podem aparecer no Google. Escreva legendas com as frases que alguém pesquisaria ("backup para empresas em Campinas"), preencha o texto alternativo e use localização "Campinas".
- **Colabs:** 2 por mês com clientes, parceiros ou entidades (o convidado precisa aceitar; o post aparece nos dois perfis).
- **Horários:** testar 3 faixas por 2 semanas (07:30, 12:30 e 18:30) e decidir com os dados do diário.
- **LinkedIn:** 3 posts por semana do fundador, em primeira pessoa, e 1 newsletter por semana com o resumo do blog.

## 10. Fase 3 — Canais que acumulam (meses 2 e 3)

- **Google:** 10 avaliações, postagens semanais, perguntas e respostas. Perfis completos e com avaliações tendem a aparecer mais nas buscas locais; o Google diz que relevância, distância e destaque definem a posição e que não há como pagar por ela.
- **Blog e busca:** Search Console e Bing verificados; 1 artigo pilar por mês ("LGPD para pequena e média empresa: por onde começar"); cada página do blog segue sendo achada por meses, ao contrário de um post de rede social, que vive 1 a 2 dias.
- **Parcerias locais:** contadores e advogados de empresas, associações (ACIC, Ciesp Campinas, Sebrae-SP), lives de 20 minutos sobre LGPD e segurança.
- **Prova social:** 2 estudos de caso anonimizados e depoimentos autorizados.
- **Lista de 50 empresas-alvo em Campinas** (contábeis, clínicas, escritórios de advocacia, indústrias): conecte-se com os decisores no LinkedIn e interaja com os posts deles.
- **Newsletter:** a do LinkedIn avisa conexões e seguidores na primeira edição e depois envia notificação e e-mail a cada edição.
- **Anúncios (opcional):** se D5 for sim, comece com anúncios de mensagem para o WhatsApp, com público em Campinas e região, e meça o custo por contato.

## 11. Quem faz o quê

### Pacote 0 — Relatório e reserva (recomendo começar por aqui; cerca de 1 dia de trabalho meu)

| ID | Item | Quem |
|---|---|---|
| Z1 | Relatório diário: script, workflow `log-diario`, envio por SMTP e Routine ponte pelo Gmail conectado | 🤖 ⚙️ |
| Z2 | Registro diário de seguidores, para atribuir crescimento a posts | 🤖 ⚙️ |
| Z3 | Gemini: cliente da API, `pauta-reserva` (07:40), curadoria com Gemini no `curator.py`, modo ensaio e testes | 🤖 ⚙️ |
| Z4 | Criar `GEMINI_API_KEY` e os segredos de e-mail (`SMTP_USER`, `SMTP_PASSWORD`, `EMAIL_TO`) | 👤 |

### Pacote 1 — assim que você disser "começar" (cerca de 1 dia)

| ID | Item | Quem |
|---|---|---|
| A1 | "Sobre" e descrição longa da Página do Facebook, pela API (guardo o texto antigo para desfazer) | 🤖 |
| A2 | Site: título, descrição, Open Graph, JSON-LD com `sameAs` e "Campinas" | 🤖 |
| A3 | Página de links para a bio (`/links/`) com WhatsApp, diagnóstico, blog, ThreatScanner e ROI, com UTM | 🤖 |
| A4 | Medição de visitas sem cookies no site (preciso do código do snippet) | 🤖 + 👤 |
| A5 | Rodapé "Siga a TECHDIM" nas páginas do blog | 🤖 |
| — | Perfis nos apps (seção 4): Instagram, Facebook, LinkedIn, Google, WhatsApp Business | 👤 |

### Pacote 2 — semanas 1 e 2

| ID | Item | Quem |
|---|---|---|
| B1 | Mesa de interação diária (08:30): contas a seguir, posts a comentar com rascunho, curtidas, por e-mail | 🤖 ⚙️ |
| B2 | Rascunhos de resposta aos comentários dos seus posts e alerta de lead | 🤖 ⚙️ |
| B3 | Carrossel de vários slides nas 3 redes | 🤖 |
| B4 | Localização "Campinas" nos posts do Instagram e do Facebook | 🤖 |
| — | Seguir 10 contas por dia e a rotina de 20 minutos | 👤 |

### Pacote 3 — semanas 3 e 4

| ID | Item | Quem |
|---|---|---|
| C1 | Reels a partir dos infográficos (15 a 30 s) e teste de Trial Reels | 🤖 |
| C2 | Rascunho semanal da newsletter (os 5 melhores itens do relatório) | 🤖 |
| C3 | Teste de horários (3 faixas) com os dados do diário | 🤖 ⚙️ |
| — | Google: avaliações e postagens; parcerias locais; lista de 50 empresas-alvo | 👤 |

## 12. Metas e medição

Estimativas minhas; dependem da execução. Revisamos no dia 30.

| Métrica | Hoje | 30 dias | 60 dias | 90 dias |
|---|---|---|---|---|
| Instagram, seguidores | 20 | 80 a 120 | 150 a 250 | 250 a 400 |
| Facebook, seguidores | 47 | 90 a 130 | 130 a 200 | 150 a 250 |
| LinkedIn (fundador), novas conexões | — | +100 | +200 | +300 |
| Instagram, alcance médio por post | cerca de 1 | 20 a 50 | 50 a 150 | 100 a 300 |
| Instagram, envios e salvamentos por semana | 0 | 5 a 10 | 15 a 30 | 30 a 60 |
| Avaliações no Google | a conferir | 5 | 8 | 10 ou mais |
| Contatos qualificados por mês (WhatsApp e site) | a conferir | 2 a 4 | 4 a 8 | 8 a 12 |

**Como medir:** o relatório diário (seção 7) traz o dia; o relatório semanal de segunda-feira traz a tendência, com a variação sobre a semana anterior (a primeira medição entra no relatório de 19/10). O LinkedIn se acompanha em Perfil → Análises. As visitas ao site por origem vêm da medição do item A4. Os contatos você marca no WhatsApp Business com a etiqueta "novo".

**Regras de decisão:** no dia 30, manter o que aumentou envios e salvamentos e cortar o que ficou abaixo da mediana; no dia 60, rever o volume de posts; no dia 90, relatório completo e novo plano.

## 13. Cronograma

| Quando | Foco | Entregas |
|---|---|---|
| Dia 1 e 2 | Pacote 0 e Pacote 1 | Relatório diário e reserva com Gemini prontos; descrições nos 5 canais; site com título, descrição e `sameAs`; página de links; medição de visitas |
| Semana 1 | Semeadura | 100 convites; círculo de 10; post de lançamento no LinkedIn; 10 contas seguidas por dia |
| Semana 2 | Interação | Mesa de interação diária; respostas aos comentários; carrossel de vários slides; localização nos posts |
| Semanas 3 e 4 | Formato | Reels e Trial Reels; newsletter semanal; teste de horários; revisão do dia 30 |
| Mês 2 | Autoridade local | Google com avaliações; 2 colabs; 1 artigo pilar; parcerias com contadores e advogados |
| Mês 3 | Escala | Estudos de caso; lista de 50 empresas-alvo; decisão sobre anúncios; relatório do dia 90 |

## 14. Riscos e limites (o que está confirmado)

- **Instagram:** nome, bio e link só mudam no app; a API não edita legendas (testado até a Graph API v26.0); seguir, curtir e comentar em contas de terceiros não existe na API e é ação de uma pessoa, no app.
- **Facebook:** o cadastro antigo do campo Site foi feito à mão e a API não o remove; categoria, endereço, horário e nome de usuário são ajustes no app.
- **LinkedIn:** a API do projeto não lê métricas nem edita perfis; tudo manual. Automação de engajamento é proibida.
- **Gemini gratuito:** cotas instáveis e uso dos dados pela Google no plano gratuito; por isso é reserva, não substituto.
- **Limites de texto:** Instagram, nome 30 e bio 150; LinkedIn, título 220 e slogan da Página 120; Google, descrição abaixo de 750, sem links; WhatsApp Business, limite não confirmado (texto abaixo de 250). O "Sobre" da Página do LinkedIn aparece com limite de 2.000 em um material e 1.500 em outro: o texto proposto tem menos de 1.500.
- **Estimativas:** metas e prazos são minhas. O que é fonte oficial e o que é prática de mercado está no Anexo D.

---

## Anexo A — 100 contas globais para seguir

100 contas, todas conferidas pela API da Meta em 16/10/2026 (conta profissional, pública e com post nos últimos 45 dias), por categoria e do maior para o menor número de seguidores (as de maior relevância para TI, nuvem e segurança entram primeiro em cada categoria). Siga 7 por dia, na ordem da coluna "Dia", junto com 3 do Anexo B. Confira o selo azul de verificação ao abrir cada perfil.

| # | Dia | Categoria | Conta | Nome na conta | Seguidores | Último post |
|---|---|---|---|---|---|---|
| 1 | Dia 1 | IA · laboratórios e produtos | [@chatgpt](https://www.instagram.com/chatgpt/) | ChatGPT | 7.711.269 | 2026-10-15 |
| 2 | Dia 1 | IA · laboratórios e produtos | [@openai](https://www.instagram.com/openai/) | OpenAI | 6.663.086 | 2026-10-14 |
| 3 | Dia 1 | IA · laboratórios e produtos | [@meta.ai](https://www.instagram.com/meta.ai/) | Meta AI | 4.859.391 | 2026-09-27 |
| 4 | Dia 1 | IA · laboratórios e produtos | [@canva](https://www.instagram.com/canva/) | Canva | 2.625.876 | 2026-10-15 |
| 5 | Dia 1 | IA · laboratórios e produtos | [@claudeai](https://www.instagram.com/claudeai/) | Claude by Anthropic | 2.248.708 | 2026-10-15 |
| 6 | Dia 1 | IA · laboratórios e produtos | [@adobe](https://www.instagram.com/adobe/) | Adobe | 2.139.126 | 2026-10-12 |
| 7 | Dia 1 | IA · laboratórios e produtos | [@googlegemini](https://www.instagram.com/googlegemini/) | Google Gemini | 1.606.300 | 2026-10-15 |
| 8 | Dia 2 | IA · laboratórios e produtos | [@perplexity](https://www.instagram.com/perplexity/) | Perplexity | 1.223.009 | 2026-10-08 |
| 9 | Dia 2 | IA · laboratórios e produtos | [@microsoftcopilot](https://www.instagram.com/microsoftcopilot/) | Microsoft Copilot | 1.068.753 | 2026-10-15 |
| 10 | Dia 2 | IA · laboratórios e produtos | [@figma](https://www.instagram.com/figma/) | Figma | 970.343 | 2026-10-15 |
| 11 | Dia 2 | IA · laboratórios e produtos | [@elevenlabs](https://www.instagram.com/elevenlabs/) | ElevenLabs | 606.671 | 2026-10-15 |
| 12 | Dia 2 | IA · laboratórios e produtos | [@lumalabsai](https://www.instagram.com/lumalabsai/) | Luma | 503.460 | 2026-10-15 |
| 13 | Dia 2 | IA · laboratórios e produtos | [@notionhq](https://www.instagram.com/notionhq/) | Notion | 493.547 | 2026-10-09 |
| 14 | Dia 2 | IA · laboratórios e produtos | [@nvidiaai](https://www.instagram.com/nvidiaai/) | NVIDIA AI | 434.526 | 2026-10-15 |
| 15 | Dia 3 | IA · laboratórios e produtos | [@googledeepmind](https://www.instagram.com/googledeepmind/) | Google DeepMind | 376.847 | 2026-10-14 |
| 16 | Dia 3 | IA · laboratórios e produtos | [@grok](https://www.instagram.com/grok/) | Grok | 264.539 | 2026-10-08 |
| 17 | Dia 3 | IA · laboratórios e produtos | [@replit](https://www.instagram.com/replit/) | Replit | 208.978 | 2026-10-15 |
| 18 | Dia 3 | IA · laboratórios e produtos | [@heygen_official](https://www.instagram.com/heygen_official/) | HeyGen | 150.037 | 2026-10-15 |
| 19 | Dia 3 | IA · laboratórios e produtos | [@pika_labs](https://www.instagram.com/pika_labs/) | Pika | 114.801 | 2026-10-07 |
| 20 | Dia 3 | IA · laboratórios e produtos | [@deeplearningai](https://www.instagram.com/deeplearningai/) | DeepLearning.AI | 113.962 | 2026-10-16 |
| 21 | Dia 3 | IA · laboratórios e produtos | [@zapier](https://www.instagram.com/zapier/) | Zapier | 104.533 | 2026-10-15 |
| 22 | Dia 4 | IA · laboratórios e produtos | [@stability.ai](https://www.instagram.com/stability.ai/) | Stability AI | 45.166 | 2026-09-15 |
| 23 | Dia 4 | Cibersegurança | [@hackthebox](https://www.instagram.com/hackthebox/) | Hack The Box | 285.443 | 2026-10-15 |
| 24 | Dia 4 | Cibersegurança | [@thehackernews](https://www.instagram.com/thehackernews/) | The Hacker News | 181.427 | 2026-10-16 |
| 25 | Dia 4 | Cibersegurança | [@kasperskylab](https://www.instagram.com/kasperskylab/) | Kaspersky / Cybersecurity | 130.732 | 2026-10-09 |
| 26 | Dia 4 | Cibersegurança | [@cisagov](https://www.instagram.com/cisagov/) | Cybersecurity & Infrastructure Security Agency | 111.465 | 2026-10-13 |
| 27 | Dia 4 | Cibersegurança | [@nist](https://www.instagram.com/nist/) | National Institute of Standards and Technology | 79.738 | 2026-10-13 |
| 28 | Dia 4 | Cibersegurança | [@splunk](https://www.instagram.com/splunk/) | Splunk | 60.802 | 2026-10-14 |
| 29 | Dia 5 | Cibersegurança | [@hacker0x01](https://www.instagram.com/hacker0x01/) | HackerOne | 59.337 | 2026-10-15 |
| 30 | Dia 5 | Cibersegurança | [@fortinet](https://www.instagram.com/fortinet/) | Fortinet | 56.034 | 2026-10-09 |
| 31 | Dia 5 | Cibersegurança | [@paloaltontwks](https://www.instagram.com/paloaltontwks/) | Palo Alto Networks | 51.828 | 2026-10-15 |
| 32 | Dia 5 | Cibersegurança | [@sophossecurity](https://www.instagram.com/sophossecurity/) | Sophos | 43.388 | 2026-10-13 |
| 33 | Dia 5 | Cibersegurança | [@bitdefender](https://www.instagram.com/bitdefender/) | Bitdefender | 35.370 | 2026-10-14 |
| 34 | Dia 5 | Cibersegurança | [@eset](https://www.instagram.com/eset/) | ESET | 34.933 | 2026-10-15 |
| 35 | Dia 5 | Cibersegurança | [@crowdstrike](https://www.instagram.com/crowdstrike/) | CrowdStrike | 34.630 | 2026-10-15 |
| 36 | Dia 6 | Cibersegurança | [@bugcrowd](https://www.instagram.com/bugcrowd/) | Bugcrowd | 31.399 | 2026-10-12 |
| 37 | Dia 6 | Cibersegurança | [@1password](https://www.instagram.com/1password/) | 1Password | 28.461 | 2026-10-14 |
| 38 | Dia 6 | Cibersegurança | [@zscalerinc](https://www.instagram.com/zscalerinc/) | Zscaler | 10.533 | 2026-10-14 |
| 39 | Dia 6 | Cibersegurança | [@microsoftsecurity](https://www.instagram.com/microsoftsecurity/) | Microsoft Security | 8.129 | 2026-10-08 |
| 40 | Dia 6 | Cibersegurança | [@proofpoint](https://www.instagram.com/proofpoint/) | Proofpoint | 5.923 | 2026-10-15 |
| 41 | Dia 6 | Cibersegurança | [@rapid7](https://www.instagram.com/rapid7/) | Rapid7 | 5.878 | 2026-09-21 |
| 42 | Dia 6 | Cibersegurança | [@owasp](https://www.instagram.com/owasp/) | OWASP Foundation | 2.075 | 2026-09-22 |
| 43 | Dia 7 | Big Tech e nuvem | [@apple](https://www.instagram.com/apple/) | apple | 38.080.361 | 2026-10-16 |
| 44 | Dia 7 | Big Tech e nuvem | [@google](https://www.instagram.com/google/) | Google | 15.786.674 | 2026-10-15 |
| 45 | Dia 7 | Big Tech e nuvem | [@amazon](https://www.instagram.com/amazon/) | Amazon | 6.890.738 | 2026-10-15 |
| 46 | Dia 7 | Big Tech e nuvem | [@meta](https://www.instagram.com/meta/) | Meta | 6.248.608 | 2026-10-15 |
| 47 | Dia 7 | Big Tech e nuvem | [@microsoft](https://www.instagram.com/microsoft/) | Microsoft | 4.559.017 | 2026-10-14 |
| 48 | Dia 7 | Big Tech e nuvem | [@nvidia](https://www.instagram.com/nvidia/) | NVIDIA | 3.010.428 | 2026-10-15 |
| 49 | Dia 7 | Big Tech e nuvem | [@samsung](https://www.instagram.com/samsung/) | Samsung | 2.839.264 | 2026-10-16 |
| 50 | Dia 8 | Big Tech e nuvem | [@windows](https://www.instagram.com/windows/) | Windows | 2.574.957 | 2026-10-15 |
| 51 | Dia 8 | Big Tech e nuvem | [@amd](https://www.instagram.com/amd/) | AMD | 2.099.116 | 2026-10-15 |
| 52 | Dia 8 | Big Tech e nuvem | [@intel](https://www.instagram.com/intel/) | Intel | 1.843.714 | 2026-10-15 |
| 53 | Dia 8 | Big Tech e nuvem | [@hp](https://www.instagram.com/hp/) | HP | 1.831.586 | 2026-10-09 |
| 54 | Dia 8 | Big Tech e nuvem | [@amazonwebservices](https://www.instagram.com/amazonwebservices/) | AWS | 1.292.337 | 2026-10-13 |
| 55 | Dia 8 | Big Tech e nuvem | [@ibm](https://www.instagram.com/ibm/) | IBM | 746.358 | 2026-10-13 |
| 56 | Dia 8 | Big Tech e nuvem | [@cisco](https://www.instagram.com/cisco/) | Cisco | 650.867 | 2026-10-10 |
| 57 | Dia 9 | Big Tech e nuvem | [@googlecloud](https://www.instagram.com/googlecloud/) | Google Cloud | 499.115 | 2026-10-13 |
| 58 | Dia 9 | Big Tech e nuvem | [@oracle](https://www.instagram.com/oracle/) | Oracle | 402.038 | 2026-10-09 |
| 59 | Dia 9 | Big Tech e nuvem | [@sap](https://www.instagram.com/sap/) | SAP | 376.034 | 2026-10-13 |
| 60 | Dia 9 | Big Tech e nuvem | [@salesforce](https://www.instagram.com/salesforce/) | Salesforce | 344.260 | 2026-10-15 |
| 61 | Dia 9 | Big Tech e nuvem | [@microsoftazure](https://www.instagram.com/microsoftazure/) | Microsoft Azure | 268.259 | 2026-10-12 |
| 62 | Dia 9 | Big Tech e nuvem | [@delltech](https://www.instagram.com/delltech/) | Dell Technologies | 173.057 | 2026-10-14 |
| 63 | Dia 9 | Big Tech e nuvem | [@red_hat](https://www.instagram.com/red_hat/) | Red Hat | 141.585 | 2026-10-15 |
| 64 | Dia 10 | Big Tech e nuvem | [@databricksinc](https://www.instagram.com/databricksinc/) | Databricks | 119.738 | 2026-10-12 |
| 65 | Dia 10 | Big Tech e nuvem | [@servicenow](https://www.instagram.com/servicenow/) | ServiceNow | 87.102 | 2026-10-15 |
| 66 | Dia 10 | Big Tech e nuvem | [@cloudflare](https://www.instagram.com/cloudflare/) | Cloudflare | 76.830 | 2026-10-13 |
| 67 | Dia 10 | Big Tech e nuvem | [@hpe](https://www.instagram.com/hpe/) | HPE | 72.661 | 2026-10-15 |
| 68 | Dia 10 | Dev, DevOps e SaaS | [@android](https://www.instagram.com/android/) | Android | 2.031.161 | 2026-10-15 |
| 69 | Dia 10 | Dev, DevOps e SaaS | [@github](https://www.instagram.com/github/) | GitHub | 934.082 | 2026-10-14 |
| 70 | Dia 10 | Dev, DevOps e SaaS | [@hubspot](https://www.instagram.com/hubspot/) | HubSpot | 661.130 | 2026-10-15 |
| 71 | Dia 11 | Dev, DevOps e SaaS | [@mongodb](https://www.instagram.com/mongodb/) | MongoDB | 183.155 | 2026-10-15 |
| 72 | Dia 11 | Dev, DevOps e SaaS | [@atlassian](https://www.instagram.com/atlassian/) | Atlassian | 149.440 | 2026-10-14 |
| 73 | Dia 11 | Dev, DevOps e SaaS | [@jetbrains](https://www.instagram.com/jetbrains/) | JetBrains | 139.665 | 2026-10-14 |
| 74 | Dia 11 | Dev, DevOps e SaaS | [@slackhq](https://www.instagram.com/slackhq/) | Slack | 107.960 | 2026-10-14 |
| 75 | Dia 11 | Dev, DevOps e SaaS | [@gitlab](https://www.instagram.com/gitlab/) | GitLab | 102.876 | 2026-10-15 |
| 76 | Dia 11 | Dev, DevOps e SaaS | [@datadoghq](https://www.instagram.com/datadoghq/) | Datadog | 96.680 | 2026-10-14 |
| 77 | Dia 11 | Dev, DevOps e SaaS | [@twilio](https://www.instagram.com/twilio/) | Twilio | 72.858 | 2026-10-15 |
| 78 | Dia 12 | Dev, DevOps e SaaS | [@dockerinc](https://www.instagram.com/dockerinc/) | Moby Dock | 26.187 | 2026-10-02 |
| 79 | Dia 12 | Dev, DevOps e SaaS | [@pagerduty](https://www.instagram.com/pagerduty/) | PagerDuty Inc | 2.401 | 2026-10-13 |
| 80 | Dia 12 | Mídia e líderes de tecnologia | [@zuck](https://www.instagram.com/zuck/) | Mark Zuckerberg | 17.330.399 | 2026-10-12 |
| 81 | Dia 12 | Mídia e líderes de tecnologia | [@sundarpichai](https://www.instagram.com/sundarpichai/) | Sundar Pichai | 5.614.879 | 2026-10-13 |
| 82 | Dia 12 | Mídia e líderes de tecnologia | [@mkbhd](https://www.instagram.com/mkbhd/) | Marques Brownlee | 5.287.730 | 2026-10-02 |
| 83 | Dia 12 | Mídia e líderes de tecnologia | [@wired](https://www.instagram.com/wired/) | WIRED | 2.369.744 | 2026-10-15 |
| 84 | Dia 12 | Mídia e líderes de tecnologia | [@techcrunch](https://www.instagram.com/techcrunch/) | TechCrunch | 1.740.602 | 2026-10-15 |
| 85 | Dia 13 | Mídia e líderes de tecnologia | [@verge](https://www.instagram.com/verge/) | The Verge | 1.686.351 | 2026-10-16 |
| 86 | Dia 13 | Mídia e líderes de tecnologia | [@cnet](https://www.instagram.com/cnet/) | CNET | 1.468.193 | 2026-10-16 |
| 87 | Dia 13 | Mídia e líderes de tecnologia | [@lexfridman](https://www.instagram.com/lexfridman/) | Lex Fridman | 1.257.866 | 2026-10-14 |
| 88 | Dia 13 | Mídia e líderes de tecnologia | [@technologyreview](https://www.instagram.com/technologyreview/) | MIT Technology Review | 1.137.392 | 2026-10-10 |
| 89 | Dia 13 | Mídia e líderes de tecnologia | [@mashable](https://www.instagram.com/mashable/) | Mashable | 982.809 | 2026-10-15 |
| 90 | Dia 13 | Mídia e líderes de tecnologia | [@ycombinator](https://www.instagram.com/ycombinator/) | Y Combinator | 756.932 | 2026-10-15 |
| 91 | Dia 13 | Mídia e líderes de tecnologia | [@a16z](https://www.instagram.com/a16z/) | Andreessen Horowitz | 220.867 | 2026-10-15 |
| 92 | Dia 14 | Mídia e líderes de tecnologia | [@hackaday](https://www.instagram.com/hackaday/) | Hackaday | 172.456 | 2026-10-15 |
| 93 | Dia 14 | Mídia e líderes de tecnologia | [@thenextweb](https://www.instagram.com/thenextweb/) | TNW | 104.439 | 2026-10-15 |
| 94 | Dia 14 | Mídia e líderes de tecnologia | [@producthunt](https://www.instagram.com/producthunt/) | Product Hunt | 49.637 | 2026-09-25 |
| 95 | Dia 14 | Mídia e líderes de tecnologia | [@arstechnica](https://www.instagram.com/arstechnica/) | Ars Technica | 44.795 | 2026-10-15 |
| 96 | Dia 14 | Pesquisa e educação | [@stanford](https://www.instagram.com/stanford/) | Stanford University | 1.516.371 | 2026-10-15 |
| 97 | Dia 14 | Pesquisa e educação | [@coursera](https://www.instagram.com/coursera/) | Coursera | 1.505.749 | 2026-10-15 |
| 98 | Dia 14 | Pesquisa e educação | [@mit](https://www.instagram.com/mit/) | MIT | 1.134.078 | 2026-10-14 |
| 99 | Dia 15 | Pesquisa e educação | [@udacity](https://www.instagram.com/udacity/) | Udacity | 105.284 | 2026-10-12 |
| 100 | Dia 15 | Pesquisa e educação | [@mit_csail](https://www.instagram.com/mit_csail/) | MIT CSAIL | 49.264 | 2026-10-15 |

## Anexo B — Contas do Brasil e de Campinas (maior ganho local)

34 contas do Brasil e de Campinas, conferidas do mesmo modo, com as de Campinas e região primeiro. Siga 3 por dia, na ordem da coluna "Dia", junto com 7 do Anexo A, e comente nelas primeiro: é daqui que vêm os seguidores locais. O ACIC Campinas e o CPQD não têm conta profissional que a API consiga conferir: procure-os pelo nome no app. Softex Campinas, APDADOS (privacidade e LGPD) e Internet Segura BR ficaram sem conferir por limite de uso da API e entram na próxima rodada.

| # | Dia | Categoria | Conta | Nome na conta | Seguidores | Último post |
|---|---|---|---|---|---|---|
| 1 | Dia 1 | Entidades e ecossistema (BR e Campinas) | [@sebraesp](https://www.instagram.com/sebraesp/) | Sebrae SP | 479.350 | 2026-10-15 |
| 2 | Dia 1 | Entidades e ecossistema (BR e Campinas) | [@ciesp.campinas](https://www.instagram.com/ciesp.campinas/) | CIESP Campinas | 2.679 | 2026-10-15 |
| 3 | Dia 1 | Entidades e ecossistema (BR e Campinas) | [@unicamp.oficial](https://www.instagram.com/unicamp.oficial/) | Unicamp | 352.062 | 2026-10-15 |
| 4 | Dia 2 | Entidades e ecossistema (BR e Campinas) | [@unicamp.ic](https://www.instagram.com/unicamp.ic/) | Instituto de Computação | 9.732 | 2026-10-14 |
| 5 | Dia 2 | Entidades e ecossistema (BR e Campinas) | [@inovaunicamp](https://www.instagram.com/inovaunicamp/) | Agência de Inovação da Unicamp | 13.680 | 2026-10-15 |
| 6 | Dia 2 | Entidades e ecossistema (BR e Campinas) | [@prefcampinas](https://www.instagram.com/prefcampinas/) | Prefeitura de Campinas | 192.670 | 2026-10-15 |
| 7 | Dia 3 | Entidades e ecossistema (BR e Campinas) | [@sebrae](https://www.instagram.com/sebrae/) | Sebrae Nacional | 2.328.295 | 2026-10-15 |
| 8 | Dia 3 | Entidades e ecossistema (BR e Campinas) | [@abstartups](https://www.instagram.com/abstartups/) | Abstartups | 64.090 | 2026-10-15 |
| 9 | Dia 3 | Entidades e ecossistema (BR e Campinas) | [@nicbr](https://www.instagram.com/nicbr/) | NIC.br | 34.312 | 2026-10-15 |
| 10 | Dia 4 | Entidades e ecossistema (BR e Campinas) | [@softex.nacional](https://www.instagram.com/softex.nacional/) | Softex Nacional | 14.081 | 2026-10-15 |
| 11 | Dia 4 | Entidades e ecossistema (BR e Campinas) | [@ciesp.oficial](https://www.instagram.com/ciesp.oficial/) | Ciesp | 7.838 | 2026-10-14 |
| 12 | Dia 4 | Entidades e ecossistema (BR e Campinas) | [@brasscomoficial](https://www.instagram.com/brasscomoficial/) | Brasscom | 7.608 | 2026-10-15 |
| 13 | Dia 5 | Empresas de tecnologia (BR) | [@googlebrasil](https://www.instagram.com/googlebrasil/) | Google Brasil | 1.026.955 | 2026-10-15 |
| 14 | Dia 5 | Empresas de tecnologia (BR) | [@rdstation](https://www.instagram.com/rdstation/) | RD Station | 455.174 | 2026-10-15 |
| 15 | Dia 5 | Empresas de tecnologia (BR) | [@intelbras](https://www.instagram.com/intelbras/) | intelbras | 334.791 | 2026-10-15 |
| 16 | Dia 6 | Empresas de tecnologia (BR) | [@contaazul](https://www.instagram.com/contaazul/) | Conta Azul / Sistema de Gestão Financeira | 277.210 | 2026-10-15 |
| 17 | Dia 6 | Empresas de tecnologia (BR) | [@totvs](https://www.instagram.com/totvs/) | TOTVS | 259.345 | 2026-10-16 |
| 18 | Dia 6 | Empresas de tecnologia (BR) | [@microsoftbr](https://www.instagram.com/microsoftbr/) | Microsoft Brasil | 203.660 | 2026-10-15 |
| 19 | Dia 7 | Empresas de tecnologia (BR) | [@redhatlatam](https://www.instagram.com/redhatlatam/) | Red Hat Latinoamérica | 76.868 | 2026-10-10 |
| 20 | Dia 7 | Empresas de tecnologia (BR) | [@locaweb](https://www.instagram.com/locaweb/) | Locaweb | 51.282 | 2026-10-15 |
| 21 | Dia 7 | Empresas de tecnologia (BR) | [@kasperskybr](https://www.instagram.com/kasperskybr/) | KasperskyBR | 47.864 | 2026-10-14 |
| 22 | Dia 8 | Empresas de tecnologia (BR) | [@stefanini](https://www.instagram.com/stefanini/) | Stefanini Brasil | 29.036 | 2026-10-15 |
| 23 | Dia 8 | Empresas de tecnologia (BR) | [@zupinnovation](https://www.instagram.com/zupinnovation/) | Zup Innovation | 22.118 | 2026-10-15 |
| 24 | Dia 8 | Empresas de tecnologia (BR) | [@positivotecnologia](https://www.instagram.com/positivotecnologia/) | Positivo TecnologIA | 14.450 | 2026-10-15 |
| 25 | Dia 9 | Empresas de tecnologia (BR) | [@sophoslatam](https://www.instagram.com/sophoslatam/) | Sophos Latam | 1.431 | 2026-09-21 |
| 26 | Dia 9 | Mídia de tecnologia e negócios (BR) | [@exame](https://www.instagram.com/exame/) | Exame | 3.651.992 | 2026-10-16 |
| 27 | Dia 9 | Mídia de tecnologia e negócios (BR) | [@revistapegn](https://www.instagram.com/revistapegn/) | Revista PEGN | 1.521.741 | 2026-10-15 |
| 28 | Dia 10 | Mídia de tecnologia e negócios (BR) | [@tecmundo](https://www.instagram.com/tecmundo/) | TecMundo | 1.051.361 | 2026-10-16 |
| 29 | Dia 10 | Mídia de tecnologia e negócios (BR) | [@olhardigital](https://www.instagram.com/olhardigital/) | Olhar Digital | 591.572 | 2026-10-15 |
| 30 | Dia 10 | Mídia de tecnologia e negócios (BR) | [@canaltech](https://www.instagram.com/canaltech/) | Canaltech | 576.387 | 2026-10-15 |
| 31 | Dia 11 | Mídia de tecnologia e negócios (BR) | [@epocanegocios](https://www.instagram.com/epocanegocios/) | Época Negócios | 562.021 | 2026-10-15 |
| 32 | Dia 11 | Mídia de tecnologia e negócios (BR) | [@tecnoblog](https://www.instagram.com/tecnoblog/) | Tecnoblog | 144.175 | 2026-10-15 |
| 33 | Dia 11 | Mídia de tecnologia e negócios (BR) | [@showmetech](https://www.instagram.com/showmetech/) | Showmetech | 16.901 | 2026-10-15 |
| 34 | Dia 12 | Mídia de tecnologia e negócios (BR) | [@meiobit](https://www.instagram.com/meiobit/) | Meio Bit | 3.836 | 2026-10-15 |

## Anexo C — Modelos prontos

**C1. Convite por WhatsApp (individual)**

```
Oi, [nome]! Tudo bem? Estou dando mais voz à TECHDIM nas redes: dicas diárias de segurança e TI para empresas, sem enrolação. Se puder seguir e, quando fizer sentido, mandar um post para quem cuida da TI da sua empresa, ajuda muito. Instagram: instagram.com/techdimbr · Site: techdimbr.github.io/techdimbr. Obrigado!
```

**C2. Post de lançamento no LinkedIn (perfil do fundador)**

```
Sua empresa já restaurou um backup de verdade?

A maioria só descobre que o backup não funciona no dia em que precisa dele.

Sou [seu nome], engenheiro de cibersegurança e fundador da TECHDIM, em Campinas. A partir de hoje publico aqui, todo dia, o que vejo na prática protegendo a TI de empresas:
• alertas de vulnerabilidades que importam para quem tem poucos recursos
• passo a passo de hardening, backup e acesso remoto seguro
• IA rodando dentro da empresa, sem mandar dados para fora

Se você cuida de uma empresa, ou da TI de uma, siga e me conte o que mais tira o seu sono. Respondo todos os comentários.

#cibersegurança #TI #LGPD #Campinas
```

**C3. Mensagem a parceiros (contadores e advogados)**

```
Olá, [nome]! Atendemos empresas que também são suas clientes, e vejo uma parceria simples: indicações cruzadas e uma live de 20 minutos juntos sobre LGPD e segurança para pequenas e médias empresas. Posso te mostrar a ideia em 15 minutos esta semana?
```

**C4. Pedido de avaliação no Google**

```
Oi, [nome]! Obrigado por confiar na TECHDIM. Se o nosso atendimento ajudou, uma avaliação no Google leva 1 minuto e ajuda outras empresas de Campinas a nos encontrarem: [link da avaliação]. Muito obrigado!
```

**C5. Modelos de comentário (adapte sempre ao post)**

- Complemento: `Ótimo ponto. Na prática com pequenas e médias empresas, o que mais vemos é [situação]. Um passo simples que reduz o risco é [ação].`
- Pergunta: `Como vocês tratam [tema] em ambientes com poucos recursos de TI? Aqui em Campinas é um desafio comum.`
- Dado: `Vale lembrar que [fato técnico]. Isso muda a decisão quando [contexto].`
- Conta do Brasil: `Parabéns pela iniciativa! Conteúdo assim ajuda muito as empresas da região, que ainda tratam [problema] como "coisa de grande empresa".`
- Conta global, em inglês curto: `Great breakdown. For small businesses, the quick win is [action].`

**C6. Resposta a quem comenta ou manda mensagem**

```
Obrigado por comentar! Se quiser, te mando a checklist completa. Me diga o tamanho da sua empresa (quantos computadores e servidores) para eu indicar por onde começar.
```

## Anexo D — Fontes

**Oficiais ou de primeira mão**

- Instagram, limite de contas seguidas (7.500): https://help.instagram.com/408167069251249/
- Instagram, Termos de Uso (acesso automatizado proibido): https://help.instagram.com/581066165581870/
- Instagram, curtidas, seguidas e comentários falsos por aplicativos de terceiros: https://about.instagram.com/blog/announcements/reducing-inauthentic-activity-on-instagram
- Instagram, restrição por entregar login a aplicativos de terceiros: https://help.instagram.com/740480200552298/
- Meta, política de comportamento inautêntico: https://transparency.meta.com/policies/community-standards/inauthentic-behavior/
- LinkedIn, software e extensões proibidos: https://www.linkedin.com/help/linkedin/answer/a1341387
- LinkedIn, atividade automatizada: https://www.linkedin.com/help/linkedin/answer/a1340567
- LinkedIn, Acordo de Usuário: https://www.linkedin.com/legal/user-agreement
- Facebook, convidar amigos para seguir uma Página: https://www.facebook.com/help/174333482624856 e https://www.facebook.com/business/help/2707286436257418
- Meta, Business Discovery (leitura de contas profissionais, base da Mesa de interação): https://developers.facebook.com/docs/instagram-api/business-discovery
- Meta, resposta a comentários no Instagram: https://developers.facebook.com/documentation/instagram-platform/instagram-graph-api/reference/ig-comment/replies
- Meta, Page Public Content Access (ler posts de outras Páginas): https://developers.facebook.com/docs/graph-api/reference/page/feed/
- Google Perfil da Empresa, dicas de posição local: https://support.google.com/business/answer/7091
- Google Perfil da Empresa, descrição (menos de 750 caracteres, sem links): https://support.google.com/business/answer/3039617
- Gemini API, termos (uso de dados no plano gratuito): https://ai.google.dev/gemini-api/terms
- Gemini API, preços e cotas: https://ai.google.dev/gemini-api/docs/pricing
- LinkedIn, newsletters: https://www.linkedin.com/help/linkedin/answer/a517925
- LinkedIn, convites para seguir uma Página: https://www.linkedin.com/help/linkedin/answer/a6202478

**Imprensa especializada (relatam anúncios da Meta)**

- Sinais do Instagram (Adam Mosseri, 22/01/2025): https://www.socialmediatoday.com/news/instagram-shares-algorithm-2025/738034/
- Trial Reels: https://www.socialmediatoday.com/news/instagram-launches-trial-reels-for-audience-sampling/735136/
- Até 5 links na bio: https://searchengineland.com/instagram-now-allows-up-to-5-links-in-bio-395742
- Posts do Instagram indexados pelo Google desde 10/07/2025: https://ppc.land/instagram-content-becomes-searchable-on-google-starting-july-10/

**Prática de mercado (direção, não garantia)**

- Limites de caracteres: https://www.outfy.com/blog/instagram-character-limit/ e https://typecount.com/blog/social-media-character-limits
- Colabs do Instagram (limite de colaboradores varia entre guias): https://www.shopify.com/blog/how-to-collab-post-on-instagram
- Alcance maior do perfil pessoal que da página da empresa no LinkedIn, ritmo de postagem e metas de crescimento: estimativas deste plano.
