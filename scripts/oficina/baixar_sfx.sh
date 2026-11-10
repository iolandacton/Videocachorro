#!/usr/bin/env bash
# Efeitos sonoros do Mixkit usados na Oficina Sete (Mixkit Sound Effects Free License: uso comercial, sem
# atribuição; NÃO redistribuir os arquivos isolados — por isso eles não ficam no repositório).
#   1120 "Modern click box check" → tick quando um rótulo de detalhe surge
#   1489 "Air woosh"              → whoosh na entrada da imagem da solução
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p public/oficina/sfx
for id in 1120 1489; do
  curl -sSf -m 30 -o public/oficina/sfx/mixkit_$id.mp3 "https://assets.mixkit.co/active_storage/sfx/$id/$id-preview.mp3"
done
ls -l public/oficina/sfx
