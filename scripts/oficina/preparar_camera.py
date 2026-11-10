#!/usr/bin/env python3
"""Oficina Sete — intermediários a partir dos ORIGINAIS DA CÂMERA (Sony XAVC HS, HEVC 10 bits, 2160x3840, 59,94p).
  59,94 → 29,97 fps por seleção exata de 1 quadro a cada 2 (sem interpolação) →
  redução 2:1 para 1080x1920 (quadro inteiro = mesmo enquadramento dos arquivos usados na edição) →
  mesma correção de cor aprovada (ganhos pelo neutro + look), conversão para 8 bits com dithering →
  SEM nitidez artificial, SEM estabilização → intermediário sem perda (qp 0).
Uso: .venv/bin/python scripts/oficina/preparar_camera.py [TAKE ...]
"""
import json, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

NEUTRO = json.load(open("public/oficina/analise/neutros.json"))
OUT = Path("public/oficina/cam"); OUT.mkdir(parents=True, exist_ok=True)
ALVO = (206.0, 195.0, 190.0)   # o mesmo branco de referência da versão aprovada
LOOK = "curves=all='0/0 0.25/0.24 0.5/0.51 0.8/0.82 0.94/0.93 1/0.97',eq=contrast=1.03:saturation=0.95"   # o mesmo look aprovado
USAR = sys.argv[1:] or ["C6211", "C6212", "C6214", "C6218", "C6219", "C6222"]


def preparar(n):
    r, g, b = NEUTRO[n]
    ganho = [max(0.85, min(1.25, ALVO[i] / v)) for i, v in enumerate((r, g, b))]
    cor = f"colorchannelmixer=rr={ganho[0]:.4f}:gg={ganho[1]:.4f}:bb={ganho[2]:.4f}"
    vf = ("select='not(mod(n\\,2))',setpts=N/(30000/1001)/TB,"
          "scale=1080:1920:flags=lanczos+accurate_rnd+full_chroma_int:sws_dither=ed,format=rgb24,"
          f"{cor},{LOOK},format=yuv420p")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f"public/oficina/camera/{n}.MP4", "-an", "-vf", vf,
                    "-r", "30000/1001", "-c:v", "libx264", "-preset", "veryfast", "-qp", "0", "-pix_fmt", "yuv420p",
                    str(OUT / f"{n}.mp4")], check=True)
    return n


with ThreadPoolExecutor(2) as ex:
    for n in ex.map(preparar, USAR):
        print("ok", n, flush=True)
