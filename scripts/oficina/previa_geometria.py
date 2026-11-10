#!/usr/bin/env python3
"""Prévia comparativa de geometria: ARQUIVO RECEBIDO | PRÉVIA V3, mesmos quadros, com grade de referência
para julgar as linhas retas e recorte 1:1 das bordas. Velocidade normal e depois 25%."""
import json, glob, os, subprocess
from pathlib import Path
Q = Path("out/oficina/geometria"); Q.mkdir(parents=True, exist_ok=True)
R = json.load(open("src/oficina/roteiro.json"))
ORIG = {os.path.basename(p).replace("(1)", "").replace(".mp4", ""): p for p in glob.glob("public/oficina/originais/*/*.mp4")}
EXP = "out/oficina/Oficina_Sete_previa_v3.mp4"
FB = subprocess.run(["fc-match", "-f", "%{file}", "Inter:style=SemiBold"], capture_output=True, text=True).stdout
FR = subprocess.run(["fc-match", "-f", "%{file}", "Inter:style=Regular"], capture_output=True, text=True).stdout
def cena(nome, t):
    return next(c for c in R["cenas"] + R["apoios"] if nome in c["video"] and c["de"] <= t < c["ate"])
ap = next(a for a in R["apoios"] if "C6218" in a["video"])
TRECHOS = [  # (título, take, início na edição, duração, recorte 540x540 em 1080p)
    ("FORNO — fechamento (C6214)", "C6214", 54.7, 3.2, (540, 640)),
    ("FORNO — plano aberto (C6211)", "C6211", 15.9, 3.0, (500, 560)),
    ("PAINEL RIPADO — apoio (C6218)", "C6218", ap["de"] + 0.15, ap["ate"] - ap["de"] - 0.3, (270, 640)),
    ("ABERTURA (C6211)", "C6211", 0.45, 2.8, (540, 260)),
]
def ff(*a): subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)
partes = []
for i, (tit, take, t, d, (cx, cy)) in enumerate(TRECHOS):
    c = cena(take, t); ts = c["inicioVideo"] + (t - c["de"])
    grade = "drawgrid=w=90:h=90:t=1:c=white@0.28"
    fc = (f"[0:v]fps=30,scale=1080:1920:flags=lanczos,split[o1][o2];[1:v]fps=30,split[e1][e2];"
          f"[o1]{grade},scale=540:960[of];[e1]{grade},scale=540:960[ef];"
          f"[o2]crop=540:540:{cx}:{cy},{grade}[oc];[e2]crop=540:540:{cx}:{cy},{grade}[ec];"
          f"[of][ef]hstack[top];[oc][ec]hstack[bot];[top][bot]vstack,pad=1080:1920:0:200:color=0x121212,"
          f"drawtext=fontfile='{FB}':text='{tit}':x=(w-tw)/2:y=50:fontsize=40:fontcolor=white,"
          f"drawtext=fontfile='{FB}':text='ARQUIVO RECEBIDO':x=(540-tw)/2:y=130:fontsize=28:fontcolor=0xF6F3EE,"
          f"drawtext=fontfile='{FB}':text='PRÉVIA V3':x=540+(540-tw)/2:y=130:fontsize=28:fontcolor=0xD8C7AC,"
          f"drawtext=fontfile='{FR}':text='recorte 1\\:1 das bordas (grade = referência de linha reta)':x=(w-tw)/2:y=1730:fontsize=26:fontcolor=0x999999[v]")
    n = Q / f"_n{i}.mp4"
    ff("-ss", f"{ts:.3f}", "-t", f"{d:.3f}", "-i", ORIG[take], "-ss", f"{t:.3f}", "-t", f"{d:.3f}", "-i", EXP,
       "-filter_complex", fc, "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", str(n))
    l = Q / f"_l{i}.mp4"
    ff("-i", str(n), "-vf", f"setpts=4*PTS,drawtext=fontfile='{FR}':text='25 por cento':x=w-220:y=1780:fontsize=26:fontcolor=0x999999",
       "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", str(l))
    partes += [n, l]
lst = Q / "_lista.txt"; lst.write_text("".join(f"file '{p.resolve()}'\n" for p in partes))
ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(Q / "Oficina_geometria_recebido_vs_v3.mp4"))
for p in partes + [lst]: p.unlink()
print(Q / "Oficina_geometria_recebido_vs_v3.mp4")
