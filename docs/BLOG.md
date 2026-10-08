# Blog do site

Blog em https://techdimbr.github.io/techdimbr/blog/ (repositório `Techdimbr/techdimbr`, GitHub Pages).
Para tudo sobre buscadores (Google, Bing e outros), veja `docs/SEO.md`.

## O que existe

Para cada dia da pauta (`content/diario/<data>/`):

- um **resumo do dia** ("Radar TECHDIM") em `blog/<data>/`;
- **um artigo por assunto** (notícia, alerta de segurança, dica e serviço) em `blog/<data>/<assunto>/`, cada um com
  título, descrição, capa (o infográfico do dia, em JPEG pequeno), fontes e dados estruturados próprios.

Também são gerados o índice (`blog/`), o arquivo por mês (`blog/arquivo/AAAA-MM/`), o feed (`blog/feed.xml`),
o `sitemap.xml`, o `robots.txt` e os blocos de SEO e de "posts recentes" da página inicial.
O texto vem da pauta já conferida: `src/blog.py` só reorganiza, não inventa fato novo.

## Como roda todo dia

A Routine "Pauta do Dia" (07:03), depois de gravar a pauta em main, executa o passo 4B do prompt:
clona o site, roda `python3 src/blog.py --site /home/user/techdimbr`, envia para a `main` do site e roda
`python3 src/indexnow.py --site /home/user/techdimbr` para avisar os buscadores. Precisa do app Claude instalado
em `Techdimbr/techdimbr`. Tudo é idempotente: rodar de novo no mesmo dia não duplica nem muda nada.

`.github/workflows/blog.yml` faz o mesmo no GitHub Actions, mas só se existir o segredo `SITE_REPO_TOKEN`
(token com *Contents: Read and write* no repositório do site). É opcional.

## Teste local

    python src/blog.py --site /caminho/do/repo-do-site            # gera tudo (capas só as que faltam)
    python src/blog.py --site /caminho/do/repo-do-site --forcar-imagens
    python src/indexnow.py --site /caminho/do/repo-do-site --simular   # mostra o que seria enviado
