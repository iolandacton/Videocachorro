"""Kit de decoração natalina para fotos (render local, sem créditos).

Só quatro itens, todos em LED branco-quente:
  - pisca-pisca (cordão de micro LEDs)
  - chuva de meteoros (tubos pendurados na árvore)
  - cascata (fios pendentes no beiral)
  - rena de mangueira luminosa

Os itens são pintados sobre a foto diurna como objetos reais; depois a
foto inteira é regradada para a noite e cada LED ilumina os pixels reais
ao redor dele:

    noite = foto * (luz_ambiente + luz_dos_LEDs) + brilho_dos_LEDs

Assim a casa, as plantas e o terreno não são redesenhados.
"""
from __future__ import annotations

import math
import random

import cv2
import numpy as np

WARM = (1.00, 0.66, 0.34)      # branco-quente (linear RGB)
P_WIRE = (26, 46, 30)          # fio verde-escuro do pisca-pisca (sRGB)
P_TUBE = (226, 222, 210)       # tubo/mangueira translúcidos apagados

KINDS = {  # núcleo (sigma px), brilho, reflexos [(sigma, ganho)]
    "micro": dict(core=1.5, emit=3.0, spill=[(9, 0.55), (26, 0.07)]),
    "bulb":  dict(core=3.0, emit=3.4, spill=[(20, 0.80), (58, 0.15)]),
}
SPILL_DS = 4


def srgb_to_lin(u8):
    x = u8.astype(np.float32) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * x ** (1 / 2.4) - 0.055)


def tonemap(x, white=3.5):
    return x * (1 + x / (white * white)) / (1 + x)


def along(pts, step, start=0.0):
    """Pontos igualmente espaçados em uma polilinha: (x, y, dx, dy)."""
    out, carry = [], start
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        if seg == 0:
            continue
        d = carry
        while d < seg:
            t = d / seg
            out.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t,
                        (x1 - x0) / seg, (y1 - y0) / seg))
            d += step
        carry = d - seg
    return out


def chaikin(pts, n=2, closed=False):
    """Suaviza uma polilinha."""
    pts = [tuple(map(float, p)) for p in pts]
    for _ in range(n):
        src = pts + [pts[0]] if closed else pts
        out = [] if closed else [src[0]]
        for (x0, y0), (x1, y1) in zip(src, src[1:]):
            out.append((0.75 * x0 + 0.25 * x1, 0.75 * y0 + 0.25 * y1))
            out.append((0.25 * x0 + 0.75 * x1, 0.25 * y0 + 0.75 * y1))
        if not closed:
            out.append(src[-1])
        pts = out
    return pts + [pts[0]] if closed else pts


def curve(p0, p1, bow=0.0, n=12):
    """Curva suave de p0 a p1, arqueada lateralmente por `bow` (fração)."""
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2 - (y1 - y0) * bow, (y0 + y1) / 2 + (x1 - x0) * bow
    return [((1 - t) ** 2 * x0 + 2 * t * (1 - t) * mx + t * t * x1,
             (1 - t) ** 2 * y0 + 2 * t * (1 - t) * my + t * t * y1)
            for t in (i / n for i in range(n + 1))]


def _bgr(rgb, k=1.0):
    return tuple(int(max(0, min(255, c * k))) for c in rgb[::-1])


def _splat(buf, x, y, sx, sy, rgb):
    """Soma uma gaussiana elíptica de pico `rgb` em buf (HxWx3)."""
    h, w = buf.shape[:2]
    rx, ry = int(3.2 * sx) + 1, int(3.2 * sy) + 1
    x0, x1 = max(0, int(x) - rx), min(w, int(x) + rx + 2)
    y0, y1 = max(0, int(y) - ry), min(h, int(y) + ry + 2)
    if x0 >= x1 or y0 >= y1:
        return
    gx = np.exp(-((np.arange(x0, x1) - x) ** 2) / (2 * sx * sx)).astype(np.float32)
    gy = np.exp(-((np.arange(y0, y1) - y) ** 2) / (2 * sy * sy)).astype(np.float32)
    buf[y0:y1, x0:x1] += (gy[:, None] * gx[None, :])[..., None] * np.asarray(rgb, np.float32)


# Rena de mangueira luminosa, de perfil, olhando para a esquerda.
# Unidades arbitrárias: x 0..100, y -6 (ponta da galhada) .. 118 (cascos).
RENA_CLOSED = [[(8, 30), (20, 21), (27, 19), (31, 22), (38, 38), (44, 47), (60, 46),
                (76, 47), (86, 52), (88, 57), (87, 68), (90, 84), (86, 96), (87, 118),
                (82, 118), (81, 97), (80, 86), (74, 75), (62, 72), (46, 72), (45, 90),
                (44, 118), (39, 118), (39, 92), (37, 72), (33, 62), (29, 45), (23, 33),
                (12, 35)]]
RENA_OPEN = [
    [(39, 71), (31, 90), (26, 104), (25, 118), (30, 118), (31, 105), (36, 92), (44, 74)],
    [(70, 73), (72, 88), (68, 100), (69, 118), (74, 118), (74, 100), (78, 88), (77, 76)],
    [(50, 47), (53, 60), (50, 72)], [(62, 46), (65, 59), (62, 72)],
    [(74, 47), (77, 60), (74, 74)],
    [(28, 20), (34, 13), (32, 22)],                                   # orelha
    [(25, 19), (24, 10), (19, 3), (18, -6)], [(24, 10), (29, 4), (28, -3)],
    [(21, 5), (15, 2)],                                               # galhada 1
    [(29, 19), (33, 9), (39, 4), (44, -4)], [(33, 9), (38, 11), (43, 9)],
    [(39, 4), (38, -3)],                                              # galhada 2
    [(88, 55), (93, 52), (91, 58)],                                   # rabo
]
RENA_H = 124.0


class Deco:
    def __init__(self, path, sky_polys=(), far_polys=(), seed=11,
                 ambient=(0.088, 0.112, 0.176), sky_tint=(0.040, 0.064, 0.135),
                 sky_gain=1.0, far_gain=0.6):
        self.rng = random.Random(seed)
        self.src = cv2.imread(path)
        assert self.src is not None, path
        self.paint = self.src.copy()            # foto diurna + itens pintados
        self.H, self.W = self.src.shape[:2]
        self.ambient = np.array(ambient, np.float32)
        self.sky_tint = np.array(sky_tint, np.float32)
        self.sky_gain = sky_gain
        self.far_gain = far_gain
        self.lights = []                         # (x, y, rgb, kind, gain, scale)
        self.washes = []                         # (x, y, sx, sy, rgb, alvo)
        self.glows = []                          # (x, y, sx, sy, rgb): só brilho
        self._masks(sky_polys, far_polys)

    # ------------------------------------------------------------------ máscaras
    def _masks(self, sky_polys, far_polys):
        b, g, r = [self.src[:, :, i].astype(np.int32) for i in range(3)]
        mx = np.maximum(np.maximum(r, g), b)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        region = np.zeros((self.H, self.W), np.uint8)
        for poly in sky_polys:
            cv2.fillPoly(region, [np.array(poly, np.int32)], 1)
        sky = (region > 0) & (((b >= g - 8) & (b >= r - 10) & (lum > 78))
                              | ((b > r + 30) & (b > g + 10)))   # nuvens | azul
        sky = cv2.medianBlur(sky.astype(np.uint8) * 255, 5)
        self.sky = cv2.GaussianBlur(sky.astype(np.float32) / 255.0, (0, 0), 1.4)
        veg = (g >= r - 3) & (g >= b + 8) & (mx > 28)
        self.veg = cv2.GaussianBlur(veg.astype(np.float32), (0, 0), 2.0)
        # fundo distante (campo/rua além da cerca): não recebe luz dos LEDs,
        # exceto onde há folhagem do jardim na frente dele
        far = np.zeros((self.H, self.W), np.float32)
        for poly in far_polys:
            cv2.fillPoly(far, [np.array(poly, np.int32)], 1.0)
        self.far = cv2.GaussianBlur(far, (0, 0), 3.0) * (1 - self.sky) * (1 - self.veg)

    # ------------------------------------------------------------------ primitivas
    def light(self, x, y, color=WARM, kind="micro", gain=1.0, scale=1.0):
        self.lights.append((float(x), float(y), color, kind, gain, scale))

    def wash(self, x, y, sx, sy=None, color=WARM, gain=1.0, target="all"):
        """Luz difusa: alvo = all | veg (só folhagem) | ground."""
        self.washes.append((x, y, sx, sy or sx, tuple(c * gain for c in color), target))

    def wire(self, pts, color=P_WIRE, thick=1):
        p = np.round(np.array(pts, np.float32) * 16).astype(np.int32)
        cv2.polylines(self.paint, [p], False, _bgr(color), thick, cv2.LINE_AA, 4)

    def _emit_line(self, pts, sigma, peak, color=WARM, step=1.5):
        amp = peak * step / (sigma * 2.5066)
        c = np.array(color, np.float32) * amp
        for x, y, _, _ in along(pts, step):
            self.glows.append((x, y, sigma, sigma, c))

    # ------------------------------------------------------------------ pisca-pisca
    def pisca(self, pts, step=14.0, scale=1.0, gain=1.0, jitter=1.0, wire=True):
        """Cordão de pisca-pisca acompanhando uma polilinha."""
        if wire:
            self.wire(pts, thick=max(1, int(round(1.3 * scale))))
        for x, y, dx, dy in along(pts, step * scale, step * scale * 0.5):
            j = self.rng.uniform(-jitter, jitter) * scale
            self.light(x - dy * j * 2, y + dx * j * 2, WARM, "micro",
                       gain * self.rng.uniform(0.85, 1.15), scale)

    def wrap(self, p0, p1, w0, w1, pitch, scale=1.0, gain=1.0, led=11.0):
        """Pisca-pisca enrolado em espiral em tronco/pilar (meia-volta visível)."""
        (x0, y0), (x1, y1) = p0, p1
        length = math.hypot(x1 - x0, y1 - y0)
        ux, uy = (x1 - x0) / length, (y1 - y0) / length
        nx, ny = -uy, ux
        for k in range(max(1, int(length / pitch))):
            pts = []
            for j in range(13):
                th = math.pi * j / 12
                s = (k + th / (2 * math.pi)) * pitch
                if s > length:
                    break
                w = w0 + (w1 - w0) * s / length
                pts.append((x0 + ux * s + nx * math.cos(th) * w / 2,
                            y0 + uy * s + ny * math.cos(th) * w / 2))
            if len(pts) < 2:
                continue
            self.wire(pts, thick=max(1, int(round(1.3 * scale))))
            for x, y, _, _ in along(pts, led * scale, led * scale * 0.5):
                self.light(x, y, WARM, "micro", gain * self.rng.uniform(0.85, 1.15), scale)

    def stems(self, base, tips, bow=0.06, **kw):
        """Pisca-pisca subindo pelos talos de uma palmeira-leque."""
        for i, tip in enumerate(tips):
            side = 1 if tip[0] < base[0] else -1
            self.pisca(curve(base, tip, bow * side), **kw)

    # ------------------------------------------------------------------ chuva de meteoros
    def meteor(self, x, y, length, scale=1.0, phase=None, hang=18):
        """Tubo de 'chuva de meteoros' pendurado em (x, y)."""
        phase = self.rng.random() if phase is None else phase
        t = max(2, int(round(5 * scale)))
        cv2.line(self.paint, (int(x), int(y - hang * scale)), (int(x), int(y)),
                 _bgr((40, 40, 40)), 1, cv2.LINE_AA)
        cv2.line(self.paint, (int(x), int(y)), (int(x), int(y + length)), _bgr(P_TUBE),
                 t, cv2.LINE_AA)
        head = 0.25 + 0.7 * phase            # posição da "gota" (0 topo .. 1 base)
        step = 1.5
        n = int(length / step)
        for i in range(n + 1):
            u = i / n
            d = head - u
            drop = math.exp(-d / 0.38) if d >= 0 else math.exp(d / 0.05)
            inten = 0.35 + 2.6 * drop
            taper = min(1.0, u / 0.08, (1 - u) / 0.05) ** 0.7
            sg = (1.2 + 1.5 * drop) * scale
            amp = inten * taper * step / (sg * 2.5066) * 1.9
            self.glows.append((x, y + u * length, sg, sg, np.array(WARM, np.float32) * amp))
        for u in (0.2, 0.5, 0.8):
            self.wash(x, y + u * length, 30 * scale, 34 * scale, WARM, 0.5, "all")

    # ------------------------------------------------------------------ cascata
    def cascata(self, p0, p1, s0=1.0, s1=1.0, spacing=36.0, led=21.0,
                lengths=(52, 100, 74, 124, 62, 108), gain=1.0, skip=(), glow=0.11):
        """Cascata de LED pendurada ao longo do beiral p0 -> p1.

        s0/s1: escala no início e no fim (perspectiva).
        skip: faixas (x0, x1) encobertas por pilares à frente do beiral."""
        (x0, y0), (x1, y1) = p0, p1
        total = math.hypot(x1 - x0, y1 - y0)
        self.wire([p0, p1], (205, 205, 200), 1)
        for t in np.arange(0.0, 1.001, 260.0 / max(260.0, total)):   # clarão suave
            s = s0 + (s1 - s0) * t
            self.wash(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + 170 * s, 300 * s, 360 * s,
                      WARM, glow, "all")
        d, i = spacing * s0 * 0.5, 0
        while d < total:
            t = d / total
            s = s0 + (s1 - s0) * t
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            ln = lengths[i % len(lengths)] * s
            if any(a <= x <= b for a, b in skip):
                d += spacing * s
                i += 1
                continue
            cv2.line(self.paint, (int(x), int(y)), (int(x), int(y + ln)),
                     _bgr((205, 205, 200)), 1, cv2.LINE_AA)
            yy = y + led * s * 0.35
            while yy <= y + ln + 0.5:
                self.light(x + self.rng.uniform(-0.6, 0.6) * s, yy, WARM, "micro",
                           gain * self.rng.uniform(0.85, 1.15), 0.95 * s)
                yy += led * s
            d += spacing * s
            i += 1

    # ------------------------------------------------------------------ rena
    def rena(self, x, y, h, flip=False, gain=1.0):
        """Rena de mangueira luminosa; (x, y) = centro dos cascos, h = altura."""
        k = h / RENA_H
        sgn = -1 if flip else 1

        def tr(p):
            return (x + sgn * (p[0] - 57) * k, y + (p[1] - 118) * k)

        paths = [chaikin([tr(p) for p in pl], 2, closed=True) for pl in RENA_CLOSED]
        paths += [chaikin([tr(p) for p in pl], 2) for pl in RENA_OPEN]
        tube = max(1.3, h * 0.0075)
        for pl in paths:
            self.wire(pl, P_TUBE, max(2, int(round(tube * 1.7))))
            self._emit_line(pl, tube, 1.15 * gain)
            for px, py, _, _ in along(pl, max(5.0, h * 0.032), h * 0.012):
                self.glows.append((px, py, tube * 0.8, tube * 0.8,
                                   np.array(WARM, np.float32) * 2.0 * gain))
        self.wash(x, y - h * 0.42, h * 0.42, h * 0.40, WARM, 0.30 * gain, "all")
        self.wash(x, y + h * 0.015, h * 0.62, h * 0.085, WARM, 1.0 * gain, "ground")

    # ------------------------------------------------------------------ render
    def render(self, exposure=1.0, vignette=0.20, grain=0.006):
        H, W = self.H, self.W
        lumw = np.array([0.2126, 0.7152, 0.0722], np.float32)
        day0 = srgb_to_lin(self.src[:, :, ::-1])
        day = srgb_to_lin(self.paint[:, :, ::-1])
        desat = day * 0.6 + (day @ lumw)[..., None] * 0.4
        sky = self.sky[..., None]
        far = self.far[..., None]

        # ambiente: chão ao luar + céu de anoitecer
        yy = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        sky_col = self.sky_tint * self.sky_gain * (0.30 + 1.25 * (day0 @ lumw)[..., None]) \
            * (0.75 + 0.6 * yy)
        ground = desat * self.ambient * (1 - (1 - self.far_gain) * far)
        out = ground * (1 - sky) + sky_col * sky

        # reflexos dos LEDs (1/4 da resolução)
        ds = SPILL_DS
        h2, w2 = H // ds + 1, W // ds + 1
        sp = {k: np.zeros((h2, w2, 3), np.float32) for k in ("all", "veg", "ground")}
        emit = np.zeros((H, W, 3), np.float32)
        for x, y, color, kind, gain, sc in self.lights:
            k = KINDS[kind]
            c = np.array(color, np.float32) * gain
            for sg, g in k["spill"]:
                s = max(0.8, sg * sc / ds)
                _splat(sp["all"], x / ds, y / ds, s, s, c * g)
            sg = max(0.7, k["core"] * sc)
            _splat(emit, x, y, sg, sg, c * k["emit"])
            _splat(emit, x, y, sg * 2.3, sg * 2.3, c * k["emit"] * 0.22)
        for x, y, sx, sy, c in self.glows:
            _splat(emit, x, y, sx, sy, c)
        for x, y, sx, sy, c, target in self.washes:
            _splat(sp[target], x / ds, y / ds, max(0.8, sx / ds), max(0.8, sy / ds), c)
        up = lambda b: cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
        near = (1 - sky) * (1 - 0.9 * far)
        illum = (up(sp["all"]) + up(sp["veg"]) * self.veg[..., None] + up(sp["ground"])) * near
        out += day * illum

        # halo
        small = cv2.resize(emit, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
        halo = cv2.GaussianBlur(small, (0, 0), 2.2) * 0.55 \
            + cv2.GaussianBlur(small, (0, 0), 9) * 0.38
        out += emit + up(halo)

        img = tonemap(out * exposure)
        yv, xv = np.mgrid[0:H, 0:W].astype(np.float32)
        r2 = ((xv / W - 0.5) ** 2 + (yv / H - 0.5) ** 2) / 0.5
        img *= (1 - vignette * r2 ** 1.3)[..., None]
        res = lin_to_srgb(img)
        if grain:
            rng = np.random.default_rng(1)
            res = res + rng.normal(0, grain, (H, W)).astype(np.float32)[..., None]
        return (np.clip(res, 0, 1) * 255 + 0.5).astype(np.uint8)[:, :, ::-1]
