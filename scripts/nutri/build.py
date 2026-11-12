"""Reel do nutricionista — prepara o vídeo COMPLETO (cortes, voz, proxies, legendas, eventos).

Uso: python -I scripts/nutri/build.py <pasta_com_C64xx.MP4> [--timeline-only]
     python -I scripts/nutri/music.py <musica.mp3>
Gera (fora do git): public/nutri/full/{seg_N.mp4, voz.wav}
Gera (no git):      src/nutri/reel.json  (linha do tempo para o Remotion)

Todos os tempos abaixo são segundos do ARQUIVO ORIGINAL de cada clipe; o script converte
para o tempo final (cortes + aceleração de 6%). Textos = o que ele fala.
"""
import json, os, subprocess, sys
import numpy as np

RAW = sys.argv[1]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUT = os.path.join(ROOT, "public", "nutri", "full"); os.makedirs(OUT, exist_ok=True)
FPS, SPEED = 30, 1.06
TAIL = 1.72  # sobra do último clipe para o cartão final (s do original)

def run(*a):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *a], check=True)

# ---------- 1. CORTES (EDL) ----------
# O corte 3→4 cai no silêncio do "p" de "primeira" (emenda a 1ª tomada com a 2ª, limpa).
EDL = [
    ("C6490", 0.50, 11.10),   # 0 gancho
    ("C6492", 1.78, 14.75),   # 1 queixa dos pacientes
    ("C6492", 15.15, 17.54),  # 2 "Só que quando a gente vai ver lá no exame de sangue, a"
    ("C6492", 33.80, 41.98),  # 3 2ª tomada: "primeira coisa ... testosterona baixa: 200, 100 ... 50"
    ("C6496", 1.40, 16.27),   # 4 revelação (estradiol)
    ("C6497", 0.40, 7.12),    # 5 consequência 1 (descarta os 3 recomeços de 7,4–11,5 s)
    ("C6497", 11.52, 16.10),  # 6 consequência 2
    ("C6498", 1.35, 8.25),    # 7 chamada final
]
starts = []; acc = 0.0
for _, a, b in EDL:
    starts.append(acc); acc += (b - a) / SPEED
VOICE_END = acc
TOTAL = VOICE_END + TAIL / SPEED
T = lambda seg, src: round(starts[seg] + (src - EDL[seg][1]) / SPEED, 3)

# ---------- 2. LEGENDAS ----------
# DSL: palavras "texto@tempo"; " | " = nova linha. Prefixos: * dourado  ~ rosa  ^ vermelho
#      ! alerta gigante  # número gigante  q: citação. Sufixo %t = risco vermelho no tempo t.
CAPS = [
    (0, "type", "Reposição@0.66 hormonal@1.26 | em@1.66 pacientes@1.82 obesos@2.26 | *nem@2.78 *sempre@3.12 | vai@3.58 ser@3.78 a@4.06 primeira@4.3 opção,@4.76"),
    (0, "pop", "mesmo@5.44 com@5.8 as@5.98 taxas@6.16 | *altamente@6.72 *alteradas@7.34"),
    (0, "pop", "no@7.86 | *exame@8.0 *de@8.3 *sangue.@8.4"),
    (0, "pop", "E@9.12 nesse@9.34 vídeo@9.76 | vou@9.98 te@10.14 explicar@10.22"),
    (0, "pop", "*o@10.44 *porquê.@10.6"),
    (1, "pop", "Muitas@1.88 vezes@2.34 | os@2.58 pacientes@2.76 chegam@3.1"),
    (1, "pop", "aqui@3.44 no@3.58 meu@3.68 | *consultório,@3.82"),
    (1, "pop", "pacientes@4.48 | *obesos,@4.9"),
    (1, "pop", "com@5.54 obesidade@5.62 de@6.3 | *grau@6.46 *1,@6.64 *grau@6.96 *2,@7.12"),
    (1, "pop", "com@7.4 mais@7.52 de@7.72 | *100@7.82 *quilos,@8.0"),
    (1, "pop", "e@8.6 sempre@8.98 me@9.2 relatam@9.36 | uma@9.84 coisa:@10.22"),
    (1, "pop", "q:“Doutor,@10.96 | q:minha@11.56 q:indisposição,@11.7"),
    (1, "pop", "q:minha@12.82 q:libido,@12.94 | q:preciso@13.8 q:melhorar.”@14.14"),
    (2, "pop", "Só@15.24 que@15.44 quando@15.68 | a@16.18 gente@16.28 vai@16.36 ver@16.46"),
    (2, "pop", "lá@16.58 no@16.72 | *exame@16.84 *de@17.04 *sangue,@17.18"),
    (3, "pop", "a@33.80 primeira@33.86 coisa@34.08 | que@34.34 eles@34.46 apontam@34.58"),
    (3, "pop", "no@34.94 exame,@35.04 geralmente,@35.36 | é@35.94 sempre@36.04 a@36.42"),
    (3, "pop", "*testosterona@36.92 | ^baixa:@38.18"),
    (3, "pop", "de@39.0 | #200,@39.1"),
    (3, "pop", "#100,@40.04"),
    (3, "pop", "já@40.62 peguei@40.78 casos@41.0 até@41.2 de@41.32 | #50.@41.48"),
    (4, "pop", "E@1.56 nesses@2.14 casos,@2.4"),
    (4, "pop", "mesmo@3.18 fazendo@3.3 a@3.64 | *reposição@3.78 *hormonal,@4.24"),
    (4, "pop", "essa@5.0 reposição@5.54"),
    (4, "pop", "!NÃO@6.04 | vai@6.2 ser@6.3 convertida@6.42"),
    (4, "pop", "em@7.0 *testosterona@7.3%7.65 | dentro@7.92 do@8.3 corpo,@8.46"),
    (4, "pop", "justamente@9.1 por@9.5 conta@9.78 do@10.0"),
    (4, "pop", "acúmulo@10.14 de@10.6 | *gordura@10.7 *corporal,@11.02"),
    (4, "pop", "essa@11.84 *testosterona@12.04"),
    (4, "pop", "vai@12.72 ser@12.86 convertida@12.98 em@13.62"),
    (4, "pop", "um@15.18 | ~hormônio@15.4 ~feminino.@15.68"),
    (5, "pop", "Por@0.5 isso@0.64 que@0.78 | muitas@0.9 vezes@1.12"),
    (5, "pop", "o@1.5 obeso@1.68 tem@2.22 a@2.42 | *predisposição@2.56 *maior,@3.16"),
    (5, "pop", "com@3.54 o@3.86 uso@3.98 hormonal,@4.14"),
    (5, "pop", "de@4.68 ter@5.22 | ~mamas@5.54 ~mais@6.14 | ~acentuadas,@6.36"),
    (6, "pop", "além@11.62 de@11.74 que@11.88 também@11.96 | pode@12.3 acarretar@12.5"),
    (6, "pop", "no@13.64 | ^fígado,@14.38"),
    (6, "pop", "^sobrecarregando.@15.24"),
    (7, "pop", "E@1.48 se@2.04 você@2.18 | quer@2.34 traçar@2.54"),
    (7, "pop", "um@2.9 *caminho@3.1 | *mais@3.38 *seguro@3.62"),
    (7, "pop", "para@4.1 a@4.34 sua@5.08 | *saúde,@5.28"),
    (7, "pop", "marque@6.3 seu@6.46 | *acompanhamento@6.58 | *nutricional.@7.3"),
]
PREF = {"*": "key", "~": "keyPink", "^": "keyRed", "!": "alert", "#": "num"}
groups = []
for seg, typ, dsl in CAPS:
    lines = []
    for ln in dsl.split(" | "):
        ws = []
        for tok in ln.split():
            text, t = tok.rsplit("@", 1); strike = None
            if "%" in t: t, strike = t.split("%")
            kind = "normal"
            if text.startswith("q:"): kind, text = "quote", text[2:]
            elif text[0] in PREF: kind, text = PREF[text[0]], text[1:]
            w = {"t": T(seg, float(t)), "text": text, "kind": kind}
            if strike: w["strikeAt"] = T(seg, float(strike))
            ws.append(w)
        lines.append(ws)
    groups.append({"type": typ, "start": lines[0][0]["t"], "lines": lines})
for i, g in enumerate(groups):
    last = max(w["t"] for l in g["lines"] for w in l)
    nxt = groups[i + 1]["start"] if i + 1 < len(groups) else VOICE_END
    g["end"] = round(min(nxt - 0.03, last + 2.0), 3)

# ---------- 3. ZOOMS (cortes secos) e EVENTOS ----------
Z = [
    (0, 0.50, 1.0, 1.05), (0, 2.78, 1.3, 1.36), (0, 5.44, 1.0, 1.05), (0, 6.72, 1.22, 1.27), (0, 9.12, 1.0, 1.04), (0, 10.44, 1.42, 1.5),
    (1, 1.78, 1.1, 1.14), (1, 3.44, 1.32, 1.37), (1, 5.54, 1.0, 1.05), (1, 7.4, 1.3, 1.36), (1, 8.6, 1.06, 1.1), (1, 10.96, 1.34, 1.4), (1, 12.82, 1.5, 1.56),
    (2, 15.15, 1.0, 1.05), (2, 16.58, 1.25, 1.3),
    (3, 33.80, 1.08, 1.12), (3, 36.42, 1.36, 1.42), (3, 39.0, 1.0, 1.03), (3, 40.04, 1.22, 1.25), (3, 40.62, 1.05, 1.08), (3, 41.4, 1.5, 1.58),
    (4, 1.40, 1.0, 1.06), (4, 3.18, 1.26, 1.31), (4, 5.0, 1.08, 1.12), (4, 6.04, 1.48, 1.55), (4, 7.92, 1.0, 1.04), (4, 9.1, 1.04, 1.4), (4, 15.15, 1.52, 1.62),
    (5, 0.40, 1.0, 1.05), (5, 2.42, 1.28, 1.33), (5, 3.54, 1.05, 1.1), (5, 5.22, 1.4, 1.48),
    (6, 11.52, 1.0, 1.04), (6, 13.64, 1.35, 1.4), (6, 15.24, 1.52, 1.6),
    (7, 1.35, 1.0, 1.06), (7, 2.9, 1.25, 1.3), (7, 4.1, 1.05, 1.1), (7, 6.3, 1.3, 1.5),
]
zooms = [[T(s, t), a, b] for s, t, a, b in Z]
CUT_IN, CUT_OUT, ESTRADIOL = T(4, 11.84), T(4, 15.15), T(4, 14.1)
ev = {
    "cutIn": CUT_IN, "cutOut": CUT_OUT, "estradiol": ESTRADIOL,
    "tension": [T(4, 9.1), CUT_IN],
    # [tempo, amplitude]
    "shakes": [[T(0, 4.76), 8], [T(3, 39.1), 10], [T(3, 40.04), 13], [T(3, 41.48), 22], [T(4, 6.04), 14], [ESTRADIOL, 22],
               [CUT_OUT, 10], [T(6, 14.38), 10], [T(6, 15.24), 18]],
    # [tempo, duração, pico]
    "redFlashes": [[T(3, 41.48), 0.45, 0.6], [T(4, 6.04), 0.3, 0.28], [ESTRADIOL, 0.5, 0.7], [T(6, 15.24), 0.4, 0.45]],
    "redEdges": [[T(3, 38.18), 0.7, 0.7], [T(3, 41.48), 0.9, 0.95], [T(4, 6.04), 0.7, 0.9], [T(6, 14.38), 0.6, 0.6], [T(6, 15.24), 0.9, 0.95]],
    "whiteFlashes": [[CUT_IN, 0.16, 0.9], [CUT_OUT, 0.14, 0.8]],
    "goldSweep": T(7, 6.58),
    "endCard": VOICE_END - 0.15,
}
# sons
cut_times = sorted(set([z[0] for z in zooms[1:]] + [CUT_IN, CUT_OUT]))
whoosh = []
for t in cut_times:
    if not whoosh or t - whoosh[-1] > 0.9: whoosh.append(t)
pops = [min(w["t"] for l in g["lines"] for w in l if w["kind"] in ("key", "keyPink", "quote"))
        for g in groups if g["type"] == "pop" and any(w["kind"] in ("key", "keyPink", "quote") for l in g["lines"] for w in l)]
ev["sfx"] = {
    "whoosh": whoosh, "pop": pops,
    "impact": [[T(0, 4.76), 0.35], [T(3, 39.1), 0.4], [T(3, 40.04), 0.5], [T(3, 41.48), 0.65], [T(4, 6.04), 0.6],
               [ESTRADIOL, 0.6], [CUT_OUT, 0.35], [T(6, 14.38), 0.4], [T(6, 15.24), 0.6]],
    "stamp": [T(4, 7.65)], "riser": round(ESTRADIOL - 5, 3), "typing": [T(0, 0.66), T(0, 5.1)],
}

MEDIA = "--timeline-only" not in sys.argv
# ---------- 4. VOZ ----------
parts = []
for i, (clip, a, b) in enumerate(EDL if MEDIA else []):
    end = b + (TAIL if i == len(EDL) - 1 else 0)
    p = os.path.join(OUT, f"_v{i}.wav")
    d = end - a
    run("-ss", f"{a}", "-t", f"{d}", "-i", os.path.join(RAW, clip + ".MP4"), "-vn", "-ac", "2", "-ar", "48000",
        "-af", f"highpass=70,afade=t=in:d=0.006,afade=t=out:st={d - 0.006}:d=0.006", p)
    parts.append(p)
lst = os.path.join(OUT, "_list.txt")
open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
if MEDIA: run("-f", "concat", "-safe", "0", "-i", lst, "-af", f"atempo={SPEED},loudnorm=I=-15:TP=-2:LRA=9", "-ar", "48000", os.path.join(OUT, "voz.wav"))
for p in parts + [lst]: os.remove(p)


# ---------- 5. VÍDEO (proxies 1620x2880, já acelerados) ----------
segs = []
for i, (clip, a, b) in enumerate(EDL):
    extra = TAIL if i == len(EDL) - 1 else 0.12
    if MEDIA: run("-ss", f"{a}", "-t", f"{b - a + extra}", "-i", os.path.join(RAW, clip + ".MP4"), "-an",
        "-vf", f"setpts=PTS/{SPEED},scale=1620:2880:flags=lanczos,fps={FPS},format=yuv420p",
        "-c:v", "libx264", "-crf", "16", "-preset", "medium", os.path.join(OUT, f"seg_{i}.mp4"))
    segs.append({"file": f"nutri/full/seg_{i}.mp4", "from": int(round(starts[i] * FPS))})
    print("seg", i, clip, f"{a}-{b}", "→ início", round(starts[i], 2), flush=True)
# (apoio de camisa branca removido a pedido do cliente; música: scripts/nutri/music.py)

total_frames = int(round(TOTAL * FPS))
for i, s in enumerate(segs):
    s["frames"] = (segs[i + 1]["from"] if i + 1 < len(segs) else total_frames) - s["from"]
json.dump({"fps": FPS, "totalFrames": total_frames, "voiceEnd": round(VOICE_END, 3), "segs": segs, "zooms": zooms,
           "groups": groups, "ev": ev}, open(os.path.join(ROOT, "src", "nutri", "reel.json"), "w"), ensure_ascii=False, indent=1)
print(f"total {TOTAL:.2f}s ({total_frames} quadros) | fala termina em {VOICE_END:.2f}s | {len(groups)} grupos de legenda")
