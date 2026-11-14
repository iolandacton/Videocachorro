#!/usr/bin/env python3
"""Edição da foto IMG_7578: retoque localizado (braço, barriga/cintura, cabelo)
e colorimetria editorial solar. Uso: editar.py ORIGINAL SAIDA_DIR

Nada fora das máscaras é reamostrado: rosto, textos e logotipos mantêm a
geometria original pixel a pixel; a resolução de saída é a do original.
"""
import sys
import numpy as np
import cv2

# ----------------------------------------------------------------- utilidades


def smoothstep(x, a, b):
    t = np.clip((x - a) / float(b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def poly_mask(shape, pts, feather):
    m = np.zeros(shape[:2], np.float32)
    cv2.fillPoly(m, [np.array(pts, np.int32)], 1.0)
    if feather > 0:
        m = cv2.GaussianBlur(m, (0, 0), feather)
    return m


def ellipse_mask(shape, center, axes, angle, feather):
    m = np.zeros(shape[:2], np.float32)
    cv2.ellipse(m, center, axes, angle, 0, 360, 1.0, -1)
    return cv2.GaussianBlur(m, (0, 0), feather)


# ------------------------------------------------------- deformação localizada
# Equivalente ao "empurrar" do Liquify: um campo de deslocamento suave, com
# queda curta para fora do contorno (fundo quase não se mexe) e longa para
# dentro (o corpo é comprimido de forma distribuída, sem dobras).


def torso_field(h, w, edge_y, edge_x, amp_fn, inward, s_out, s_in):
    """Deslocamento horizontal ao longo de um contorno x=edge(y)."""
    ys = np.arange(h, dtype=np.float32)
    ex = np.interp(ys, edge_y, edge_x).astype(np.float32)[:, None]
    amp = amp_fn(ys).astype(np.float32)[:, None]
    xs = np.arange(w, dtype=np.float32)[None, :]
    u = (xs - ex) * inward            # >0 = dentro do corpo
    sig = np.where(u >= 0, s_in, s_out)
    return inward * amp * np.exp(-0.5 * (u / sig) ** 2)


def arm_field(h, w, p0, p1, amp_fn, s_out, s_in):
    """Deslocamento perpendicular à borda inferior do braço (segmento p0-p1)."""
    p0 = np.array(p0, np.float32)
    p1 = np.array(p1, np.float32)
    d = (p1 - p0) / np.linalg.norm(p1 - p0)
    n_in = np.array([d[1], -d[0]], np.float32)   # para cima/direita = dentro
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    rx, ry = xs - p0[0], ys - p0[1]
    along = rx * d[0] + ry * d[1]
    u = rx * n_in[0] + ry * n_in[1]              # >0 = dentro do braço
    amp = amp_fn(p0[0] + along * d[0])           # amplitude em função de x
    sig = np.where(u >= 0, s_in, s_out)
    mag = amp * np.exp(-0.5 * (u / sig) ** 2)
    return mag * n_in[0], mag * n_in[1]


def apply_warp(img, dx, dy):
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    out = cv2.remap(img, xs - dx, ys - dy, cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REFLECT)
    moved = (np.abs(dx) + np.abs(dy)) > 0.02
    res = img.copy()
    res[moved] = out[moved]
    return res, moved


def retouch_body(img, P):
    h, w = img.shape[:2]
    dx = np.zeros((h, w), np.float32)
    dy = np.zeros((h, w), np.float32)

    # Barriga (contorno frontal, lado esquerdo da imagem)
    ly = [1900, 1945, 1990, 2020, 2060, 2100, 2140, 2160, 2180, 2200, 2220,
          2240, 2260, 2300]
    lx = [668, 668, 668, 667, 664, 665, 668, 661, 658, 652, 646, 638, 636, 630]
    dx += torso_field(
        h, w, ly, lx,
        lambda y: P['belly'] * smoothstep(y, 1925, 1990) *
        (1 - smoothstep(y, 2130, 2270)),
        inward=+1, s_out=20.0, s_in=85.0)

    # Cintura (contorno das costas, lado direito da imagem)
    ry = [1900, 1960, 2000, 2020, 2040, 2060, 2080, 2100, 2120, 2140, 2200]
    rx = [990, 990, 990, 997, 1006, 1017, 1026, 1033, 1038, 1041, 1046]
    dx += torso_field(
        h, w, ry, rx,
        lambda y: P['waist'] * smoothstep(y, 1920, 1985) *
        (1 - smoothstep(y, 2020, 2160)),
        inward=-1, s_out=20.0, s_in=85.0)

    # Braço erguido: contorno inferior entre cotovelo e manga
    ax, ay = arm_field(
        h, w, (502, 1442), (597, 1511),
        lambda x: P['arm'] * smoothstep(x, 482, 535) *
        (1 - smoothstep(x, 552, 612)),
        s_out=14.0, s_in=17.0)
    # restringe à vizinhança do braço
    box = np.zeros((h, w), np.float32)
    box[1380:1600, 440:660] = 1
    box = cv2.GaussianBlur(box, (0, 0), 8)
    dx += ax * box
    dy += ay * box

    return apply_warp(img, dx, dy) + (dx, dy)


def soften_belly_folds(img, strength):
    """Dodge de média frequência: clareia só os vincos escuros do cós, que é
    o que dá leitura de volume na barriga. Não altera a geometria."""
    m = poly_mask(img.shape, [(690, 2010), (985, 2010), (1010, 2075),
                              (1015, 2170), (700, 2170), (685, 2100)], 14)
    f = img.astype(np.float32)
    y = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    small = cv2.GaussianBlur(y, (0, 0), 4)
    big = cv2.GaussianBlur(y, (0, 0), 22)
    lift = np.clip(big - small, 0, None) * strength * m
    gain = (y + lift) / np.maximum(y, 1.0)
    return np.clip(f * gain[..., None] + 0.5, 0, 255).astype(np.uint8)


# ------------------------------------------------------------ fios dispersos


def tidy_hair(img, polys, k=15, feather=6):
    """Remove fios finos e isolados dentro dos polígonos. O fio é detectado
    pela queda no canal vermelho em relação ao fundo (fechamento morfológico);
    a bainha da bandeira, que quase não perde vermelho, fica intacta. O
    preenchimento é feito por inpainting a partir do fundo vizinho."""
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    r = img[..., 2]
    drop = cv2.morphologyEx(r, cv2.MORPH_CLOSE, ker).astype(np.float32) - r
    strand = smoothstep(drop, 11.0, 20.0)
    region = np.zeros(img.shape[:2], np.float32)
    for p in polys:
        region = np.maximum(region, poly_mask(img.shape, p, feather))
    hard = ((strand > 0.25) & (region > 0.02)).astype(np.uint8)
    hard = cv2.dilate(hard, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    filled = cv2.inpaint(img, hard, 5, cv2.INPAINT_TELEA).astype(np.float32)
    a = cv2.GaussianBlur(hard.astype(np.float32), (0, 0), 1.0) * region
    a = np.clip(a * 1.6, 0, 1)[..., None]
    rng = np.random.default_rng(7)
    grain = rng.normal(0, 1.0, img.shape[:2]).astype(np.float32)[..., None]
    out = img.astype(np.float32) * (1 - a) + (filled + grain) * a
    return np.clip(out + 0.5, 0, 255).astype(np.uint8), a[..., 0]


# --------------------------------------------------------------- colorimetria


def srgb_to_lin(v):
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(v):
    v = np.clip(v, 0, None)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


def person_mask(shape):
    """Pele da modelo (protegida do reforço de laranja)."""
    polys = [
        # rosto e pescoço
        [(735, 1190), (800, 1160), (900, 1175), (960, 1260), (975, 1360),
         (960, 1470), (990, 1530), (930, 1580), (850, 1590), (800, 1500),
         (760, 1420), (735, 1330)],
        # braço erguido e mão
        [(150, 1085), (260, 1090), (350, 1215), (470, 1285), (650, 1375),
         (655, 1470), (600, 1525), (500, 1450), (380, 1370), (300, 1330),
         (215, 1260), (150, 1170)],
        # braço da frente e mão
        [(470, 1700), (560, 1680), (640, 1760), (800, 1790), (1000, 1740),
         (1090, 1760), (1095, 1860), (1000, 1930), (850, 1940), (660, 1900),
         (540, 1880), (470, 1800)],
        # abdômen
        [(660, 1935), (1000, 1935), (1000, 2005), (660, 2005)],
        # pernas
        [(625, 2300), (1020, 2330), (1010, 2576), (620, 2576)],
    ]
    m = np.zeros(shape[:2], np.float32)
    for p in polys:
        cv2.fillPoly(m, [np.array(p, np.int32)], 1.0)
    return cv2.GaussianBlur(m, (0, 0), 14)


def grade(img, G):
    h, w = img.shape[:2]
    rgb = img[..., ::-1].astype(np.float32) / 255.0
    lin = srgb_to_lin(rgb)

    # 1) balanço de branco mais quente + exposição
    wb = np.array(G['wb'], np.float32)
    lum_w = np.array([0.2126, 0.7152, 0.0722], np.float32)
    wb = wb / float((wb * lum_w).sum())
    lin = lin * wb * G['exposure']

    # 2) luz suave no rosto (dodge com máscara elíptica bem difusa)
    face = ellipse_mask(img.shape, (838, 1322), (120, 165), -8, 45)
    lin = lin * (1.0 + G['face'] * face[..., None])

    # 3) curva: levanta sombras, protege altas luzes, leve contraste
    Y = (lin * lum_w).sum(-1)
    Yg = lin_to_srgb(Y)
    lift = G['shadows'] * Yg * (1 - Yg) ** 3 * 4.0          # pico nas sombras
    sc = G['contrast'] * np.sin(2 * np.pi * Yg) * -0.05     # S suave
    Yt = Yg + lift + sc
    knee = 0.86                                              # ombro suave
    over = np.clip(Yt - knee, 0, None)
    Yt = np.where(Yt > knee, knee + (1 - knee) * (1 - np.exp(-over / (1 - knee))), Yt)
    gain = srgb_to_lin(np.clip(Yt, 0, 1)) / np.maximum(Y, 1e-5)
    lin = lin * np.clip(gain, 0.5, 2.5)[..., None]
    # compressão suave de canal (evita estourar o vermelho da bandeira)
    lin = np.where(lin > 0.8, 0.8 + 0.2 * (1 - np.exp(-(lin - 0.8) / 0.2)), lin)
    rgb2 = lin_to_srgb(lin).astype(np.float32)

    # 4) cor seletiva em Lab
    lab = cv2.cvtColor(np.clip(rgb2, 0, 1), cv2.COLOR_RGB2Lab)
    L, a, b = cv2.split(lab)
    C = np.sqrt(a * a + b * b)
    hue = np.degrees(np.arctan2(b, a))                       # Lab hue

    skin = person_mask(img.shape)
    # laranja/coral da bandeira e do painel: hue ~20-60, croma alta
    w_or = smoothstep(hue, 12, 26) * (1 - smoothstep(hue, 58, 75)) * \
        smoothstep(C, 30, 55) * (1 - skin)
    # turquesa: hue ~ -175..-120 (ou 180+)
    hue_t = np.where(hue < 0, hue + 360, hue)
    w_tq = smoothstep(hue_t, 170, 195) * (1 - smoothstep(hue_t, 245, 265)) * \
        smoothstep(C, 12, 28)
    shorts = poly_mask(img.shape, [(640, 1975), (1010, 1975), (1065, 2200),
                                   (1040, 2420), (600, 2380), (615, 2250)], 12)
    k = 1.0 + G['vibrance'] * (1 - smoothstep(C, 20, 60)) * (1 - skin) \
        + G['orange'] * w_or + (G['turq'] + G['turq_shorts'] * shorts) * w_tq
    a *= k
    b *= k
    # o reforço de croma em Lab puxa o laranja para o vermelho; compensa com
    # uma rotação mínima de matiz em direção ao laranja
    th = np.radians(G['orange_hue']) * w_or
    a, b = a * np.cos(th) - b * np.sin(th), a * np.sin(th) + b * np.cos(th)
    L = L + G['turq_L'] * w_tq * shorts + G['orange_L'] * w_or
    out = cv2.cvtColor(cv2.merge([np.clip(L, 0, 100).astype(np.float32), a.astype(np.float32), b.astype(np.float32)]), cv2.COLOR_Lab2RGB)
    out = np.where(out > 0.9, 0.9 + 0.1 * (1 - np.exp(-(out - 0.9) / 0.1)), out)
    out = np.clip(out, 0, 1)
    return (out[..., ::-1] * 255.0 + 0.5).astype(np.uint8)


# ---------------------------------------------------------------------- main

PARAMS = dict(belly=10.0, waist=8.0, arm=6.5, folds=0.45)
GRADE = dict(wb=(1.035, 1.0, 0.915), exposure=1.10, face=0.16, shadows=0.11,
             contrast=0.55, vibrance=0.06, orange=0.12, orange_L=1.0, orange_hue=4.0,
             turq=0.07, turq_shorts=0.07, turq_L=2.5)

HAIR_POLYS = [
    # fios finos acima da massa de cabelo, sobre a bandeira
    [(1082, 1196), (1200, 1232), (1345, 1292), (1348, 1344), (1262, 1340),
     (1215, 1334), (1180, 1322), (1140, 1292), (1108, 1240)],
    # fios finos soltos abaixo da última mecha
    [(1180, 1528), (1240, 1516), (1290, 1530), (1292, 1572), (1280, 1588),
     (1250, 1590), (1205, 1570)],
]

if __name__ == '__main__':
    src, outdir = sys.argv[1], sys.argv[2]
    img = cv2.imread(src, cv2.IMREAD_COLOR)
    ret, moved, dx, dy = retouch_body(img, PARAMS)
    ret = soften_belly_folds(ret, PARAMS['folds'])
    ret, hair_a = tidy_hair(ret, HAIR_POLYS)
    cv2.imwrite(f'{outdir}/retoque.png', ret)
    fin = grade(ret, GRADE)
    cv2.imwrite(f'{outdir}/final.png', fin)
    cv2.imwrite(f'{outdir}/grade_only.png', grade(img, GRADE))
    np.save(f'{outdir}/disp.npy', np.stack([dx, dy]))
    print('tamanho', fin.shape, 'desloc. máx px', float(np.hypot(dx, dy).max()),
          'pixels reamostrados %.2f%%' % (100 * moved.mean()),
          'pixels de cabelo alterados %.3f%%' % (100 * (hair_a > 0.05).mean()))
