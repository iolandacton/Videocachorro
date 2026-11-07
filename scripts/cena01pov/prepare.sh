#!/usr/bin/env bash
# CENA 01 — POV do Yorkshire: prepara a filmagem e a camada do cachorro (sem IA generativa).
# Requer Python com: pip install -r scripts/cena01pov/requirements.txt
set -euo pipefail
cd "$(dirname "$0")/../.."
mkdir -p public/cena01pov
# 1) Filmagem real 3.5–8.5 s: só recorte (remove marca d'água) e ampliação; sem correção de cor.
ffmpeg -v error -y -ss 3.5 -t 5.0 -i public/originais/praia_insta360.mov \
  -vf "crop=466:828:23:0,scale=1080:1920:flags=lanczos,setsar=1" \
  -c:v libx264 -crf 12 -preset slow -pix_fmt yuv420p -r 30 -c:a pcm_s16le -ar 48000 \
  public/cena01pov/praia_3.5-8.5.mov
# 2) Recorte do cachorro (rembg isnet-general-use + alpha matting), se ainda não existir.
if [ ! -f public/cena01pov/yorkshire_recorte.png ]; then
python -I - <<'PY'
from rembg import remove, new_session
from PIL import Image
im = Image.open("refs/cena01/yorkshire_costas.jpg").convert("RGB")
remove(im, session=new_session("isnet-general-use"), alpha_matting=True,
       alpha_matting_foreground_threshold=240, alpha_matting_background_threshold=15,
       alpha_matting_erode_size=8).save("public/cena01pov/yorkshire_recorte.png")
PY
fi
# 3) Camada animada do cachorro (cabeça, orelhas, pelo) no ritmo do trote.
python -I scripts/cena01pov/dog_layer.py
echo "Agora: npm run render:pov && npm run export:pov"
