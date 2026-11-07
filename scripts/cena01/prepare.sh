#!/usr/bin/env bash
# Prepara a CENA 01 (chegada à praia) a partir do vídeo original, sem alterá-lo.
# - Frames: recorte (remove marca d'água Insta360 e dedos na borda inferior),
#   correção de cor tropical, upscale lanczos para 1080x1920 (não cria detalhe novo).
# - Áudio: trechos do som original + efeitos sintetizados (sem música, sem licenças).
set -euo pipefail
cd "$(dirname "$0")/../.."
SRC=public/originais/praia_chegada_completo.mov
OUT=public/cena01
FR=$OUT/frames
mkdir -p "$FR" "$OUT/audio"

GRADE="hqdn3d=1.5:1.5:3:3,crop=448:796:32:0,scale=1080:1920:flags=lanczos,\
eq=contrast=1.07:saturation=1.06:gamma=0.97,\
curves=all='0/0 0.25/0.235 0.5/0.5 0.8/0.815 1/0.965',\
colorbalance=rm=0.02:gm=0.005:bm=-0.015:rh=0.01:bh=-0.01,\
unsharp=5:5:0.25"

# Trechos usados (segundos da fonte). Nome do frame = índice da fonte a 30 fps.
for r in "0.4 7.1" "22.4 29.2" "31.9 60.2" "88.1 92.8" "103.9 113.6"; do
  set -- $r
  n0=$(python3 -c "print(round($1*30))")
  nf=$(python3 -c "print(round(($2-$1)*30))")
  ffmpeg -v error -y -ss "$1" -i "$SRC" -frames:v "$nf" -vf "$GRADE" -q:v 2 \
    -start_number "$n0" "$FR/f_%05d.jpg"
done

A=$OUT/audio
# Som natural original
ffmpeg -v error -y -ss 0.3 -t 3.4 -i "$SRC" -vn -af "highpass=80,volume=14dB,afade=t=out:st=2.8:d=0.6" -ar 48000 -ac 2 "$A/amb_arvores.wav"
ffmpeg -v error -y -ss 88.2 -t 4.6 -i "$SRC" -vn -af "highpass=60,volume=9dB" -ar 48000 -ac 2 "$A/mar_revelacao.wav"
ffmpeg -v error -y -ss 104 -t 3.2 -i "$SRC" -vn -af "highpass=60,volume=9dB" -ar 48000 -ac 2 "$A/mar_areia.wav"
# Folhas ao vento (ruído rosa modulado)
ffmpeg -v error -y -f lavfi -i "anoisesrc=color=pink:duration=3.5:amplitude=0.5:seed=7" \
  -af "highpass=1800,lowpass=7000,tremolo=f=5:d=0.6,volume=-12dB,afade=t=in:d=0.6,afade=t=out:st=2.8:d=0.7" -ar 48000 -ac 2 "$A/folhas.wav"
# Vento crescente (6 s): ruído marrom, volume e brilho subindo
ffmpeg -v error -y -f lavfi -i "anoisesrc=color=brown:duration=6:amplitude=0.9:seed=3" \
  -af "lowpass=f=2500,highpass=120,volume='0.05+0.95*pow(t/6,2)':eval=frame,afade=t=out:st=5.7:d=0.3" -ar 48000 -ac 2 "$A/vento_crescente.wav"
# Whoosh discreto (0.55 s)
ffmpeg -v error -y -f lavfi -i "anoisesrc=color=pink:duration=0.55:amplitude=0.9:seed=11" \
  -af "highpass=350,lowpass=4500,volume='if(lt(t,0.22),pow(t/0.22,2),pow(max(0,1-(t-0.22)/0.33),2))':eval=frame,volume=-4dB" -ar 48000 -ac 2 "$A/whoosh.wav"
# Impacto suave (sub grave com decaimento)
ffmpeg -v error -y -f lavfi -i "aevalsrc='0.9*sin(2*PI*(52+30*exp(-t*18))*t)*exp(-t*4.5)':s=48000:d=1.2" \
  -af "lowpass=180,volume=-3dB" -ac 2 "$A/impacto.wav"
# Passos rápidos na areia (rajadas curtas de ruído filtrado)
ffmpeg -v error -y -f lavfi -i "anoisesrc=color=white:duration=2.6:amplitude=0.8:seed=5" \
  -af "bandpass=f=1400:width_type=o:w=1.6,volume='pow(max(0,1-mod(t,0.19)/0.06),3)':eval=frame,volume=-10dB,afade=t=in:d=0.3" -ar 48000 -ac 2 "$A/passos_areia.wav"
echo "Pronto: $(ls $FR | wc -l) frames, $(ls $A | wc -l) áudios"
