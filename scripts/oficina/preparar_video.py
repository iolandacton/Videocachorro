#!/usr/bin/env python3
"""Oficina Sete — prepara cada clipe usado (uma única passagem, intermediário de alta qualidade):
  estabilização leve só nos apoios que tremem (vid.stab) → ampliação lanczos 512x910→1080x1920 →
  nitidez adaptativa discreta → balanço de branco/exposição pelo NEUTRO da cena (paredes/teto claros) →
  look comum discreto (contraste suave, realces protegidos, saturação levemente contida).
Uso: .venv/bin/python scripts/oficina/preparar_video.py
"""
import json, glob, os, subprocess
from pathlib import Path

ORIG = {os.path.basename(p).replace("(1)", "").replace(".mp4", ""): p for p in glob.glob("public/oficina/originais/*/*.mp4")}
NEUTRO = json.load(open("public/oficina/analise/neutros.json"))
OUT = Path("public/oficina/proc"); OUT.mkdir(parents=True, exist_ok=True)
ALVO = (206.0, 195.0, 190.0)      # branco de referência: claro e levemente quente (R−B ≈ +16)
ESTABILIZAR = {"C6218", "C6219", "C6220", "C6221", "C6222", "C6223"}   # apoios; o protagonista já está firme
USAR = ["C6211", "C6212", "C6214", "C6218", "C6219", "C6220", "C6221", "C6222", "C6223"]
LOOK = "curves=all='0/0 0.25/0.24 0.5/0.51 0.8/0.82 0.94/0.93 1/0.97',eq=contrast=1.03:saturation=0.95"


def ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


for n in USAR:
    src = ORIG[n]
    r, g, b = NEUTRO[n]
    ganho = [max(0.85, min(1.25, ALVO[i] / v)) for i, v in enumerate((r, g, b))]
    cor = f"colorchannelmixer=rr={ganho[0]:.4f}:gg={ganho[1]:.4f}:bb={ganho[2]:.4f}"
    pre = ""
    if n in ESTABILIZAR:
        trf = OUT / f"{n}.trf"
        ff("-i", src, "-vf", f"vidstabdetect=shakiness=6:accuracy=15:result={trf}", "-f", "null", "-")
        pre = f"vidstabtransform=input={trf}:smoothing=10:optzoom=1:interpol=bicubic,"
    vf = f"{pre}scale=1080:1920:flags=lanczos+accurate_rnd+full_chroma_int,cas=0.25,format=rgb24,{cor},{LOOK},format=yuv420p"
    ff("-i", src, "-an", "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "8", "-pix_fmt", "yuv420p",
       str(OUT / f"{n}.mp4"))
    print(f"{n}: ganhos RGB {[round(x, 3) for x in ganho]}" + (" + estabilização" if n in ESTABILIZAR else ""), flush=True)
