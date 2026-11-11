#!/usr/bin/env python3
"""Fotos da Casa Tambaba com decoração natalina simples (render local, sem créditos).

Itens usados: pisca-pisca, chuva de meteoros, cascata e rena de LED,
todos em branco-quente. Coordenadas em pixels de cada foto original.

Uso: python3 scripts/natal/fotos.py [1 2 3 4 5 6] [--debug]
Saída: out/natal/fotos/fotoN_natal.jpg
"""
from __future__ import annotations

import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deco import Deco  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "public", "originais", "tambaba")
OUT = os.path.join(ROOT, "out", "natal", "fotos")


def src(n):
    return os.path.join(SRC, f"foto{n}.jpg")


def meteors(d, poly, n, length, scale, min_d):
    """Pendura n tubos de meteoro em pontos de folhagem dentro do polígono."""
    pts = np.array(poly, np.float32)
    (x0, y0), (x1, y1) = pts.min(0), pts.max(0)
    acc = []
    for _ in range(20000):
        if len(acc) >= n:
            break
        x, y = d.rng.uniform(x0, x1), d.rng.uniform(y0, y1)
        if cv2.pointPolygonTest(pts, (x, y), False) < 0 or d.veg[int(y), int(x)] < 0.6:
            continue
        if any(abs(x - a) < min_d * 0.55 and abs(y - b) < length * 1.1 or
               (x - a) ** 2 + (y - b) ** 2 < min_d ** 2 for a, b in acc):
            continue
        acc.append((x, y))
    for x, y in acc:
        d.meteor(x, y, length * d.rng.uniform(0.8, 1.15), scale)


def foto1():
    d = Deco(src(1), sky_polys=[[(0, 0), (1932, 0), (1932, 1330), (0, 1330)]])
    # árvore: troncos com pisca-pisca + chuva de meteoros na copa
    d.wrap((945, 1410), (925, 1312), 17, 15, 19, 0.75)
    d.wrap((923, 1308), (850, 1215), 10, 8, 18, 0.7)
    d.wrap((850, 1215), (815, 1160), 8, 6, 18, 0.7)
    d.wrap((935, 1300), (945, 1205), 9, 7, 18, 0.7)
    d.wrap((1052, 1395), (1067, 1300), 15, 13, 19, 0.75)
    d.wrap((1066, 1296), (1045, 1190), 9, 7, 18, 0.7)
    d.wrap((1085, 1408), (1110, 1292), 11, 9, 18, 0.7)
    meteors(d, [(520, 1100), (570, 880), (780, 800), (960, 745), (1140, 790), (1230, 860),
                (1250, 1020), (1440, 1110), (1400, 1180), (1150, 1240), (800, 1240),
                (620, 1200)], 20, 120, 0.75, 85)
    # rena no gramado
    d.rena(1560, 2130, 340)
    return d


def foto2():
    d = Deco(src(2), sky_polys=[[(0, 0), (1932, 0), (1932, 1440), (0, 1440)]])
    d.wrap((925, 1500), (882, 1320), 24, 20, 26)
    d.wrap((880, 1316), (790, 1170), 14, 10, 24)
    d.wrap((790, 1170), (735, 1100), 10, 8, 24)
    d.wrap((884, 1300), (906, 1215), 12, 9, 24)
    d.wrap((1062, 1468), (1084, 1300), 22, 18, 26)
    d.wrap((1080, 1296), (1052, 1160), 12, 9, 24)
    d.wrap((1112, 1455), (1146, 1340), 16, 13, 26)
    d.wrap((1147, 1335), (1132, 1150), 11, 8, 24)
    meteors(d, [(330, 1000), (380, 720), (700, 580), (960, 520), (1200, 580), (1330, 720),
                (1370, 960), (1600, 1060), (1560, 1180), (1200, 1250), (700, 1250),
                (400, 1150)], 22, 170, 1.0, 120)
    d.rena(1720, 2400, 450)
    return d


def foto3():
    d = Deco(src(3), sky_polys=[[(0, 600), (2576, 640), (2576, 960), (0, 960)]],
             far_polys=[[(0, 935), (2576, 935), (2576, 1115), (2000, 1130), (1650, 1180),
                         (1160, 1215), (980, 1215), (0, 1245)]])
    d.cascata((0, 628), (2576, 666), 1.0, 1.0, skip=[(1240, 1304)])   # beiral
    d.wrap((1272, 660), (1272, 1225), 56, 56, 62, 1.1)         # pilar
    kw = dict(step=15, scale=0.85)
    d.stems((693, 1335), [(575, 1050), (628, 940), (682, 905), (762, 930), (845, 940),
                          (858, 1005)], **kw)
    d.stems((1533, 1275), [(1385, 1000), (1405, 875), (1472, 925), (1565, 1030),
                           (1650, 900), (1705, 860), (1735, 950)], **kw)
    d.stems((2150, 1238), [(2090, 1010), (2125, 1000), (2160, 1000), (2195, 1010)], **kw)
    # portão e cerca
    g = dict(step=13, scale=0.7)
    d.pisca([(992, 1185), (992, 1025)], **g)
    d.pisca([(1000, 1040), (1150, 1040)], **g)
    d.pisca([(1157, 995), (1157, 1185)], **g)
    f = dict(step=14, scale=0.62)
    d.pisca([(0, 1088), (370, 1068)], **f)
    d.pisca([(900, 1037), (985, 1032)], **f)
    d.pisca([(1165, 1035), (1290, 1040)], **f)
    d.pisca([(1700, 1056), (1960, 1076)], **f)
    d.rena(290, 1345, 215, flip=True)
    return d


def foto4():
    d = Deco(src(4), sky_polys=[[(400, 829), (2576, 417), (2576, 905), (330, 905), (330, 850)]],
             far_polys=[[(330, 890), (2576, 885), (2576, 1170), (1990, 1165), (1760, 1160),
                         (1430, 1138), (990, 1112), (330, 1085)]])
    d.cascata((410, 829), (2366, 459), 0.6, 1.75, skip=[(808, 872)])
    d.cascata((2486, 436), (2576, 419), 1.8, 1.85)
    d.wrap((2427, 480), (2427, 1780), 106, 106, 135, 1.7)      # pilares
    d.wrap((840, 730), (840, 1205), 55, 55, 52, 0.9)
    d.wrap((366, 845), (366, 1150), 36, 36, 36, 0.65)
    kw = dict(step=15, scale=0.85)
    d.stems((1531, 1252), [(1425, 1000), (1462, 890), (1520, 845), (1588, 805), (1650, 800),
                           (1695, 850), (1705, 930)], **kw)
    kw = dict(step=13, scale=0.7)
    d.stems((885, 1178), [(880, 960), (905, 940), (930, 930), (955, 940), (985, 960)], **kw)
    d.stems((592, 1134), [(560, 1000), (590, 985), (620, 985), (655, 1000)], step=13, scale=0.6)
    g = dict(step=13, scale=0.75)
    d.pisca([(1765, 1158), (1765, 992)], **g)
    d.pisca([(1775, 998), (1955, 994)], **g)
    d.pisca([(1967, 987), (1967, 1158)], **g)
    d.pisca([(1020, 1004), (1370, 1004)], 14, 0.62)
    d.rena(1200, 1208, 180, flip=True)
    return d


def foto5():
    d = Deco(src(5), sky_polys=[[(0, 776), (700, 826), (700, 900), (0, 900)],
                                [(1000, 760), (2576, 425), (2576, 560), (2000, 640),
                                 (1300, 760)]])
    d.cascata((0, 778), (790, 824), 0.7, 0.9, skip=[(490, 520)])   # beiral da área gourmet
    d.cascata((862, 810), (2576, 427), 0.9, 1.8)
    d.pisca([(1985, 772), (2576, 712)], 15, 1.0)               # viga do pergolado
    d.wrap((826, 660), (826, 940), 52, 52, 78, 1.3)            # pilares
    d.wrap((505, 835), (505, 1170), 22, 22, 40, 0.8)
    d.wrap((2058, 800), (2058, 1280), 52, 52, 66, 1.1)
    t = dict(pitch=22, scale=0.6, led=9)                       # troncos das palmeiras
    d.wrap((1100, 1210), (1095, 1000), 9, 9, **t)
    d.wrap((1140, 1210), (1150, 920), 9, 8, **t)
    d.wrap((1152, 1118), (1173, 938), 8, 8, **t)
    d.wrap((1342, 1063), (1342, 982), 8, 8, **t)
    d.wrap((1487, 1128), (1484, 996), 9, 9, **t)
    d.wrap((1504, 1130), (1523, 982), 8, 8, **t)
    d.pisca([(880, 1090), (960, 1083), (1050, 1088)], 14, 0.7)  # cerca viva
    d.pisca([(300, 1108), (420, 1100), (530, 1098)], 14, 0.7)
    d.rena(1830, 1690, 360)
    return d


def foto6():
    d = Deco(src(6), sky_polys=[[(0, 690), (2300, 930), (2300, 1012), (0, 1012)]],
             far_polys=[[(0, 1000), (2300, 1000), (2300, 1100), (1700, 1180), (1500, 1215),
                         (1300, 1235), (950, 1272), (500, 1350), (0, 1415)]])
    d.cascata((0, 698), (2297, 928), 1.5, 0.5,
              skip=[(732, 796), (1755, 1797), (2142, 2178)])
    d.wrap((764, 800), (764, 1450), 57, 57, 105, 1.8)
    d.wrap((1776, 890), (1776, 1265), 38, 38, 44, 0.72)
    d.wrap((2160, 930), (2160, 1208), 34, 34, 36, 0.55)
    d.stems((1101, 1392), [(960, 1105), (1010, 1020), (1040, 935), (1112, 945), (1175, 1020),
                           (1215, 1065)], step=13, scale=1.0)
    d.stems((1642, 1265), [(1575, 1065), (1610, 1040), (1645, 1030), (1685, 1045),
                           (1720, 1070)], step=13, scale=0.65)
    d.stems((1926, 1157), [(1890, 1065), (1915, 1050), (1945, 1050), (1975, 1065)],
            step=13, scale=0.5)
    d.pisca([(215, 1203), (540, 1183), (730, 1171)], 14, 0.7)
    d.pisca([(800, 1166), (878, 1160), (960, 1152)], 14, 0.7)
    d.rena(300, 1545, 270, flip=True)
    return d


FOTOS = {1: foto1, 2: foto2, 3: foto3, 4: foto4, 5: foto5, 6: foto6}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    os.makedirs(OUT, exist_ok=True)
    for n in [int(a) for a in args] or sorted(FOTOS):
        d = FOTOS[n]()
        if "--debug" in sys.argv:           # foto diurna com os itens marcados
            dbg = d.paint.copy()
            for x, y, *_ in d.lights:
                cv2.circle(dbg, (int(x), int(y)), 3, (0, 255, 255), -1)
            for x, y, *_ in d.glows:
                cv2.circle(dbg, (int(x), int(y)), 1, (0, 200, 255), -1)
            cv2.imwrite(os.path.join(OUT, f"foto{n}_debug.jpg"), dbg)
        img = d.render()
        p = os.path.join(OUT, f"foto{n}_natal.jpg")
        cv2.imwrite(p, img, [cv2.IMWRITE_JPEG_QUALITY, 94])
        print("ok", p, len(d.lights), "LEDs")
