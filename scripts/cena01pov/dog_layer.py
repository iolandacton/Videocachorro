"""Camada do Yorkshire para a CENA 01 (POV) — composição convencional, sem IA generativa.

Gera PNGs RGBA 1080x1920 (só o cachorro, fundo transparente) para sobrepor à filmagem
real da praia no Remotion. A câmera está "presa" nas costas: o dorso fica quase fixo no
quadro e só a cabeça, as orelhas e o pelo se movem, no ritmo do trote (src/cena01pov/trot.json).

Etapas por quadro:
  1. Deformação local (cv2.remap): aceno da cabeça atrasado em relação ao trote, pequenos
     giros, orelhas balançando e ondulação do pelo nas bordas. O dorso não se mexe.
  2. Nitidez casada com a filmagem: reduz à resolução da fonte (512 px de largura) e amplia.
  3. Cor/exposição casadas com a areia molhada da filmagem, sem aumentar saturação/contraste.
  4. Leve luz de recorte quente nas bordas superiores (o sol está à frente do cachorro).
  5. Grão equivalente ao da filmagem.

Uso: python -I scripts/cena01pov/dog_layer.py   (requer numpy e opencv; ver requirements.txt)
"""
import json
import math
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = json.load(open(os.path.join(ROOT, "src", "cena01pov", "trot.json")))
D = P["dog"]
W, H, FPS, N = 1080, 1920, P["fps"], P["frames"]
SRC_W = 512  # largura da filmagem original
# MOTION=real → movimento medido no vídeo real do Yorkshire (src/cena01pov/gait_real.json)
REAL = os.environ.get("MOTION") == "real"
if REAL:
    G = json.load(open(os.path.join(ROOT, "src", "cena01pov", "gait_real.json")))
    N = G["frames"]
OUT = os.path.join(ROOT, "public", "cena01pov", "dog_real" if REAL else "dog")
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

# ---------- 1. Recorte e enquadramento ----------
cut = cv2.imread(os.path.join(ROOT, "public", "cena01pov", "yorkshire_recorte.png"), cv2.IMREAD_UNCHANGED)
cut = cut.astype(np.float32) / 255.0
ys, xs = np.where(cut[..., 3] > 0.5)
top, bot, l, r = ys.min(), ys.max(), xs.min(), xs.max()
pad = 60
crop = cut[max(0, top - pad): top + int((bot - top) * D["keepHeightFrac"]), max(0, l - pad): r + pad]
tw = int(W * D["widthFrac"])
s = tw / crop.shape[1]
crop = cv2.resize(crop, (tw, int(crop.shape[0] * s)), interpolation=cv2.INTER_AREA)
ch, cw = crop.shape[:2]
# premultiplica para a deformação não criar halos
rgb0 = crop[..., :3] * crop[..., 3:4]
a0 = crop[..., 3]

# posição fixa (montagem nas costas): base cortada pela borda inferior
x0 = (W - cw) // 2
y0 = H - int((ch - pad * s) * D["visibleFrac"])

# ---------- pesos espaciais ----------
yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
yn, xn = yy / ch, xx / cw
w_head = np.clip(1 - yn / 0.62, 0, 1) ** 1.5           # topo = cabeça; base (dorso) = 0
w_ear = w_head * np.clip(np.abs(xn - 0.5) * 2.2 - 0.25, 0, 1) ** 1.5
side = np.sign(xn - 0.5)
er = cv2.erode((a0 > 0.5).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32)
w_edge = np.clip(cv2.GaussianBlur(a0 - er * a0, (0, 0), 6) * 3, 0, 1)  # fios soltos/bordas
w_rim = np.clip(a0 - cv2.GaussianBlur(er, (0, 0), 5), 0, 1) * np.clip(1 - yn / 0.75, 0, 1)

# ruído suave para o pelo (duas texturas que deslizam no tempo)
def smooth_noise(seed):
    g = np.random.default_rng(seed).standard_normal((ch // 24 + 3, cw // 24 + 3)).astype(np.float32)
    return cv2.resize(g, (cw + 200, ch + 200), interpolation=cv2.INTER_CUBIC)
NX, NY = smooth_noise(1), smooth_noise(2)

# ---------- 3. referência de cor/exposição na filmagem ----------
cap = cv2.VideoCapture(os.path.join(ROOT, "public", "cena01pov", "praia_3.5-8.5.mov"))
refs, full = [], []
for i in range(0, N, 25):
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, fr = cap.read()
    if ok:
        refs.append(fr[int(H * 0.62):, :].astype(np.float32) / 255.0)
        full.append(fr[::4, ::4].astype(np.float32) / 255.0)
cap.release()
plate_ref = np.concatenate([x.reshape(-1, 3) for x in refs])
lab = lambda x: cv2.cvtColor(np.clip(x, 0, 1).astype(np.float32), cv2.COLOR_BGR2LAB)
ref_lab = lab(plate_ref.reshape(-1, 1, 3)).reshape(-1, 3)
# Exposição: compara a FOTO inteira (realces e areia ao fundo) com a filmagem, e não o pelo
# preto com a areia. Ganho multiplicativo em L preserva os pretos; não mexe em contraste.
photo = cv2.imread(os.path.join(ROOT, "refs", "cena01", "yorkshire_costas.jpg")).astype(np.float32) / 255.0
photo_lab = lab(photo)
photo_bg = photo_lab[cut[..., 3] < 0.02]
full_L = lab(np.concatenate([x.reshape(-1, 1, 3) for x in full]))[..., 0]
k_L = 1 + 0.7 * (np.percentile(full_L, 99) / np.percentile(photo_lab[..., 0], 99) - 1)
d_a = 0.5 * (ref_lab[:, 1].mean() - photo_bg[:, 1].mean())   # balanço de branco da luz da praia
d_b = 0.5 * (ref_lab[:, 2].mean() - photo_bg[:, 2].mean())
# brilho dos realces da filmagem para a luz de recorte
hi = plate_ref[plate_ref.mean(1) > np.percentile(plate_ref.mean(1), 99)].mean(0)
rim_col = np.clip(hi / hi.max(), 0, 1)

# grão: desvio padrão do alto-falante (detalhe fino) da filmagem, em área de areia
gray = cv2.cvtColor(refs[len(refs) // 2], cv2.COLOR_BGR2GRAY)
grain_sd = float(np.std(gray - cv2.GaussianBlur(gray, (0, 0), 1.5))) * 0.6
print(f"cor: ganho L={k_L:.3f} da={d_a:.2f} db={d_b:.2f} | grão sd={grain_sd:.4f} | cachorro {cw}x{ch} em ({x0},{y0})")

# ---------- movimento medido (modo real) ----------
if REAL:
    # Conversão física: fração da altura do cachorro (~0.25 m) → deslocamento da cabeça a ~0.15 m
    # da câmera (f ≈ 805 px no quadro 1080x1920). Metade do medido (máscara inclui pernas/pelo).
    PX = 0.5 * 0.25 * 805 / 0.15
    head_dy = np.array(G["heady"]) * PX
    head_dx = np.array(G["headx"]) * PX + np.clip(np.array(G["headx_slow"]) * 0.5 * 0.12 * 805 / 0.15, -25, 25)
    # orelhas/pelo: mola amortecida excitada pela aceleração vertical REAL do corpo (sem ciclo fixo)
    vert = np.array(G["vert"]); acc = np.gradient(np.gradient(vert)) * FPS * FPS
    wn, z, dt = 2 * math.pi * 5.0, 0.25, 1 / FPS
    x = v = 0.0; spring = []
    for a_ in acc:
        for _ in range(4):
            v += (-wn * wn * x - 2 * z * wn * v - a_) * dt / 4; x += v * dt / 4
        spring.append(x)
    spring = np.array(spring); spring = spring / (np.abs(spring).max() + 1e-9)
    print(f"real: cabeça dy ±{np.abs(head_dy).max():.0f}px dx ±{np.abs(head_dx).max():.0f}px")

# ---------- render por quadro ----------
small = (int(cw * SRC_W / W), int(ch * SRC_W / W))
for f in range(N):
    t = f / FPS
    ph = 2 * math.pi * P["strideHz"] * t
    amp = 1 + 0.15 * math.sin(2 * math.pi * 0.7 * t) + 0.05 * math.sin(2 * math.pi * 1.9 * t)
    # 1. deslocamentos (px)
    dy = D["mountFlexY"] * math.sin(2 * ph - 0.3) * amp \
        + D["headNodY"] * math.sin(2 * ph - 1.0) * amp * w_head
    dx = (D["headYawX"] * math.sin(2 * math.pi * 0.35 * t + 0.5)
          + D["headRollX"] * math.sin(ph - 0.6) * amp) * w_head
    ear = D["earFlap"] * amp * (math.sin(2 * ph - 1.8) + 0.35 * math.sin(4 * ph - 2.4))
    dx = dx + ear * w_ear * side
    dy = dy + 0.7 * ear * w_ear
    o = int(40 * t) % 200
    dx = dx + D["hairRipple"] * w_edge * NX[o:o + ch, o:o + cw]
    dy = dy + D["hairRipple"] * w_edge * NY[o:o + ch, o:o + cw]
    if REAL:  # substitui todo o movimento sintético pelo medido
        ear = D["earFlap"] * 1.5 * spring[f]
        dy = head_dy[f] * w_head + 0.7 * ear * w_ear
        dx = head_dx[f] * w_head + ear * w_ear * side
        o = int(25 * t) % 200
        dx = dx + D["hairRipple"] * (1 + abs(spring[f])) * w_edge * NX[o:o + ch, o:o + cw]
        dy = dy + D["hairRipple"] * (1 + abs(spring[f])) * w_edge * NY[o:o + ch, o:o + cw]
    mx, my = (xx - dx).astype(np.float32), (yy - dy).astype(np.float32)
    rgb = cv2.remap(rgb0, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    a = cv2.remap(a0, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    rim = cv2.remap(w_rim, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    # 2. nitidez da filmagem
    rgba = np.dstack([rgb, a])
    rgba = cv2.resize(cv2.resize(rgba, small, interpolation=cv2.INTER_AREA), (cw, ch), interpolation=cv2.INTER_CUBIC)
    rgb, a = rgba[..., :3], np.clip(rgba[..., 3], 0, 1)
    un = np.where(a[..., None] > 1e-3, rgb / np.maximum(a[..., None], 1e-3), 0)
    # 3. cor/exposição
    L = lab(un)
    L[..., 0] = np.clip(L[..., 0] * k_L, 0, 100)
    L[..., 1] += d_a
    L[..., 2] += d_b
    un = np.clip(cv2.cvtColor(L, cv2.COLOR_LAB2BGR), 0, 1)
    # 4. luz de recorte (tela, sutil)
    rr = np.clip(cv2.resize(cv2.resize(rim, small, interpolation=cv2.INTER_AREA), (cw, ch)), 0, 1)[..., None] * 0.16
    un = 1 - (1 - un) * (1 - rim_col * rr)
    # 5. grão (gerado na resolução da fonte e ampliado, como na filmagem)
    g = rng.standard_normal((small[1], small[0])).astype(np.float32)
    g = cv2.resize(g, (cw, ch), interpolation=cv2.INTER_CUBIC)
    un = np.clip(un + (g * grain_sd)[..., None], 0, 1)
    # monta o quadro inteiro
    canvas = np.zeros((H, W, 4), np.float32)
    yA, yB = max(0, y0), min(H, y0 + ch)
    canvas[yA:yB, x0:x0 + cw, :3] = un[yA - y0:yB - y0]
    canvas[yA:yB, x0:x0 + cw, 3] = a[yA - y0:yB - y0]
    cv2.imwrite(os.path.join(OUT, f"d_{f:04d}.png"), (canvas * 255 + 0.5).astype(np.uint8))
    if f % 30 == 0:
        print("quadro", f, file=sys.stderr)
print("pronto:", N, "quadros em", OUT)
