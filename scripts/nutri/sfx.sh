#!/usr/bin/env bash
# Efeitos sonoros sintetizados (sem arquivos de terceiros, sem licenças).
set -euo pipefail
cd "$(dirname "$0")/../.."
A=public/nutri/sfx; mkdir -p "$A"
ff() { ffmpeg -v error -y "$@"; }
# whoosh curto para os zooms
ff -f lavfi -i "anoisesrc=color=pink:duration=0.42:amplitude=0.9:seed=11" -af "highpass=400,lowpass=5200,volume='if(lt(t,0.17),pow(t/0.17,2),pow(max(0,1-(t-0.17)/0.25),2))':eval=frame,volume=-5dB" -ar 48000 -ac 2 "$A/whoosh.wav"
# pop das palavras-chave
ff -f lavfi -i "aevalsrc='0.8*sin(2*PI*(520+900*exp(-t*60))*t)*exp(-t*38)':s=48000:d=0.14" -af "volume=-8dB" -ac 2 "$A/pop.wav"
# impacto grave
ff -f lavfi -i "aevalsrc='0.95*sin(2*PI*(46+70*exp(-t*22))*t)*exp(-t*4.2)':s=48000:d=1.3" -f lavfi -i "anoisesrc=color=white:duration=0.12:amplitude=0.6:seed=3" -filter_complex "[1]highpass=1500,afade=t=out:d=0.12[n];[0][n]amix=inputs=2:normalize=0,lowpass=6000,volume=-2dB" -ar 48000 -ac 2 "$A/impacto.wav"
# subida de tensão (5 s): tom + ruído crescendo
ff -f lavfi -i "aevalsrc='0.35*sin(2*PI*(110*t+34*t*t))*pow(t/5,2)':s=48000:d=5" -f lavfi -i "anoisesrc=color=pink:duration=5:amplitude=0.7:seed=9" -filter_complex "[1]highpass=900,volume='pow(t/5,3)':eval=frame[n];[0][n]amix=inputs=2:normalize=0,afade=t=out:st=4.93:d=0.07,volume=-9dB" -ar 48000 -ac 2 "$A/subida.wav"
# carimbo do X
ff -f lavfi -i "anoisesrc=color=brown:duration=0.2:amplitude=0.9:seed=4" -af "lowpass=900,afade=t=out:d=0.2,volume=2dB" -ar 48000 -ac 2 "$A/carimbo.wav"
ls "$A"
