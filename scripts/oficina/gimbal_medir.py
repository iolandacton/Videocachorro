#!/usr/bin/env python3
"""Oficina Sete — mede o movimento GLOBAL da câmera em cada tomada (para a estabilização tipo gimbal).
Quadros a 29,97 fps (1 a cada 2 do original 59,94p), 512x910 em cinza → campo de movimento por blocos
(correlação de fase) → ajuste robusto de uma transformação de SIMILARIDADE (translação + giro + escala);
o apresentador, que se move sozinho, é descartado como outlier. Também mede a posição horizontal do
apresentador (mancha escura da roupa na faixa do tronco). Saída: public/oficina/gimbal/<TAKE>.npz
Uso: .venv/bin/python scripts/oficina/gimbal_medir.py [TAKE ...]
"""
import subprocess, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import geometria as G

W, H = G.W, G.H
OUT = Path("public/oficina/gimbal"); OUT.mkdir(parents=True, exist_ok=True)


def similaridade(pts, vec):
    """dx = tx + a·x − b·y ; dy = ty + b·x + a·y (x,y a partir do centro) — a = escala−1, b = giro (rad)."""
    if len(pts) < 12:
        return np.zeros(4), 0
    x, y = pts[:, 0] - W / 2, pts[:, 1] - H / 2
    A = np.r_[np.c_[np.ones_like(x), np.zeros_like(x), x, -y], np.c_[np.zeros_like(x), np.ones_like(x), y, x]]
    b = np.r_[vec[:, 0], vec[:, 1]]
    ok = np.ones(len(pts), bool)
    for _ in range(4):
        m = np.r_[ok, ok]
        p, *_ = np.linalg.lstsq(A[m], b[m], rcond=None)
        r = A @ p - b; r = np.hypot(r[:len(pts)], r[len(pts):])
        ok = r < max(0.3, np.percentile(r[ok], 70) * 2.0)
    return p, int(ok.sum())


def medir(item):
    take, _, modo = item.partition(":")      # TAKE:lento → mede TODOS os quadros (câmera lenta 50%)
    lento = modo == "lento"
    src = f"public/oficina/camera/{take}.MP4"
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", src, "-vf",
                          ("" if lento else "select='not(mod(n\\,2))',") + f"scale={W}:{H}:flags=area", "-vsync", "0", "-f", "rawvideo",
                          "-pix_fmt", "gray", "-"], stdout=subprocess.PIPE)
    ant, mov, escuro = None, [], []
    while True:
        raw = p.stdout.read(W * H)
        if len(raw) < W * H:
            break
        f = np.frombuffer(raw, np.uint8).reshape(H, W).astype(float)
        escuro.append((f[int(H * .30):int(H * .62)] < 45).mean(0))   # perfil horizontal de pixels escuros (tronco)
        if ant is not None:
            pts, vec = G.campo(ant, f)
            q, n = similaridade(pts, vec)
            mov.append([*q, n])
        ant = f
    take = take + ("_lento" if lento else "")
    np.savez(OUT / f"{take}.npz", mov=np.array(mov), escuro=np.array(escuro))
    m = np.array(mov)
    print(take, len(m) + 1, "quadros | passo médio |dx| %.2f |dy| %.2f px(512) | blocos %d" %
          (np.abs(m[:, 0]).mean(), np.abs(m[:, 1]).mean(), m[:, 4].mean()), flush=True)


if __name__ == "__main__":
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(medir, sys.argv[1:] or ["C6211", "C6212", "C6214"]))
