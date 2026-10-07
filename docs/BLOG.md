# Blog do site

Um post por dia em https://techdimbr.github.io/techdimbr/blog/ (repositório `Techdimbr/techdimbr`, GitHub Pages).

- `src/blog.py` monta o post "Radar TECHDIM" a partir da pauta do dia (`content/diario/<data>/`): notícia, alerta, dica
  (com os passos e as fontes) e o serviço do dia. Nada de fato novo é inventado: é o texto já conferido da pauta.
- Gera `blog/<data>/index.html`, o índice `blog/`, o feed `blog/feed.xml`, as entradas no `sitemap.xml` e o link
  "Blog" no menu do site. Rodar de novo no mesmo dia reescreve o mesmo arquivo (não duplica).
- `.github/workflows/blog.yml` roda quando a pauta é gravada em main (e uma vez por dia como reserva) e envia o
  resultado ao repositório do site.

## Para ativar

O workflow precisa do segredo **`SITE_REPO_TOKEN`** neste repositório: um token (fine-grained, só no repositório
`Techdimbr/techdimbr`, permissão *Contents: Read and write*). Sem ele o workflow só avisa e não publica.
Para publicar os posts já existentes: Actions → "Blog do site" → Run workflow (deixe "datas" vazio).

Teste local: `python src/blog.py --site /caminho/do/repo-do-site`.
