#!/usr/bin/env python3
"""Mede deformação NÃO RÍGIDA ("efeito borracha") entre quadros consecutivos.
Campo de movimento por blocos (correlação de fase) → ajuste robusto de uma transformação global afim
(o protagonista, que se move sozinho, sai como outlier) → resíduo nos blocos rígidos. Resíduo que oscila
de quadro para quadro = linhas retas entortando/esticando. Também mede o "cisalhamento" vertical
(deslocamento horizontal variando com a altura: assinatura de rolling shutter / warp)."""
import subprocess
import numpy as np

W, H, B, P = 512, 910, 48, 32   # resolução de análise, tamanho do bloco, passo


def frames(p, ss, t, vf=""):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ss:.3f}", "-t", f"{t:.3f}", "-i", p, "-vf",
                          (vf + "," if vf else "") + f"scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(float)


def _desloc(a, b):
    A = np.fft.fft2(a - a.mean()); Bf = np.fft.fft2(b - b.mean()); R = A * np.conj(Bf); R /= np.abs(R) + 1e-9
    c = np.real(np.fft.ifft2(R)); iy, ix = np.unravel_index(np.argmax(c), c.shape); h, w = c.shape
    def sub(cm, c0, cp): d = cm - 2 * c0 + cp; return 0 if d == 0 else 0.5 * (cm - cp) / d
    dx = (ix if ix < w // 2 else ix - w) + sub(c[iy, (ix - 1) % w], c[iy, ix], c[iy, (ix + 1) % w])
    dy = (iy if iy < h // 2 else iy - h) + sub(c[(iy - 1) % h, ix], c[iy, ix], c[(iy + 1) % h, ix])
    return dx, dy, c.max()


def campo(f0, f1, roi=None):
    pts, vec = [], []
    win = np.outer(np.hanning(B), np.hanning(B))
    for y in range(0, H - B, P):
        for x in range(0, W - B, P):
            a, b = f0[y:y + B, x:x + B], f1[y:y + B, x:x + B]
            if a.std() < 6:   # bloco sem textura (parede lisa): não dá para medir
                continue
            dx, dy, q = _desloc(a * win, b * win)
            if q < 0.08:
                continue
            pts.append((x + B / 2, y + B / 2)); vec.append((dx, dy))
    return np.array(pts), np.array(vec)


def residuo(pts, vec):
    """ajuste afim robusto (3 iterações descartando outliers) → resíduo médio dos inliers e cisalhamento."""
    if len(pts) < 12:
        return np.nan, np.nan, 0
    X = np.c_[pts, np.ones(len(pts))]
    ok = np.ones(len(pts), bool)
    for _ in range(3):
        cx, *_ = np.linalg.lstsq(X[ok], vec[ok, 0], rcond=None); cy, *_ = np.linalg.lstsq(X[ok], vec[ok, 1], rcond=None)
        r = np.hypot(vec[:, 0] - X @ cx, vec[:, 1] - X @ cy)
        lim = max(0.25, np.percentile(r[ok], 75) * 2.0)
        ok = r < lim
    # cisalhamento: dx dependendo de y além do afim → ajusta termo quadrático em y nos inliers
    Xq = np.c_[X, (pts[:, 1] / H) ** 2]
    cq, *_ = np.linalg.lstsq(Xq[ok], vec[ok, 0], rcond=None)
    return float(r[ok].mean()), float(abs(cq[3])), int(ok.sum())


def analisar(p, ss, t, vf=""):
    f = frames(p, ss, t, vf)
    res, cis = [], []
    for i in range(len(f) - 1):
        r, c, n = residuo(*campo(f[i], f[i + 1]))
        res.append(r); cis.append(c)
    res, cis = np.array(res), np.array(cis)
    return {"residuo_medio": float(np.nanmean(res)), "residuo_p95": float(np.nanpercentile(res, 95)),
            "curvatura_media": float(np.nanmean(cis)), "por_quadro": res.round(3).tolist()}
