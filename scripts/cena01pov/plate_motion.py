"""Aplica à filmagem REAL da praia o movimento de câmera medido no Yorkshire real.

Física: a praia é plana. Uma câmera que sobe/desce (Δh) sobre um plano desloca cada ponto do
chão proporcionalmente à sua distância à linha do horizonte (homografia do plano):
    y' = yh + (y - yh) * (1 + Δh/h)        x' = x - (Δx/h) * (y - yh)
O céu (no infinito) não se move com translação. Δh/h ≈ fração medida da altura do cachorro
(câmera na altura do dorso), usando metade do valor medido. Motion blur: 3 subamostras do
mesmo movimento (obturador 180°). Nenhum pixel novo é criado; só deformação geométrica.
"""
import json, os
import cv2, numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
G = json.load(open(os.path.join(ROOT, "src", "cena01pov", "gait_real.json")))
N, YH, K, ZOOM = G["frames"], 1179.0, 0.5, 1.03
OUT = os.path.join(ROOT, "public", "cena01pov", "plate_real"); os.makedirs(OUT, exist_ok=True)
vert, lat = np.array(G["vert"]), np.array(G["lat"])
ti = np.arange(N)
interp = lambda s, t: np.interp(t, ti, s)
cap = cv2.VideoCapture(os.path.join(ROOT, "public", "cena01pov", "praia_3.5-8.5.mov"))
H, W = 1920, 1080
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
# zoom leve (esconde bordas do cisalhamento), ancorado no horizonte
yz = YH + (yy - YH) / ZOOM; xz = W / 2 + (xx - W / 2) / ZOOM
below = np.clip(yz - YH, 0, None)
for f in range(N):
    ok, fr = cap.read()
    acc = np.zeros_like(fr, np.float32)
    for k, dtt in enumerate((-0.25, 0.0, 0.25)):
        sv = K * interp(vert, f + dtt); sl = K * interp(lat, f + dtt)
        my = np.where(yz > YH, YH + below / (1 + sv), yz).astype(np.float32)
        mx = (xz + sl * below).astype(np.float32)
        acc += cv2.remap(fr, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
    cv2.imwrite(os.path.join(OUT, f"p_{f:04d}.jpg"), (acc / 3).astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 96])
print("placa:", N, "quadros | desloc. máx. na base: vertical ±%.0fpx, lateral ±%.0fpx" % (
    np.abs(K * vert).max() * (H - YH) * ZOOM, np.abs(K * lat).max() * (H - YH) * ZOOM))
