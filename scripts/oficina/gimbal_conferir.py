#!/usr/bin/env python3
"""Confere a estabilização: mede o movimento do fundo no arquivo original (cam/) e no estabilizado (gimbal/)
e compara o tremor (desvio em relação ao caminho suave de 1 s) e o "passo" quadro a quadro.
Uso: .venv/bin/python scripts/oficina/gimbal_conferir.py ARQ_ANTES ARQ_DEPOIS [inicio fim]"""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).parent))
import geometria as G
from gimbal_medir import similaridade
from gimbal_caminho import suave


def tremor(arq, ss, t):
    f = G.frames(arq, ss, t); mov = []
    for a, b in zip(f, f[1:]):
        pts, vec = G.campo(a, b); q, _ = similaridade(pts, vec); mov.append(q)
    m = np.array(mov); P = np.cumsum(m[:, :2], 0); th = np.degrees(np.cumsum(m[:, 3]))
    hf = lambda x: x - suave(x, 30)
    acel = np.diff(m[:, :2], axis=0)      # variação do passo de um quadro para o outro (o "tranco")
    return dict(x=hf(P[:, 0]).std(), y=hf(P[:, 1]).std(), giro=hf(th).std(), tranco=np.hypot(*acel.T).mean())


if __name__ == "__main__":
    a, d = sys.argv[1:3]; ss, fim = (float(v) for v in sys.argv[3:5]) if len(sys.argv) > 3 else (0, 12)
    A, B = tremor(a, ss, fim - ss), tremor(d, ss, fim - ss)
    print(f"{Path(d).name} [{ss:.0f}–{fim:.0f}s]  tremor x {A['x']:.2f}→{B['x']:.2f}  y {A['y']:.2f}→{B['y']:.2f} px(512)"
          f"  giro {A['giro']:.3f}→{B['giro']:.3f}°  tranco quadro a quadro {A['tranco']:.2f}→{B['tranco']:.2f} px")
