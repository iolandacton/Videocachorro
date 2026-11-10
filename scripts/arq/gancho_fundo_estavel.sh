#!/usr/bin/env bash
# Remove a cintilação da porta/parede do fundo na abertura (C6282) sem tocar no Yuri:
# média temporal ponderada de 7 quadros (câmera move só ~0,14 px/quadro → sem fantasmas) + suavização
# mínima das bordas super-nitidificadas, aplicadas SÓ dentro de uma máscara suave sobre a porta/parede.
# Mistura por alfa (overlay): fora da máscara os pixels são cópia exata do original. Mesmos 181 quadros.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=public/arq_v2/gancho_q
SRC=public/originais/yuri_gancho_C6282.mp4
N=$(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 $SRC)
ffmpeg -v error -y -f lavfi -i "color=c=black:s=1080x1920:d=1" -frames:v 1 \
  -vf "drawbox=x=735:y=400:w=345:h=660:color=white:t=fill,gblur=sigma=10" -pix_fmt gray $OUT/mascara_porta.png
ffmpeg -v error -y -i $SRC -loop 1 -i $OUT/mascara_porta.png -filter_complex \
  "[0:v]split[o][t];[t]tmix=frames=7:weights='1 2 3 4 3 2 1',gblur=sigma=0.8[s];\
   [1:v]format=gray[m];[s][m]alphamerge[sa];[o][sa]overlay=format=yuv420:eof_action=pass[v]" \
  -map "[v]" -map 0:a -frames:v $N -c:v libx264 -qp 0 -preset veryfast -c:a copy $OUT/yuri_gancho_C6282_fundo_estavel.mp4
echo "quadros: $N"
