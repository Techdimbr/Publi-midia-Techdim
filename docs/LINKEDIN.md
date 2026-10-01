# LinkedIn — passo a passo

Objetivo: a automação publicar no LinkedIn com imagem, legenda e primeiro
comentário, como já faz no Facebook e no Instagram. Leva uns 15 minutos para
publicar como **perfil pessoal**. Publicar como **página da empresa** depende de
uma aprovação do LinkedIn (passo 7).

Seu app: Client ID `77h1pbpeug4k88`.

## 0. Antes de tudo: troque o Client Secret

O Client Secret apareceu no chat, então considere-o exposto. A automação **não
usa** esse segredo, então trocar não quebra nada.

1. Abra [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps) e clique no seu app.
2. Aba **Auth** → ao lado de *Primary Client Secret*, **Generate a new Client Secret**.
3. Guarde o novo valor no seu gerenciador de senhas. Não cole em chat.

## 1. Habilite os produtos do app

Aba **Products** do app → **Request access** em:

| Produto | Para quê | Aprovação |
|---|---|---|
| **Share on LinkedIn** | libera o escopo `w_member_social`: publicar como você | imediata |
| **Sign In with LinkedIn using OpenID Connect** | libera `openid` e `profile`: o script "Descobrir IDs" descobre seu URN | imediata |
| **Community Management API** | publicar como **página da empresa** (`w_organization_social`) | passa por análise do LinkedIn |

Aguarde até os dois primeiros aparecerem em **Added products**.

## 2. Gere o token de acesso

1. Abra o [Token Generator](https://www.linkedin.com/developers/tools/oauth/token-generator) do LinkedIn.
2. Escolha o seu app e o fluxo **Member authorization code (3-legged)**.
3. Marque os escopos: `openid`, `profile` e `w_member_social`.
4. **Request access token**, faça login e autorize.
5. Copie o token (começa com `AQ`).

Confira no [Token Inspector](https://www.linkedin.com/developers/tools/oauth/token-inspector): ele mostra a validade (**60 dias**) e os escopos concedidos.

Documentação oficial: [Developer Portal Tools](https://learn.microsoft.com/en-us/linkedin/shared/authentication/developer-portal-tools).

## Alternativa ao Token Generator: fluxo manual com `localhost`

Use se o Token Generator não aparecer para o seu app. Redirect URL do app:
`http://localhost:8080/callback`.

1. No app, aba **Auth** → *Authorized redirect URLs for your app* → **Add redirect URL** → cole `http://localhost:8080/callback` e salve. A URL precisa ser idêntica, caractere por caractere.
2. Abra este endereço no navegador (já com o seu Client ID), logado no LinkedIn:

   ```
   https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id=77h1pbpeug4k88&redirect_uri=http%3A%2F%2Flocalhost%3A8080%2Fcallback&state=techdim&scope=openid%20profile%20w_member_social
   ```
3. Autorize. O navegador vai para `localhost:8080/callback?code=...` e mostra erro de página: é normal, não há nada rodando ali. **Copie o valor depois de `code=`** da barra de endereço. Ele vale ~30 minutos e só pode ser usado uma vez.
4. Troque o código pelo token **no seu computador** (o Client Secret não sai dele):

   ```bash
   curl -X POST https://www.linkedin.com/oauth/v2/accessToken \
     -d grant_type=authorization_code \
     -d code=COLE_O_CODE \
     -d redirect_uri=http://localhost:8080/callback \
     -d client_id=77h1pbpeug4k88 \
     -d client_secret=SEU_CLIENT_SECRET
   ```
   A resposta traz `access_token` (copie) e `expires_in` (≈ 5 184 000 s = 60 dias).

## Links diretos para cadastrar no GitHub

| O quê | Tipo | Link |
|---|---|---|
| `LINKEDIN_ACCESS_TOKEN` | Secret | [criar](https://github.com/Techdimbr/Publi-midia-Techdim/settings/secrets/actions/new) |
| `LINKEDIN_URN` | Variable | [criar](https://github.com/Techdimbr/Publi-midia-Techdim/settings/variables/actions/new) |
| `META_ACCESS_TOKEN` (trocar o token) | Secret | [editar](https://github.com/Techdimbr/Publi-midia-Techdim/settings/secrets/actions/META_ACCESS_TOKEN) |
| `ANTHROPIC_API_KEY` (opcional) | Secret | [criar](https://github.com/Techdimbr/Publi-midia-Techdim/settings/secrets/actions/new) |
| Todos os Secrets | — | [lista](https://github.com/Techdimbr/Publi-midia-Techdim/settings/secrets/actions) |
| Todas as Variables | — | [lista](https://github.com/Techdimbr/Publi-midia-Techdim/settings/variables/actions) |

Só `LINKEDIN_ACCESS_TOKEN` e `LINKEDIN_URN` são necessários. O **Client ID** e o
**Client Secret** do app **não** vão para o GitHub: a automação usa o token.

## 3. Cadastre o token no GitHub

Direto no GitHub, nunca no chat:

1. [Secrets do repositório](https://github.com/Techdimbr/Publi-midia-Techdim/settings/secrets/actions) → **New repository secret**.
2. Nome: `LINKEDIN_ACCESS_TOKEN`. Valor: o token do passo 2.

## 4. Descubra o `LINKEDIN_URN`

1. [Actions → Descobrir IDs](https://github.com/Techdimbr/Publi-midia-Techdim/actions/workflows/descobrir-ids.yml) → **Run workflow**.
2. Abra a execução e o passo **LinkedIn**. Ele imprime algo como:
   `LINKEDIN_URN = urn:li:person:AbCdEf123`
3. [Variables do repositório](https://github.com/Techdimbr/Publi-midia-Techdim/settings/variables/actions) → **New repository variable**: nome `LINKEDIN_URN`, valor o URN completo.

## 5. Teste com um post real só no LinkedIn

1. [Actions → Publicar](https://github.com/Techdimbr/Publi-midia-Techdim/actions/workflows/publicar.yml) → **Run workflow**.
2. `tema`: `especial` · `redes`: `linkedin` · `ensaio`: **desmarcado**.
3. A execução deve ficar verde, com "LinkedIn: publicado". O post sai no seu perfil.
4. Confira o registro do dia: [registros/](https://github.com/Techdimbr/Publi-midia-Techdim/tree/assets/registros).

Se não quiser publicar de verdade ainda, rode com **ensaio** marcado: gera a imagem e o texto, sem publicar.

## 6. Daqui em diante é automático

Cada tema passa a sair também no LinkedIn, com o primeiro comentário trazendo as
fontes e o site. O workflow
[Verificar token](https://github.com/Techdimbr/Publi-midia-Techdim/actions/workflows/token.yml)
roda toda segunda e **falha de propósito** quando o token vence, para o GitHub
te avisar por e-mail.

**Renovação:** a cada ~50 dias repita os passos 2 e 3. Tokens de app comum não
se renovam sozinhos.

## 7. Publicar como página da empresa (opcional)

1. No app, aba **Settings**, confirme que o app está associado à **Página da TECHDIM** no LinkedIn.
2. Aba **Products** → **Community Management API** → **Request access** e preencha o formulário. A análise do LinkedIn pode levar dias.
3. Com a aprovação, gere um token novo (passo 2) marcando também `w_organization_social`.
4. Rode **Descobrir IDs** de novo: ele lista as páginas que você administra como `urn:li:organization:NNN`.
5. Troque a Variable `LINKEDIN_URN` por esse valor.

## Problemas comuns

| Sintoma | Causa | Solução |
|---|---|---|
| `401` | token vencido ou revogado | gerar token novo (passo 2) |
| `403` | falta escopo | gerar token marcando o escopo e conferir no Token Inspector |
| `426` | versão da API desativada | atualizar `LINKEDIN_VERSION` em `src/config.py` |
| "não configurado" no registro | falta Secret ou Variable | passos 3 e 4 |
| URN não aparece | falta o produto *Sign In with LinkedIn using OpenID Connect* | passo 1 |

## Todo movimento fica registrado

Cada publicação, comentário, teste e falha vai para o diário do dia em
`registros/AAAA-MM-DD/movimentos.md`. Se você apagar ou editar um post à mão,
anote com o workflow
[Registrar movimento](https://github.com/Techdimbr/Publi-midia-Techdim/actions/workflows/registrar-movimento.yml).
