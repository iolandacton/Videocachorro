#!/usr/bin/env python3
"""Prévia 3: takes com upscale Runway — ORIGINAL (512x910) | SEM IA | RUNWAY, take a take, normal + 50%."""
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from previas_qualidade import comparar, ff, Q  # noqa: E402

R = json.load(open("src/arquitetura/v2/final_v3.json"))
V3 = "out/arq_v3/arquitetura_final_v3_qualidade.mp4"
SEM_IA = "out/qualidade/corrigido_takes.mp4"   # começa em 43,5 s da edição
CROPS = {"IMG_2722": ((280, 430), (380, 510)), "IMG_2721": ((310, 500), (400, 580)), "IMG_2720": ((360, 260), (520, 380))}
cen = [c for c in R["cenas"] if any(k in str(c.get("video")) for k in CROPS)]
orig_inicio = {"IMG_2722": 0.6, "IMG_2721": 2.2, "IMG_2720": 0.0}
normais, lentos = [], []
for i, c in enumerate(cen):
    nome = c["video"].split("/")[-1][:8]
    d = c["ate"] - c["de"]
    o = Q / f"_o{i}.mp4"
    ff("-ss", f"{orig_inicio[nome]:.3f}", "-t", f"{d:.3f}", "-i", f"public/arq_v2/originais/{nome}.mp4", "-an",
       "-vf", "fps=30,scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", str(o))
    n, l = comparar(f"_rw{i}", f"PRÉVIA 3 — TAKES COM RUNWAY  ·  {nome}", "ORIGINAL (512x910)",
                    [(str(o), 0), (SEM_IA, c["de"] - 43.5), (V3, c["de"])], d, *CROPS[nome],
                    ["Runway (Magnific, criatividade 0, natural): textura de pele e fios gerados por IA.",
                     "Geometria do rosto preservada (desvio 0–2 px); tom e contraste igualados à fonte.",
                     "IMG_2723 (detalhe da trena, sem rosto) ficou com a correção sem IA."],
                    juntar=False, rot1="SEM IA", rot2="RUNWAY (usado)")
    normais.append(n); lentos.append(l); o.unlink()
(Q / "_p3.txt").write_text("".join(f"file '{x.resolve()}'\n" for x in normais + lentos))
ff("-f", "concat", "-safe", "0", "-i", str(Q / "_p3.txt"), "-c", "copy", "-movflags", "+faststart", str(Q / "Previa_3_takes_runway_comparacao.mp4"))
for x in normais + lentos + [Q / "_p3.txt"]:
    x.unlink()
print(Q / "Previa_3_takes_runway_comparacao.mp4")
