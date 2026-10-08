# SEO: como o site e o blog chegam aos buscadores

Endereço oficial do site: **https://techdimbr.github.io/techdimbr/** (constante `BASE_URL` em `src/blog.py` e
`src/indexnow.py`; se um dia houver domínio próprio, troque nos dois).

## O que já está feito no código

**Página inicial**
- `canonical`, `og:url` e `twitter:url` corrigidos: apontavam para `https://techdimbr.github.io/`, que não existe (404).
- `og:image` e `twitter:image` agora são endereços absolutos (os relativos não funcionam em redes sociais), com tamanho e texto alternativo.
- `robots` com `max-image-preview:large` e `max-snippet:-1` (permite prévias grandes nos resultados).
- Dados estruturados (JSON-LD): `ProfessionalService` completo (id, logo, imagem, redes sociais, área atendida, fundador),
  `WebSite` e `Blog`.
- `hreflang` pt-BR, link do feed RSS, link do sitemap e bloco "Blog TECHDIM" com os posts mais novos (link interno direto
  da página mais forte do site para cada artigo).

**Blog (cada resumo do dia e cada artigo)**
- `<title>` e descrição próprios (a descrição é a primeira informação do texto, com até 155 caracteres), `canonical`,
  `robots`, Open Graph (`article:published_time`, seção, tags, imagem com tamanho e alt) e Twitter Card.
- JSON-LD `BlogPosting` (título, datas, autor e editora com logo, imagem, fontes citadas, palavras-chave),
  `BreadcrumbList` e, no resumo do dia, `CollectionPage` com `ItemList`.
- Trilha de navegação visível, links para o dia anterior e o seguinte, "Mais do Radar de hoje" e "Leia também"
  (artigos de dias anteriores com o mesmo assunto), para os robôs e as pessoas navegarem entre as páginas.
- Uma página por assunto, com endereço legível (`/blog/2026-10-07/exchange-server-atualizacao-fora-de-ciclo-corrige-leitura/`):
  quem pesquisa "CVE-2026-96940" ou "LGPD registro ANPD" encontra uma página sobre aquilo, não um resumo misturado.
- Capa em JPEG de 720×900 (cerca de 70 KB), com texto alternativo, também listada no sitemap de imagens.

**Arquivos do site**
- `sitemap.xml`: só endereços válidos deste site, com `lastmod` e imagens. (O antigo listava páginas de `www.techdim.com.br`
  que não existem neste site; o Google rejeita sitemap com endereço de outro domínio.)
- `blog/feed.xml` (RSS), `robots.txt` apontando para o sitemap certo, `seo.json` e a chave pública do IndexNow.

## Como cada post novo é avisado aos buscadores (automático)

1. A Routine grava a pauta e roda `src/blog.py`, que cria a página e atualiza índice, arquivo, feed, sitemap e home.
2. O site é enviado ao GitHub Pages.
3. `src/indexnow.py` espera a página ficar no ar e envia o endereço pelo protocolo **IndexNow**, aceito por
   **Bing, Yandex, Naver, Seznam e Yep** (e por quem usa o índice do Bing, como DuckDuckGo e Ecosia).
4. **Google:** não aceita IndexNow nem "ping" de sitemap (o ping foi desativado em 2023). Ele descobre as páginas pelo
   sitemap e pelo feed (enviados uma vez no Search Console), pelos links internos e por links de fora. Por isso a home
   ganhou o bloco de posts recentes, e vale divulgar o blog nos perfis (veja abaixo).

## O que só o dono da conta pode fazer (uma vez só, ~10 minutos)

**1. Google Search Console** (https://search.google.com/search-console)
1. "Adicionar propriedade" → **Prefixo do URL** → `https://techdimbr.github.io/techdimbr/`.
2. Método de verificação **Tag HTML**: copie só o valor de `content="..."`.
3. Cole em `seo.json`, no campo `google_site_verification`, e rode `python src/blog.py --site ...` (ou me peça).
   A tag entra na página inicial e permanece nas execuções seguintes.
4. Clique em "Verificar". Depois, em **Sitemaps**, envie `sitemap.xml` e também `blog/feed.xml` (o Search Console aceita RSS).
5. Em "Inspeção de URL", cole a página inicial e o resumo do dia e clique em "Solicitar indexação" (limite diário baixo).

**2. Bing Webmaster Tools** (https://www.bing.com/webmasters): "Importar do Google Search Console" (um clique, sem
nova verificação). Mostra a indexação no Bing e no DuckDuckGo.

**3. Perfil da Empresa no Google** (https://business.google.com): coloque o endereço do site no perfil de Campinas e
publique no perfil os posts de destaque. É o atalho mais forte para aparecer em buscas locais ("suporte de TI Campinas").

**4. Links de fora** (cada um ajuda o Google a achar e a confiar no site): site no perfil do Instagram, na página do
LinkedIn e na página do Facebook; link do blog na assinatura de e-mail.

## Limites e boas práticas

- Projeto no GitHub Pages **não controla o `robots.txt` da raiz** (`techdimbr.github.io/robots.txt`); sem ele os
  buscadores podem rastrear tudo, que é o desejado. O `robots.txt` da pasta serve só de documentação.
- **Domínio próprio** (ex.: `www.techdim.com.br`) é o próximo passo de maior efeito: concentra a autoridade na marca e
  libera `robots.txt` e sitemap na raiz. Passos: arquivo `CNAME` no repositório do site, registro DNS `CNAME` de `www` para
  `techdimbr.github.io`, ativar "Enforce HTTPS" em Settings → Pages, e trocar `BASE_URL` no código.
- Posição no Google depende de conteúdo útil e constante, de tempo (semanas) e de links. Nada garante primeira página.
- Não repita nem resubmeta endereços sem mudança no IndexNow; o script só envia o que mudou no último commit.

## Conferência rápida

    python src/indexnow.py --site /home/user/techdimbr --simular   # o que seria enviado
    curl -s https://techdimbr.github.io/techdimbr/sitemap.xml | head
