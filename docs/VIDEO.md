# Vídeos e Reels

O publicador de imagens ganhou um irmão: o tema **`video`** publica um MP4 vertical como **Reel no Instagram**,
**Reel no Facebook** e **vídeo no LinkedIn**. É o mesmo workflow **Publicar** (ensaio, pré-voo, diário,
anti-duplicidade e exclusão pelo workflow *Apagar posts* funcionam como nos demais temas).

## Como publicar um vídeo

1. **Suba o MP4 no branch `assets`**, em `videos/AAAA-MM-DD/<nome>.mp4` (binário grande não entra no histórico do código).
2. **Escreva a pauta** em `content/videos/<nome>.json`:

       {
         "titulo": "Acompanhe a TECHDIM: análises técnicas todos os dias",
         "arquivo": "videos/2026-10-16/apresentacao-techdim.mp4",
         "legenda": "Texto principal, vale para todas as redes.",
         "hashtags": ["#TECHDIM", "#InfraestruturaDeTI"],
         "ia": true,
         "capa_ms": 2500,
         "motivo": "Por que este vídeo (vai para o diário)."
       }

   | Campo | Para quê |
   |---|---|
   | `titulo` | 1ª linha da legenda, título no LinkedIn e no Facebook, diário (até 100 caracteres) |
   | `arquivo` | caminho do MP4 **no branch assets** |
   | `legenda` | texto principal; cada rede acrescenta o endereço do site do jeito dela e as hashtags |
   | `hashtags` | do assunto; a marca entra sempre e o limite de cada rede é respeitado |
   | `ia` | `true` quando o vídeo foi gerado por IA (ver abaixo) |
   | `capa_ms` | quadro de capa do Reel do Instagram, em milissegundos (opcional) |

3. **Actions → Publicar → Run workflow**: `tema` = `video`, `video` = `<nome>` (o nome do JSON, sem `.json`),
   `redes` vazio (as três) ou uma só, por exemplo `linkedin`. Marque **ensaio** para só gerar e conferir
   (nenhuma rede é tocada). Se uma rede falhar, repita só ela (`redes` = a que falhou, com `evitar_duplicado`).

O workflow busca o MP4 no branch assets, **confere o arquivo contra os limites de cada rede antes de publicar em
qualquer uma** (`src/video.py`) e só então envia. Também dá para conferir um arquivo na sua máquina:

    PYTHONPATH=src python src/video.py conferir arquivo.mp4

## O que cada rede exige

Conferido na documentação oficial em 16/10/2026 (links no topo de `src/video.py`).

| | Instagram (Reels) | Facebook (Reels da Página) | LinkedIn |
|---|---|---|---|
| Duração | 3 s a 15 min | 3 a 90 s | 3 s a 30 min |
| Tamanho | até 300 MB | — | 75 KB a 500 MB |
| Proporção | 9:16 recomendado | **9:16**, mínimo 540×960 | qualquer |
| Estrutura | `moov` antes do `mdat`, **sem lista de edição**, H.264/HEVC, AAC até 48 kHz, 23–60 fps | H.264/H.265, AAC-LC 48 kHz, 24–60 fps | MP4 |
| Limite de API | 100 posts por 24 h | 30 Reels por 24 h | — |

Para gerar um arquivo que passa em tudo (vertical, H.264, sem B-frames e sem lista de edição, `moov` na frente):

    ffmpeg -i entrada.mp4 -c:v libx264 -preset slow -crf 18 -profile:v high -bf 0 -pix_fmt yuv420p -r 24 \
           -c:a aac -b:a 160k -ar 48000 -use_editlist 0 -movflags +faststart saida.mp4

## Como o envio funciona (sem URL pública)

O GitHub serve `.mp4` como `application/octet-stream`, que o Instagram e o Facebook podem recusar. Por isso o
arquivo **sobe direto** do runner, e nada depende de URL pública:

- **Instagram:** container `REELS` com `upload_type=resumable`; o arquivo vai ao `rupload.facebook.com/ig-api-upload`;
  espera o container ficar `FINISHED` (até 5 min); `media_publish`. `share_to_feed=true`.
- **Facebook:** `video_reels` em três tempos (`start` → envio ao `rupload.facebook.com/video-upload` → `finish` com
  `video_state=PUBLISHED`), e acompanha o status até aparecer como publicado.
- **LinkedIn:** Videos API: `initializeUpload`, partes de 4 MB por PUT (o `ETag` de cada uma), `finalizeUpload`, espera
  `AVAILABLE` e cria o post com o URN do vídeo. A assinatura da `uploadUrl` nunca vai para o log.
- O diário (`registros/AAAA-MM-DD/`) mostra o vídeo como link e registra o resultado de cada rede, como nas imagens.
  Stories com vídeo ainda não são suportados.

## Conteúdo gerado por IA

Vídeo feito com IA generativa **precisa ser declarado**. O arquivo original do Google traz as Credenciais de
Conteúdo (C2PA) assinadas, com a classificação `trainedAlgorithmicMedia`, e as redes leem isso para rotular o post.
**Qualquer reedição apaga essa assinatura** (mudar um pixel invalida o selo), então uma versão editada precisa
declarar a origem por conta própria. Com `"ia": true` o sistema:

- liga `is_ai_generated` no Instagram (autodeclaração oficial da API);
- escreve em todas as legendas "Vídeo criado com inteligência artificial.";
- registra isso no diário.

Se a edição foi só o texto na tela e você preferir manter o selo original, publique o arquivo **sem reeditar**.

## Erros comuns

| Mensagem | O que fazer |
|---|---|
| `o vídeo não serve para: instagram: …` | o arquivo não cumpre o limite da rede; refaça com o `ffmpeg` acima |
| `(#4) Application request limit reached` | limite de uso do app da Meta (o Radar e as publicações dividem o mesmo): espere cerca de 1 h e repita só essa rede |
| `LinkedIn não processou o vídeo` | formato recusado; o motivo vem na mensagem (`processingFailureReason`) |
| `rejeitou o container` (Instagram) | o motivo vem na mensagem; confira estrutura, codec e proporção |
