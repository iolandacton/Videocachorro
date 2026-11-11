"""Mapa das luzes de Natal da Casa Tambaba.

Todas as coordenadas estão em pixels da foto aérea original
(public/originais/casa_tambaba_aerea.jpg, 1320x750).

Só há luzes em áreas externas: nada no telhado, nas placas solares,
nas janelas nem dentro da casa.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

# Cores em espaço linear
WARM = (1.00, 0.62, 0.30)   # branco-quente (~2700 K)
GOLD = (1.00, 0.50, 0.13)   # dourado
RED = (1.00, 0.07, 0.04)    # detalhes vermelhos

# Grupos (ordem em que acendem no vídeo)
PALMS, PERGOLA, LEFT, RIGHT, GOURMET, PATHS, FENCES = range(7)
GROUP_NAMES = ["palmeiras", "pergolado", "jardim_esq", "jardim_dir",
               "gourmet", "caminhos", "cercas"]


@dataclass
class Light:
    x: float
    y: float
    color: tuple
    group: int
    kind: str = "micro"     # micro | bulb | lantern | wash
    gain: float = 1.0
    snap: bool = False      # encaixar no ponto de vegetação mais próximo
    phase: float = 0.0      # fase da cintilação


# Telhado + caixa d'água: nenhuma luz e nenhum reflexo de luz por cima
ROOF = [(396, 211), (956, 213), (1017, 412), (364, 407)]
TANK = [(488, 176), (578, 178), (578, 216), (488, 216)]


def _along(pts, step, start=0.0):
    """Pontos igualmente espaçados ao longo de uma polilinha."""
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


def build(seed: int = 7) -> list[Light]:
    rng = random.Random(seed)
    L: list[Light] = []

    def add(x, y, color, group, kind="micro", gain=1.0, snap=False):
        L.append(Light(x, y, color, group, kind, gain, snap, rng.random()))

    def string(pts, step, color, group, kind="micro", gain=1.0, jitter=0.4,
               red_every=0, closed=False):
        if closed:
            pts = list(pts) + [pts[0]]
        for i, (x, y, _, _) in enumerate(_along(pts, step)):
            c = RED if red_every and i % red_every == red_every - 1 else color
            add(x + rng.uniform(-jitter, jitter), y + rng.uniform(-jitter, jitter),
                c, group, kind, gain * rng.uniform(0.8, 1.15))

    def garland(pts, posts_step, step, color, group, sag=3.0, gain=1.0,
                red_every=0):
        """Cordão com leve barriga entre os mourões."""
        total = 0.0
        for i, (x, y, dx, dy) in enumerate(_along(pts, step)):
            total = i * step
            u = (total % posts_step) / posts_step
            drop = sag * 4 * u * (1 - u)
            c = RED if red_every and i % red_every == red_every - 1 else color
            add(x, y + drop, c, group, "micro", gain * rng.uniform(0.8, 1.15))

    def cluster(cx, cy, r, n, group, color=WARM, gain=1.0, red=0.0, kind="micro"):
        """Rede de micro LEDs sobre um arbusto/copa."""
        for _ in range(n):
            a = rng.uniform(0, 2 * math.pi)
            d = r * math.sqrt(rng.random())
            c = RED if rng.random() < red else color
            add(cx + d * math.cos(a), cy + d * math.sin(a) * 0.8, c, group,
                kind, gain * rng.uniform(0.7, 1.15), snap=True)

    def wrap(x0, y0, x1, y1, n, group, width=2.0, color=WARM, gain=1.0):
        """Micro LEDs enrolados em um tronco (ziguezague = espiral vista de cima)."""
        for i in range(n):
            t = i / max(1, n - 1)
            s = width * (1 if i % 2 else -1) * (1 - 0.3 * t)
            add(x0 + (x1 - x0) * t + s, y0 + (y1 - y0) * t, color, group,
                "micro", gain)

    # ------------------------------------------------------------------
    # 1. Jardim frontal: seis palmeiras (micro LED branco-quente + copa)
    # (base x, base y, comprimento das folhas, abertura do leque em graus)
    front_palms = [
        (507, 486, 40, 62), (600, 486, 46, 66), (705, 489, 46, 66),
        (818, 489, 47, 66), (931, 492, 44, 64),
    ]
    for bx, by, ln, spread in front_palms:
        wrap(bx, by - 1, bx, by - 13, 9, PALMS, width=3.2, gain=1.25)
        add(bx, by - 26, WARM, PALMS, "wash", 1.0)          # copa iluminada
        add(bx, by - 6, WARM, PALMS, "lantern", 0.55)       # projetor no vaso
        fronds = 7
        for k in range(fronds):
            ang = math.radians(-spread + 2 * spread * k / (fronds - 1))
            flen = ln * (0.78 + 0.22 * math.cos(ang))
            for d in range(16, int(flen), 7):
                bend = 0.10 * (d / flen) ** 2 * flen * math.copysign(1, ang)
                add(bx + math.sin(ang) * d + bend * 0.3,
                    by - 8 - math.cos(ang) * d + abs(bend) * 0.25,
                    WARM, PALMS, "micro", 0.48, snap=True)
    # sexta palmeira (cica menor entre a 1ª e a 2ª)
    add(553, 481, WARM, PALMS, "wash", 0.7)
    add(553, 486, WARM, PALMS, "lantern", 0.45)
    cluster(553, 480, 13, 26, PALMS, gain=0.6)

    # ------------------------------------------------------------------
    # 3. Pergolado esquerdo: cordões dourados acompanhando a estrutura
    A, B, C, D = (232, 219), (291, 236), (250, 268), (191, 250)
    string([A, B, C, D], 3.2, GOLD, PERGOLA, "bulb", 0.9, closed=True)
    for t in (0.25, 0.5, 0.75):                     # travessas internas
        p = (A[0] + (B[0] - A[0]) * t, A[1] + (B[1] - A[1]) * t)
        q = (D[0] + (C[0] - D[0]) * t, D[1] + (C[1] - D[1]) * t)
        string([p, q], 4.2, GOLD, PERGOLA, "micro", 0.9)
    wrap(D[0] + 1, D[1] + 4, 206, 287, 8, PERGOLA, 1.3, GOLD)   # pilares
    wrap(C[0], C[1] + 4, 245, 298, 7, PERGOLA, 1.3, GOLD)
    wrap(B[0] - 1, B[1] + 4, 287, 262, 6, PERGOLA, 1.3, GOLD)
    add(240, 250, GOLD, PERGOLA, "wash", 0.8)

    # ------------------------------------------------------------------
    # 2. Jardim lateral esquerdo: plantas, arbustos e caminhos de pedra
    left_plants = [  # x, y, raio, n, vermelho
        (362, 190, 14, 22, 0.08), (352, 212, 9, 10, 0.0), (368, 228, 9, 12, 0.25),
        (312, 240, 15, 22, 0.0), (338, 255, 9, 10, 0.1), (352, 272, 10, 14, 0.1),
        (330, 292, 10, 12, 0.0), (338, 318, 10, 12, 0.1), (316, 338, 8, 8, 0.0),
        (207, 337, 13, 14, 0.0), (233, 322, 8, 7, 0.15),
        (126, 346, 20, 30, 0.0), (140, 376, 12, 14, 0.2), (182, 386, 13, 16, 0.0),
        (280, 283, 9, 9, 0.1), (268, 392, 12, 12, 0.0),
        (140, 432, 24, 34, 0.05), (192, 440, 18, 22, 0.05), (232, 470, 18, 24, 0.05),
        (188, 494, 13, 16, 0.3), (158, 474, 14, 14, 0.0), (220, 515, 14, 14, 0.08),
        (262, 478, 14, 16, 0.0),
    ]
    for x, y, r, n, red in left_plants:
        cluster(x, y, r, n, LEFT, gain=0.75, red=red)
        add(x, y, WARM, LEFT, "wash", 0.38)
    # cordões acompanhando os caminhos de pedra
    stone_paths = [
        [(350, 186), (366, 182), (392, 186), (408, 196), (410, 210), (400, 222),
         (386, 236), (381, 256), (377, 280), (370, 300), (356, 320), (340, 336),
         (324, 349), (300, 357), (280, 369), (262, 377), (244, 384)],
        [(350, 187), (352, 214)],
        [(320, 268), (302, 292), (286, 309), (265, 315), (240, 312), (215, 310),
         (196, 315), (181, 330), (173, 350), (181, 369), (200, 377), (224, 380),
         (244, 385)],
        [(288, 312), (293, 332), (296, 350), (300, 357)],
    ]
    for pl in stone_paths:
        for i, (x, y, dx, dy) in enumerate(_along(pl, 7.5)):
            side = 5.5 if i % 2 else -5.5
            add(x - dy * side, y + dx * side, WARM, LEFT, "micro", 1.0)

    # ------------------------------------------------------------------
    # 4. Jardim lateral direito: palmeiras e plantas, luz discreta
    right_plants = [
        (1010, 222, 20, 26, 0.0), (1040, 262, 14, 16, 0.0), (1062, 268, 12, 14, 0.05),
        (1082, 282, 10, 10, 0.1), (1112, 254, 16, 20, 0.0), (1150, 266, 16, 20, 0.0),
        (1128, 290, 9, 8, 0.15), (1175, 262, 10, 8, 0.0), (1216, 300, 9, 9, 0.1),
        (1266, 270, 18, 22, 0.0), (1252, 338, 24, 34, 0.0), (1292, 350, 12, 10, 0.1),
        (1300, 392, 14, 12, 0.1), (1296, 440, 14, 10, 0.0), (1272, 452, 16, 14, 0.1),
        (1010, 462, 12, 14, 0.0),
    ]
    for x, y, r, n, red in right_plants:
        cluster(x, y, r, n, RIGHT, gain=0.7, red=red)
        add(x, y, WARM, RIGHT, "wash", 0.36)
    wrap(1005, 240, 998, 266, 9, RIGHT, 1.6, gain=1.0)      # troncos
    wrap(1250, 352, 1245, 371, 7, RIGHT, 1.6, gain=1.0)
    wrap(1011, 472, 1012, 500, 8, RIGHT, 1.2, gain=0.9)

    # ------------------------------------------------------------------
    # 5. Área gourmet: cordões ao redor da cobertura e da estrutura
    roof = [(1065, 360), (1180, 361), (1213, 366), (1250, 446), (1097, 438)]
    string(roof, 3.6, GOLD, GOURMET, "bulb", 0.95, closed=True, red_every=12)
    umbrella = [(1041, 325), (1087, 301), (1130, 335), (1096, 357)]
    string(umbrella, 4.0, WARM, GOURMET, "micro", 0.9, closed=True)
    wrap(1097, 442, 1093, 482, 9, GOURMET, 1.3, GOLD)        # pilares
    wrap(1204, 449, 1194, 486, 9, GOURMET, 1.3, GOLD)
    wrap(1232, 449, 1229, 462, 4, GOURMET, 1.3, GOLD)
    add(1140, 468, WARM, GOURMET, "wash", 1.0)               # piso sob a cobertura
    add(1090, 420, WARM, GOURMET, "wash", 0.5)

    # ------------------------------------------------------------------
    # 6. Caminhos e entrada: pequenas luminárias até o portão
    for y in (466, 481, 496, 511):
        add(647, y, WARM, PATHS, "lantern", 1.0)
        add(690, y + 1, WARM, PATHS, "lantern", 1.0)
    for x, y in ((650, 527), (690, 529)):                   # portão social
        add(x, y, GOLD, PATHS, "lantern", 0.9)
        add(x, y - 5, RED, PATHS, "micro", 1.3)
    string([(652, 524), (688, 526)], 4.0, GOLD, PATHS, "micro", 0.9, red_every=3)
    for x, y in ((269, 512), (346, 516)):                   # portão de veículos
        add(x, y, GOLD, PATHS, "lantern", 0.8)
    add(404, 508, GOLD, PATHS, "lantern", 0.8)              # pilar da entrada
    add(404, 503, RED, PATHS, "micro", 1.3)
    # balizadores no contorno do jardim junto à calçada
    for x, y, _, _ in _along([(104, 408), (132, 446), (166, 487), (204, 522),
                              (243, 538)], 23):
        add(x, y, WARM, PATHS, "lantern", 0.7)
    # balizadores no rodapé da cerca frontal
    curb = [(262, 540), (400, 543), (640, 546)]
    for x, y, _, _ in _along(curb, 47, 20):
        if not 380 < x < 432:
            add(x, y - 2, WARM, PATHS, "lantern", 0.6)
    curb2 = [(700, 548), (1020, 554), (1318, 560)]
    for x, y, _, _ in _along(curb2, 47, 20):
        add(x, y - 2, WARM, PATHS, "lantern", 0.6)
    # arvoretas da calçada
    for x, y, r, n in ((718, 520, 10, 12), (812, 515, 11, 14), (900, 546, 9, 10),
                       (944, 530, 8, 9), (1003, 540, 9, 10), (1105, 520, 13, 14)):
        cluster(x, y, r, n, PATHS, gain=0.6, red=0.12)

    # ------------------------------------------------------------------
    # 7. Cercas e limites do jardim: cordão sutil
    garland([(352, 524), (382, 525)], 53, 4.6, WARM, FENCES, gain=0.6)
    garland([(432, 526), (644, 531)], 53, 4.6, WARM, FENCES, gain=0.6, red_every=12)
    garland([(696, 533), (1020, 540), (1318, 546)], 53, 4.6, WARM, FENCES,
            gain=0.6, red_every=12)
    garland([(166, 299), (245, 212), (300, 172)], 40, 5.0, WARM, FENCES,
            sag=2.0, gain=0.5)
    garland([(392, 164), (500, 176)], 40, 5.0, WARM, FENCES, sag=2.0, gain=0.45)
    for x, y, r, n in ((1045, 550, 20, 18), (1075, 560, 12, 8), (1195, 556, 22, 20),
                       (1262, 552, 24, 22)):               # arbustos da divisa
        cluster(x, y, r, n, FENCES, gain=0.55, red=0.15)
        add(x, y, WARM, FENCES, "wash", 0.25)

    return L
