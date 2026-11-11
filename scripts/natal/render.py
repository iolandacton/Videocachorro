#!/usr/bin/env python3
"""Iluminação natalina externa da Casa Tambaba — render 100% local (sem créditos).

A foto aérea original é a única fonte de imagem: a casa, os carros, a
vegetação e o terreno não são redesenhados. A noite é obtida regradando
a própria foto, e cada luz ilumina os pixels reais ao redor dela
(pixel_final = foto * (luz_ambiente + luz_das_lâmpadas) + brilho_das_lâmpadas).

Uso:
  python3 scripts/natal/render.py preview [--width 3840] [--out out/natal/previa.png]
  python3 scripts/natal/render.py debug   # foto diurna com as luzes marcadas
"""
from __future__ import annotations

import argparse
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "public", "originais", "casa_tambaba_aerea.jpg")

# Recorte 16:9 da foto (descarta a faixa preta inferior)
CROP_X, CROP_Y, CROP_W, CROP_H = 2, 0, 1316, 740

# Luz ambiente (multiplicador linear sobre a foto)
NIGHT_AMBIENT = np.array([0.050, 0.068, 0.110], np.float32)   # luar azulado
DUSK_AMBIENT = np.array([0.34, 0.30, 0.36], np.float32)       # anoitecer
DAY_AMBIENT = np.array([1.0, 1.0, 1.0], np.float32)

# kind -> (raio do núcleo, ganho do núcleo, [(sigma do reflexo, ganho)...]) em px da foto
KINDS = {
    "micro":   dict(core=0.42, emit=2.6, spill=[(3.0, 0.55), (8.0, 0.10)]),
    "bulb":    dict(core=0.55, emit=3.4, spill=[(4.0, 0.70), (11.0, 0.13)]),
    "lantern": dict(core=0.75, emit=4.2, spill=[(5.5, 1.25), (15.0, 0.30)]),
    "wash":    dict(core=0.0,  emit=0.0, spill=[(17.0, 0.95)]),
}
BLOOM = [(2.6, 0.085), (9.0, 0.014)]   # halos do brilho (sigma px da foto, ganho)


def srgb_to_lin(u8):
    x = u8.astype(np.float32) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def tonemap(x, white=3.5):
    return x * (1 + x / (white * white)) / (1 + x)


def blur(img, sigma):
    if sigma < 0.3:
        return img
    return cv2.GaussianBlur(img, (0, 0), sigma, borderType=cv2.BORDER_REPLICATE)


def splat(buf, x, y, rgb):
    """Deposita um ponto com interpolação bilinear."""
    h, w = buf.shape[:2]
    x0, y0 = int(np.floor(x)), int(np.floor(y))
    fx, fy = x - x0, y - y0
    for dx, dy, wt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                       (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
        xx, yy = x0 + dx, y0 + dy
        if 0 <= xx < w and 0 <= yy < h:
            buf[yy, xx] += np.asarray(rgb, np.float32) * wt


class Scene:
    def __init__(self, width=3840, seed=7):
        self.W = width
        self.H = round(width * 9 / 16)
        self.s = self.W / CROP_W                      # px de saída por px da foto
        src = cv2.imread(SRC)
        assert src is not None, SRC
        self.src = src
        crop = src[CROP_Y:CROP_Y + CROP_H, CROP_X:CROP_X + CROP_W]
        up = cv2.resize(crop, (self.W, self.H), interpolation=cv2.INTER_LANCZOS4)
        if self.s > 1.5:                              # nitidez leve após ampliar
            soft = cv2.GaussianBlur(up, (0, 0), self.s * 0.55)
            up = cv2.addWeighted(up, 1.2, soft, -0.2, 0)
        self.day = srgb_to_lin(up[:, :, ::-1])        # RGB linear
        lum = self.day @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        self.day_desat = self.day * 0.6 + lum[..., None] * 0.4
        self.lights = layout.build(seed)
        self._snap_to_vegetation()
        self._build_layers()

    # -- geometria ------------------------------------------------------
    def to_out(self, x, y):
        return (x - CROP_X + 0.5) * self.s - 0.5, (y - CROP_Y + 0.5) * self.s - 0.5

    def _snap_to_vegetation(self):
        """Move micro LEDs marcados para o pixel de folhagem mais próximo."""
        b, g, r = [self.src[:, :, i].astype(np.int32) for i in range(3)]
        veg = ((g > r + 4) & (g > b + 10) & (g > 45)).astype(np.float32)
        score = cv2.GaussianBlur(veg, (0, 0), 1.0) + 0.002 * g
        h, w = veg.shape
        for lt in self.lights:
            if not lt.snap:
                continue
            xi, yi = int(round(lt.x)), int(round(lt.y))
            best, bx, by = -1.0, xi, yi
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    xx, yy = xi + dx, yi + dy
                    if 0 <= xx < w and 0 <= yy < h:
                        sc = score[yy, xx] - 0.03 * (dx * dx + dy * dy)
                        if sc > best:
                            best, bx, by = sc, xx, yy
            lt.x, lt.y = float(bx), float(by)

    def _roof_mask(self):
        m = np.zeros((self.H, self.W), np.float32)
        for poly in (layout.ROOF, layout.TANK):
            pts = np.array([self.to_out(x, y) for x, y in poly], np.float32)
            cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1.0)
        return blur(m, self.s * 1.2)

    # -- camadas de luz por grupo ----------------------------------------
    def _build_layers(self):
        n = len(layout.GROUP_NAMES)
        ds = 2 if self.W >= 2560 else 1                # reflexo em meia resolução
        w2, h2 = self.W // ds, self.H // ds
        s2 = self.s / ds
        keep = 1.0 - 0.96 * self._roof_mask()[..., None]
        self.spill, self.emit = [], []
        for g in range(n):
            spill = np.zeros((h2, w2, 3), np.float32)
            emit = np.zeros((self.H, self.W, 3), np.float32)
            for kind, k in KINDS.items():
                pts = [lt for lt in self.lights if lt.group == g and lt.kind == kind]
                if not pts:
                    continue
                imp = np.zeros((h2, w2, 3), np.float32)
                for lt in pts:
                    x, y = self.to_out(lt.x, lt.y)
                    splat(imp, (x + 0.5) / ds - 0.5, (y + 0.5) / ds - 0.5,
                          np.array(lt.color) * lt.gain)
                for sigma, gain in k["spill"]:
                    sg = sigma * s2
                    spill += blur(imp, sg) * (2 * np.pi * sg * sg * gain)
                if k["emit"] > 0:
                    impf = np.zeros((self.H, self.W, 3), np.float32)
                    for lt in pts:
                        x, y = self.to_out(lt.x, lt.y)
                        splat(impf, x, y, np.array(lt.color) * lt.gain)
                    sc = max(0.6, k["core"] * self.s)
                    core = blur(impf, sc) * (2 * np.pi * sc * sc * k["emit"])
                    emit += core
            if ds > 1:
                spill = cv2.resize(spill, (self.W, self.H), interpolation=cv2.INTER_LINEAR)
            glow = np.zeros_like(emit)
            for sigma, gain in BLOOM:
                glow += blur(emit, sigma * self.s) * (gain * (sigma * self.s) ** 2 /
                                                      max(0.36, (0.5 * self.s) ** 2))
            self.spill.append((spill * keep).astype(np.float16))
            self.emit.append(((emit + glow * 0.02) * keep).astype(np.float16))

    # -- composição -------------------------------------------------------
    def frame(self, ambient=NIGHT_AMBIENT, levels=None, desat=1.0, exposure=1.0):
        n = len(layout.GROUP_NAMES)
        levels = [1.0] * n if levels is None else levels
        base = self.day * (1 - desat) + self.day_desat * desat
        out = base * ambient
        illum = np.zeros_like(self.day)
        emit = np.zeros_like(self.day)
        for g in range(n):
            if levels[g] <= 0:
                continue
            illum += self.spill[g].astype(np.float32) * levels[g]
            emit += self.emit[g].astype(np.float32) * levels[g]
        out = out + self.day * illum + emit
        return out * exposure

    def finish(self, lin, night=1.0, seed=0):
        """Tone mapping, vinheta e grão -> BGR uint8."""
        img = tonemap(lin) * night + np.clip(lin, 0, 1) * (1 - night)
        yy, xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)
        r2 = ((xx / self.W - 0.5) ** 2 + (yy / self.H - 0.5) ** 2) / 0.5
        img = img * (1 - 0.22 * night * r2 ** 1.3)[..., None]
        out = lin_to_srgb(img)
        if night > 0:
            rng = np.random.default_rng(seed)
            out = out + rng.normal(0, 0.006 * night, out.shape[:2]).astype(np.float32)[..., None]
        return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)[:, :, ::-1]


def cmd_preview(a):
    sc = Scene(a.width)
    img = sc.finish(sc.frame())
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    cv2.imwrite(a.out, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print("ok", a.out, img.shape, "luzes:", len(sc.lights))


def cmd_debug(a):
    sc = Scene(a.width)
    img = (lin_to_srgb(sc.day)[:, :, ::-1] * 255).astype(np.uint8).copy()
    cols = [(0, 255, 255), (0, 165, 255), (0, 255, 0), (255, 255, 0),
            (255, 0, 255), (255, 255, 255), (255, 128, 128)]
    for lt in sc.lights:
        x, y = sc.to_out(lt.x, lt.y)
        r = {"micro": 2, "bulb": 3, "lantern": 5, "wash": 9}[lt.kind]
        cv2.circle(img, (int(x), int(y)), r, cols[lt.group], 1 if lt.kind == "wash" else -1)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    cv2.imwrite(a.out, img)
    print("ok", a.out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["preview", "debug"])
    ap.add_argument("--width", type=int, default=3840)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.out is None:
        a.out = os.path.join(ROOT, "out", "natal",
                             "previa_noturna.jpg" if a.cmd == "preview" else "debug_luzes.png")
    {"preview": cmd_preview, "debug": cmd_debug}[a.cmd](a)
