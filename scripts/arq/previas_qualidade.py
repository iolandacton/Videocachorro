#!/usr/bin/env python3
"""Monta as prévias de qualidade lado a lado: ORIGINAL | EXPORTADO (atual) | CORRIGIDO.
Linha 1: quadro inteiro. Linha 2: recorte 1:1. Linha 3: ampliação 2x pixel a pixel (sem suavizar).
Toca em velocidade normal e depois a 50%. Uso: python3 scripts/arq/previas_qualidade.py
"""
import json, subprocess
from pathlib import Path

Q = Path("out/qualidade"); Q.mkdir(parents=True, exist_ok=True)
FONT = subprocess.run(["fc-match", "-f", "%{file}", "Inter:style=Regular"], capture_output=True, text=True).stdout
FONTB = subprocess.run(["fc-match", "-f", "%{file}", "Inter:style=SemiBold"], capture_output=True, text=True).stdout
INI = json.load(open("public/arq_v2/voz/cortes.json"))[0]["mantido"][0][0]
R = json.load(open("src/arquitetura/v2/final_v2.json"))
EXP = "out/arq_v2/arquitetura_final_v2_corrigido.mp4"


def ff(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)


def comparar(saida, titulo, rot0, entradas, dur, c1, c2, nota, juntar=True):
    """entradas: [(arquivo, inicio)] x3, todos já em 1080x1920/30 fps; c1=(x,y) recorte 360; c2=(x,y) recorte 180→2x."""
    args = []
    for p, ss in entradas:
        args += ["-ss", f"{ss:.3f}", "-t", f"{dur:.3f}", "-i", p]
    args += ["-f", "lavfi", "-t", f"{dur:.3f}", "-i", "color=c=0x121212:s=1080x1920:r=30"]
    fc = []
    for i in range(3):
        fc.append(f"[{i}:v]fps=30,scale=1080:1920:flags=lanczos,setsar=1,split=3[a{i}][b{i}][c{i}]")
        fc.append(f"[a{i}]scale=360:640:flags=lanczos[f{i}]")
        fc.append(f"[b{i}]crop=360:360:{c1[0]}:{c1[1]}[r{i}]")
        fc.append(f"[c{i}]crop=180:180:{c2[0]}:{c2[1]},scale=360:360:flags=neighbor[z{i}]")
    base = "[3:v]"
    k = 0
    for i in range(3):
        for tag, y in (("f", 190), ("r", 900), ("z", 1340)):
            fc.append(f"{base}[{tag}{i}]overlay={360*i}:{y}[o{k}]"); base = f"[o{k}]"; k += 1
    rotulos = [rot0, "EXPORTADO (atual)", "CORRIGIDO"]
    txt = [f"drawtext=fontfile='{FONTB}':text='{titulo}':x=(w-tw)/2:y=50:fontsize=40:fontcolor=0xF6F3EE"]
    for i, r in enumerate(rotulos):
        cor = "0xD8C7AC" if i == 2 else "0xF6F3EE"
        txt.append(f"drawtext=fontfile='{FONTB}':text='{r}':x={360*i}+(360-tw)/2:y=140:fontsize=24:fontcolor={cor}")
    txt.append(f"drawtext=fontfile='{FONT}':text='recorte 1\\:1':x=20:y=860:fontsize=24:fontcolor=0x999999")
    txt.append(f"drawtext=fontfile='{FONT}':text='ampliação 2x (pixel a pixel)':x=20:y=1300:fontsize=24:fontcolor=0x999999")
    for j, linha in enumerate(nota):  # via arquivo: o drawtext não aceita ":" e "%" direto no texto
        tf = Q / f"_{saida}_nota{j}.txt"; tf.write_text(linha)
        txt.append(f"drawtext=fontfile='{FONT}':textfile='{tf}':expansion=none:x=40:y={1735 + 40*j}:fontsize=26:fontcolor=0xBBBBBB")
    fc.append(f"{base}{','.join(txt)}[v]")
    normal = Q / f"_{saida}_normal.mp4"
    ff(*args, "-filter_complex", ";".join(fc), "-map", "[v]", "-c:v", "libx264", "-preset", "slow", "-crf", "14",
       "-pix_fmt", "yuv420p", str(normal))
    for tf in Q.glob(f"_{saida}_nota*.txt"):
        tf.unlink()
    lento = Q / f"_{saida}_lento.mp4"
    ff("-i", str(normal), "-vf", "setpts=2*PTS,drawtext=fontfile='" + FONT + "':text='50 por cento':x=w-200:y=95:fontsize=24:fontcolor=0x999999",
       "-c:v", "libx264", "-preset", "slow", "-crf", "14", "-pix_fmt", "yuv420p", str(lento))
    if not juntar:
        return normal, lento
    lista = Q / f"_{saida}.txt"
    lista.write_text(f"file '{normal.resolve()}'\nfile '{lento.resolve()}'\n")
    ff("-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", "-movflags", "+faststart", str(Q / f"{saida}.mp4"))
    for f in (normal, lento, lista):
        f.unlink()
    print(Q / f"{saida}.mp4")


# Prévia 1 — introdução (5,2 s do gancho). Original = arquivo enviado, no mesmo instante da edição.
comparar("Previa_1_introducao_comparacao", "PRÉVIA 1 — INTRODUÇÃO",
         "ORIGINAL (arquivo)", [("public/originais/yuri_gancho_C6282.mp4", INI), (EXP, 0), ("out/qualidade/corrigido_intro.mp4", 0)],
         5.2, (330, 470), (420, 590),
         ["Causa principal: zoom digital de 2–4% no vídeo real (reamostragem).",
          "Também: grão sintético, cor aplicada 2x, JPEG 80 e codificação dupla.",
          "Nitidez do rosto: exportado 62% da fonte → corrigido 95%."])

# Prévia 2 — takes finais. Original = os mesmos trechos das fontes 512x910, montados nos mesmos tempos.
cen = [c for c in R["cenas"] if "IMG_27" in str(c.get("video"))]
t_ini, t_fim = cen[0]["de"], R["duracao"]
partes = []
for i, c in enumerate(cen):
    nome = c["video"].split("/")[-1]
    d = (c["ate"] if i + 1 < len(cen) else t_fim) - c["de"]
    p = Q / f"_orig_{i}.mp4"
    ff("-ss", f"{c['inicioVideo']:.3f}", "-t", f"{d:.3f}", "-i", f"public/arq_v2/originais/{nome}", "-an",
       "-vf", "fps=30,scale=1080:1920:flags=lanczos", "-c:v", "libx264", "-qp", "0", "-preset", "veryfast", str(p))
    partes.append(p)
(Q / "_orig.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in partes))
ff("-f", "concat", "-safe", "0", "-i", str(Q / "_orig.txt"), "-c", "copy", str(Q / "_orig_takes.mp4"))
# um bloco por take, cada um com o recorte no rosto (ou na mão, no detalhe): normais primeiro, depois 50%
CROPS = {"IMG_2722": ((280, 430), (380, 510)), "IMG_2721": ((310, 500), (400, 580)),
         "IMG_2723": ((180, 1150), (300, 1240)), "IMG_2720": ((360, 260), (520, 380))}
normais, lentos, acum = [], [], 0.0
for i, c in enumerate(cen):
    nome = c["video"].split("/")[-1][:8]
    d = (c["ate"] if i + 1 < len(cen) else t_fim) - c["de"]
    n, l = comparar(f"_take{i}", f"PRÉVIA 2 — TAKES FINAIS  ·  {nome}", "ORIGINAL (512x910)",
                    [(str(Q / "_orig_takes.mp4"), acum), (EXP, c["de"]), ("out/qualidade/corrigido_takes.mp4", c["de"] - 43.5)],
                    d, *CROPS[nome],
                    ["Limite real: as fontes recebidas têm 512x910 (menos da metade de 1080p).",
                     "Corrigido: sem zoom, sem redução de ruído temporal, cor 1x, nitidez discreta.",
                     "Não há detalhe novo: é o máximo do arquivo de 512x910 sem IA."], juntar=False)
    normais.append(n); lentos.append(l); acum += d
(Q / "_p2.txt").write_text("".join(f"file '{x.resolve()}'\n" for x in normais + lentos))
ff("-f", "concat", "-safe", "0", "-i", str(Q / "_p2.txt"), "-c", "copy", "-movflags", "+faststart", str(Q / "Previa_2_takes_comparacao.mp4"))
for x in normais + lentos + [Q / "_p2.txt"]:
    x.unlink()
print(Q / "Previa_2_takes_comparacao.mp4")
for p in [*partes, Q / "_orig.txt", Q / "_orig_takes.mp4"]:
    p.unlink()
