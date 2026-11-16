#!/usr/bin/env python3
"""Oficina Sete — "gimbal virtual": a partir do movimento medido (gimbal_medir.py) calcula, quadro a quadro,
a janela de recorte no original 4K que deixa a imagem com movimento SUAVE e o apresentador mais ao centro.

Só transformações GLOBAIS (deslocar, girar e aproximar a janela inteira) — nenhuma deformação localizada.
  P(i)  = trajetória acumulada da câmera (fundo), θ(i) = giro acumulado, s(i) = escala acumulada
  alvo  = deslocamento que centraliza o apresentador (parcial, limitado)
  janela o(i) = P(i) − suave(P(i) − alvo(i))  → o fundo passa a se mover só pelo caminho suavizado
  giro e "respiração" de escala: remove só a parte rápida (θ − suave(θ), s − suave(s))
Saída: public/oficina/gimbal/<TAKE>_janela.json  (centro em px do original 2160x3840, ângulo em graus, zoom)
"""
import json, sys
from pathlib import Path
import numpy as np

W, H, ESC = 512, 910, 2160 / 512
D = Path("public/oficina/gimbal")
# alfa = quanto da descentralização do apresentador corrigir; chaves = (tempo no take, zoom, v) com
# v = deslocamento vertical da janela em px de análise (+ = desce, para não cortar os pés em plano inteiro)
CFG = {"C6211": dict(alfa=0.85, chaves=[(0, 1.18, 0), (9.6, 1.18, 0), (12.0, 1.30, 70), (33, 1.30, 70)]),
       "C6212": dict(alfa=0.85, chaves=[(0, 1.30, 70), (33, 1.30, 70)]),
       "C6214": dict(alfa=0.85, chaves=[(0, 1.30, 70), (8.0, 1.30, 70), (10.0, 1.24, 10), (11, 1.24, 10)])}
DET = dict(alfa=0.0, chaves=[(0, 1.10, 0), (99, 1.10, 0)])   # takes de detalhe: só estabiliza
for _n, _z in (("C6215_lento", 1.32), ("C6220_lento", 1.24), ("C6221_lento", 1.16)):   # detalhes com mais balanço: mais folga
    CFG[_n] = dict(alfa=0.0, chaves=[(0, _z, 0), (99, _z, 0)])
SIGMA = 1.4                            # segundos — suavização do caminho (jeito de gimbal)


def suave(x, sig):
    n = int(4 * sig); k = np.exp(-0.5 * (np.arange(-n, n + 1) / sig) ** 2); k /= k.sum()
    return np.convolve(np.pad(x, n, mode="edge"), k, "valid")


def apresentador(esc):
    """centro horizontal do tronco (mancha escura mais densa), seguindo quadro a quadro."""
    xs = np.arange(W); out = []; ant = None
    for e in esc:
        m = e > 0.45
        if ant is not None:
            m &= np.abs(xs - ant) < 110
        elif m.any():      # 1º quadro: o trecho contínuo mais largo fora da borda esquerda (janela/esquadria)
            m &= xs > 0.22 * W
        if m.sum() < 8:
            out.append(ant if ant is not None else W / 2); continue
        c = float((xs[m] * e[m]).sum() / e[m].sum()); out.append(c); ant = c
    return np.array(out)


def janela(nome, fps=30000 / 1001):
    """nome = TAKE ou TAKE_lento (todos os quadros do 59,94p tocados a 29,97: a suavização vale no tempo de exibição)."""
    take = nome.split("_")[0]
    d = np.load(D / f"{nome}.npz"); cfg = CFG.get(nome, DET)
    mov = -d["mov"][:, :4]   # a correlação mede o quadro anterior em relação ao seguinte: inverte → movimento do conteúdo
    n = len(mov) + 1
    tt = np.arange(n) / fps; ch = np.array(cfg["chaves"], float)
    z = suave(np.interp(tt, ch[:, 0], ch[:, 1]), 0.7 * fps)
    mx, my = (1 - 1 / z) / 2 * W, (1 - 1 / z) / 2 * H      # folga de cada lado, quadro a quadro
    sig = SIGMA * fps
    alvo_x = np.zeros(n)
    if cfg["alfa"]:
        xp = suave(apresentador(d["escuro"]), 0.5 * fps)
        alvo_x = np.clip(cfg["alfa"] * (xp - W / 2), -0.72 * mx, 0.72 * mx)
    alvo_y = np.minimum(suave(np.interp(tt, ch[:, 0], ch[:, 2]), 0.7 * fps), 0.8 * my)
    ox, oy = alvo_x.copy(), alvo_y.copy()
    for _ in range(3):   # o deslocamento medido no centro do quadro é levado ao centro da janela (giro/escala)
        dx = mov[:, 0] + mov[:, 2] * ox[:-1] - mov[:, 3] * oy[:-1]
        dy = mov[:, 1] + mov[:, 3] * ox[:-1] + mov[:, 2] * oy[:-1]
        Px, Py = np.r_[0, np.cumsum(dx)], np.r_[0, np.cumsum(dy)]
        ox = Px - suave(Px - alvo_x, sig); oy = Py - suave(Py - alvo_y, sig)
    th = np.r_[0, np.cumsum(mov[:, 3])]; sc = np.r_[0, np.cumsum(mov[:, 2])]
    giro = th - suave(th, sig); resp = sc - suave(sc, sig)
    # nunca sair do quadro: se o tremor + centralização pedirem mais que a folga, limita (suavemente, no pico)
    # (o giro e a respiração da janela também gastam folga nos cantos)
    lx = mx - (np.abs(giro) * H / 2 + np.abs(resp) * W / 2) / z - 1.0
    ly = my - (np.abs(giro) * W / 2 + np.abs(resp) * H / 2) / z - 1.0
    fx, fy = (np.abs(ox) / lx).max(), (np.abs(oy) / ly).max()
    aviso = ""
    if fx > 1 or fy > 1:
        aviso = f" (limitado: pediu {fx:.2f}× / {fy:.2f}× a folga)"
        ox, oy = np.clip(ox, -lx, lx), np.clip(oy, -ly, ly)
    out = {"take": take, "zoom": np.round(z, 4).tolist(), "fps": fps,
           "cx": np.round((W / 2 + ox) * ESC, 2).tolist(), "cy": np.round((H / 2 + oy) * ESC, 2).tolist(),
           "ang": np.round(np.degrees(giro), 4).tolist(), "esc": np.round(resp, 5).tolist()}
    (D / f"{nome}_janela.json").write_text(json.dumps(out))
    print(f"{nome}: zoom {z.min():.2f}–{z.max():.2f} | janela x {ox.min():+.0f}..{ox.max():+.0f} de ±{mx.max():.0f}, y {oy.min():+.0f}..{oy.max():+.0f} de ±{my.max():.0f}"
          f" | giro corrigido ±{np.degrees(np.abs(giro).max()):.2f}° | alvo x {alvo_x.min():+.0f}..{alvo_x.max():+.0f}{aviso}")
    return out


if __name__ == "__main__":
    for t in sys.argv[1:] or ["C6211", "C6212", "C6214"] + [f"C62{i}_lento" for i in range(15, 23)]:
        janela(t)
