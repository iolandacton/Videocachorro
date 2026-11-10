#!/usr/bin/env bash
# Takes reais em qualidade máxima possível a partir das fontes disponíveis (512x910):
# ampliação única (lanczos), SEM redução de ruído temporal, nitidez adaptativa discreta (cas),
# sem correção de cor aqui (a cor é aplicada uma única vez na composição), intermediário SEM PERDA.
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p public/arq_v2/takes_q
for f in IMG_2720 IMG_2721 IMG_2722 IMG_2723; do
  ffmpeg -v error -y -i public/arq_v2/originais/$f.mp4 -an \
    -vf "scale=1080:1920:flags=lanczos+accurate_rnd+full_chroma_int,cas=0.35" \
    -c:v libx264 -qp 0 -preset veryfast -pix_fmt yuv420p public/arq_v2/takes_q/$f.mp4 &
done
wait
ls -lh public/arq_v2/takes_q
