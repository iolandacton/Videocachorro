#!/usr/bin/env python3
"""Oficina Sete — colorimetria (v8). Uma curva por take, aplicada ANTES de qualquer conversão para 8 bits.

Problema da versão anterior: o original (Sony 10 bits, BT.709) grava luz acima do "branco legal" (níveis
940–1019); a conversão antiga cortava tudo isso em branco puro — por isso o fundo "estourava", principalmente
na abertura (janela atrás do apresentador). Aqui o original é lido com a faixa COMPLETA (0–1023) e a curva:
  1. tira o pedestal do preto (64) e aplica o balanço/exposição do take (mesmos ganhos por neutro de antes);
  2. dá densidade aos meios-tons (imagem menos lavada) com um S suave;
  3. comprime as altas luzes de forma progressiva ("ombro" de filme): o que estava acima do branco volta a
     ter desenho e o que está realmente queimado no sensor vira um branco suave, sem borda dura.
Saída: LUT 1D (.cube) por take em public/oficina/gimbal/cor/<TAKE>.cube, usada pelo filtro lut1d do FFmpeg
em 16 bits; a saturação é ajustada depois (matriz), também em 16 bits.
"""
import json
from pathlib import Path
import numpy as np

NEUTRO = json.load(open("public/oficina/analise/neutros.json"))
ALVO = (206.0, 195.0, 190.0)          # branco de referência da cena (levemente quente), como nas versões anteriores
PRETO, BRANCO = 64 / 1023, 940 / 1023
N = 4096
SAT = 1.10                            # a compressão das luzes tira um pouco de cor; devolve
# Perfis de cor. v8: mais densa e quente (a cliente achou o apresentador amarelo). v9: mesma recuperação das
# altas luzes, meios-tons mais leves, balanço mais frio (wb multiplica os ganhos R,G,B do take), menos saturação
# no geral e ainda menos nos amarelos/laranjas (madeira + LED quente contaminando a pele).
PERFIS = {
    "v8": dict(tom=dict(dens=1.16, ombro=0.56, teto=0.972), wb=(1, 1, 1), sat=1.10, amarelo=0.0),
    "v9": dict(tom=dict(dens=1.06, ombro=0.54, teto=0.965), wb=(0.963, 1.0, 1.043), sat=0.88, amarelo=-0.26),
}


def tom(L, exp=0.0, dens=1.16, ombro=0.56, teto=0.972):
    """L = nível real da cena (0 = preto, 1 = branco legal, até ~1,09 nos superbrancos) → saída 0–1."""
    L = np.clip(L, 0, None) * 2 ** exp
    m = L ** dens                                             # densidade nos meios-tons
    m = m + 0.035 * np.sin(2 * np.pi * np.clip(m, 0, 1)) * -1 * (m < 1)   # S suave: sombras mais firmes, pele viva
    # ombro: acima de "ombro" a curva dobra e se aproxima do teto sem nunca encostar de forma brusca
    x = np.clip(m - ombro, 0, None)
    k = teto - ombro
    return np.where(m <= ombro, m, ombro + k * (1 - np.exp(-x / k)))


def ganhos(take):
    return [max(0.85, min(1.25, ALVO[i] / v)) for i, v in enumerate(NEUTRO[take])]


def lut(take, wb=(1, 1, 1), **kw):
    x = np.linspace(0, 1, N)                                  # código do original interpretado como faixa completa
    L = (x - PRETO) / (BRANCO - PRETO)
    return np.stack([tom(L * g * w, **kw) for g, w in zip(ganhos(take), wb)], 1)


def gravar(take, sufixo="", wb=(1, 1, 1), **kw):
    D = Path("public/oficina/gimbal/cor"); D.mkdir(parents=True, exist_ok=True)
    t = lut(take, wb, **kw)
    with open(D / f"{take}{sufixo}.cube", "w") as f:
        f.write(f"LUT_1D_SIZE {N}\n")
        f.writelines(f"{r:.6f} {g:.6f} {b:.6f}\n" for r, g, b in t)
    return D / f"{take}{sufixo}.cube"


def matriz_sat(s=SAT):
    """colorchannelmixer que muda só a saturação (pesos de luminância BT.709)."""
    lr, lg, lb = 0.2126, 0.7152, 0.0722
    m = [[lr + s * (1 - lr), lg * (1 - s), lb * (1 - s)], [lr * (1 - s), lg + s * (1 - lg), lb * (1 - s)],
         [lr * (1 - s), lg * (1 - s), lb + s * (1 - lb)]]
    n = "rr rg rb gr gg gb br bg bb".split()
    return "colorchannelmixer=" + ":".join(f"{k}={v:.5f}" for k, v in zip(n, sum(m, [])))


def filtro(take, perfil="v8", **troca):
    """cadeia do FFmpeg: original lido com a faixa completa, em RGB de 16 bits → curva do take → saturação
    (→ no v9, menos saturação só nos amarelos/laranjas)."""
    P = {**PERFIS[perfil], **troca}
    arq = gravar(take, "" if perfil == "v8" else f"_{perfil}", P["wb"], **P["tom"])
    f = ("scale=iw:ih:in_range=full:out_range=full:flags=bicubic+accurate_rnd+full_chroma_int,format=gbrp16le,"
         f"lut1d=file={arq}:interp=linear,{matriz_sat(P['sat'])}")
    if P["amarelo"]:
        f += f",huesaturation=colors=r+y:saturation={P['amarelo']}:strength=1"
    return f


if __name__ == "__main__":
    for k in NEUTRO:
        print(gravar(k))
