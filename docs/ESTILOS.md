# Padrão visual das publicações

Cada post sai como um infográfico 1080×1350 (LinkedIn, Facebook e Instagram), gerado por
`src/infografico.py`: título em duas cores, texto curto, "3 lições táticas", pergunta final
com chamada "Vamos conversar?", hashtags e rodapé TECHDIM + www.techdim.com.br.

A cena ilustrada muda conforme o assunto (campo `cena` do bloco `infografico`):

| cena | quando usar |
|---|---|
| `noticias` | notícias de tecnologia e IA (monitor de notícias, mapa, celular com alerta) |
| `painel` | cibersegurança/hacker (terminal com os fatos do caso, em `terminal`) |
| `ensino` | conhecimento e passo a passo (quadro, notebook com aula, caneca) |
| `dev` | desenvolvimento de software sob medida (monitor com código, notebook com sistema, celular com app) |
| `rede` | infraestrutura, redes, backup e segurança (rack de servidores, rede com cadeado) |

Sem `cena`, vale o padrão do tema. Sem o bloco `infografico`, o post usa a arte antiga.
As cenas são desenhadas por código (sem foto de banco de imagem, sem direitos de terceiros).

## Cena composta (única por post)

O Claude descreve a cena pensando no assunto do post, no campo `cena_composta` do bloco
`infografico`:

    "cena_composta": {"fundo": "escritorio|datacenter|espaco|cidade|laboratorio",
                      "elementos": ["notebook","nuvem","celular"],   // 1 a 4
                      "legenda": "BACKUP NA NUVEM · DADOS SEGUROS"}

Elementos: notebook, monitor, celular, rack, nuvem, escudo, globo, engrenagens, grafico,
documento, chip. Cada combinação de fundo, elementos e legenda gera uma imagem diferente.

## Validação e reserva

O bloco `infografico` da pauta passa por `infografico.validar`:

- textos longos são cortados em palavra inteira, com reticências;
- no máximo 3 lições, 4 elementos, 8 linhas de terminal e 6 hashtags;
- fundo, elemento ou cena desconhecidos caem no padrão do tema;
- sem `titulo_branco`/`titulo_destaque` ou sem nenhuma lição o bloco é recusado — e
  o post sai com a arte antiga (carrossel/capa), nunca deixa de sair.

As hashtags da imagem saem em caixa alta. Na legenda, as do assunto vêm primeiro,
sem acento; escreva-as em CamelCase (`#IAGenerativa`) para ficarem legíveis.
