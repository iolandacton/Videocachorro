#!/usr/bin/env python3
"""Trilha indie chill ORIGINAL (composição própria, sem amostras de terceiros → uso comercial livre).

Guitarra limpa dedilhada (modelo físico de corda Karplus-Strong), uma segunda guitarra com
frases curtas, baixo macio e percussão leve (shaker, aro, bumbo quase inaudível). Sem batidas fortes.
Uso: .venv/bin/python pipeline/musica_indie.py SAIDA.wav --duracao 60 [--bpm 88] [--seed 4]
"""
from __future__ import annotations

import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
# Dmaj7 → Bm7 → Gmaj7 → A6sus: progressão I–vi–IV–V com sétimas, leve e solar.
ACORDES = [
    [50, 57, 61, 66, 69],  # Dmaj7
    [47, 54, 57, 62, 66],  # Bm7
    [43, 50, 54, 59, 62],  # Gmaj7
    [45, 52, 57, 62, 66],  # A6sus (A E A D F#)
]
DEDILHADO = [0, 2, 3, 4, 3, 2, 1, 3]  # índices do acorde em colcheias (fingerpicking)
FRASES = [[74, 73, 69], [71, 69, 66], [74, 76, 73], [69, 66, 64]]  # guitarra 2, a cada 2 compassos


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def corda(freq: float, dur: float, vel: float, rng, brilho: float = 0.55, t60: float = 2.6) -> np.ndarray:
    """Karplus-Strong com afinação fracionária, calculado em blocos de um período."""
    n = int(dur * SR)
    per = SR / freq
    L = int(per)
    a = per - L
    g = 10 ** (-3 / (t60 * freq))  # perda por período → decaimento parecido em todas as notas
    exc = rng.uniform(-1, 1, L)
    k = max(1, int((1 - brilho) * 8))  # palhetada mais macia = excitação mais filtrada
    exc = np.convolve(exc, np.ones(k) / k, "same")
    pos = max(1, int(L * 0.13))  # posição da palhetada perto do cavalete
    exc = exc - np.roll(exc, pos)
    y = np.zeros(n + L + 1)
    y[1:L + 1] = exc * vel
    i = L + 1
    while i < n + L + 1:
        j = min(i + L, n + L + 1)
        y[i:j] = g * ((1 - a) * y[i - L:j - L] + a * y[i - L - 1:j - L - 1])
        i = j
    out = y[1:n + 1]
    fim = int(0.08 * SR)
    out[-fim:] *= np.linspace(1, 0, fim)
    return out


def ruido_curto(rng, dur: float, decai: float, agudo: bool) -> np.ndarray:
    n = int(dur * SR)
    r = rng.standard_normal(n)
    r = np.diff(np.diff(r, prepend=0), prepend=0) if agudo else np.convolve(r, np.ones(8) / 8, "same")
    t = np.arange(n) / SR
    return r * np.minimum(t / 0.002, 1) * np.exp(-t * decai)


def gerar(duracao: float, bpm: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    compasso = 4 * beat
    total = int((duracao + 3) * SR)
    L, R = np.zeros(total), np.zeros(total)

    def por(s: np.ndarray, t0: float, gl: float, gr: float) -> None:
        i = int(max(t0, 0) * SR)
        if i >= total:
            return
        s = s[: total - i]
        L[i:i + len(s)] += gl * s
        R[i:i + len(s)] += gr * s

    swing = 0.06 * beat
    for c in range(int(np.ceil((duracao + 3) / compasso))):
        t0 = c * compasso
        acorde = ACORDES[c % 4]
        intro = c == 0  # primeiro compasso só a guitarra, entrando suave
        for k, idx in enumerate(DEDILHADO):
            t = t0 + k * beat / 2 + (swing if k % 2 else 0) + rng.normal(0, 0.006)
            vel = (0.32 if k % 4 == 0 else 0.22) * rng.uniform(0.85, 1.0) * (0.7 if intro else 1)
            nota = acorde[idx]
            pan = 0.35 + 0.06 * idx
            por(corda(hz(nota), 2.4, vel, rng, brilho=0.5 + 0.05 * idx), t, 1 - pan, pan)
        if c % 2 == 1 and not intro:  # guitarra 2: frase curta, à direita
            for k, nota in enumerate(FRASES[(c // 2) % 4]):
                por(corda(hz(nota), 2.8, 0.17, rng, brilho=0.45, t60=3.2), t0 + (1.5 + k) * beat, 0.3, 0.75)
        if not intro:
            raiz = acorde[0] - 12
            for tb, nota, d in ((0, raiz, 1.8), (2.5, raiz + 7, 1.2)):  # baixo macio
                por(corda(hz(nota), d * beat + 0.3, 0.42, rng, brilho=0.15, t60=1.4), t0 + tb * beat, 0.5, 0.5)
            for k in range(16):  # shaker em semicolcheias, com acentos
                acento = 1.0 if k % 4 == 2 else 0.55
                por(ruido_curto(rng, 0.07, 55, True), t0 + k * beat / 4 + (swing / 2 if k % 2 else 0),
                    0.012 * acento, 0.016 * acento)
            for b in (1, 3):  # aro bem leve
                rim = ruido_curto(rng, 0.09, 45, False) + 0.4 * np.sin(2 * np.pi * 1750 * np.arange(int(0.09 * SR)) / SR) \
                    * np.exp(-np.arange(int(0.09 * SR)) / SR * 60)
                por(rim, t0 + b * beat, 0.035, 0.03)
            n = int(0.3 * SR)
            tt = np.arange(n) / SR
            bumbo = np.sin(2 * np.pi * np.cumsum(48 + 50 * np.exp(-tt * 35)) / SR) * np.exp(-tt * 14)
            por(bumbo, t0, 0.12, 0.12)
    mix = np.stack([L, R], 1)
    return mix / (np.abs(mix).max() + 1e-9) * 0.8


def salvar(mix: np.ndarray, destino: Path) -> None:
    bruto = destino.with_suffix(".raw.wav")
    with wave.open(str(bruto), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    # timbre de guitarra limpa: corpo, chorus suave, sala curta e agudos macios
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(bruto), "-af",
                    "highpass=f=45,equalizer=f=220:t=q:w=1:g=2,equalizer=f=2500:t=q:w=1:g=-3,"
                    "chorus=0.7:0.9:45|58:0.35|0.28:0.3|0.45:1.6|1.1,"
                    "aecho=0.85:0.55:70|130|210:0.22|0.14|0.08,lowpass=f=11000,"
                    "acompressor=threshold=-18dB:ratio=2:attack=20:release=200",
                    str(destino)], check=True)
    bruto.unlink()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--duracao", type=float, required=True)
    ap.add_argument("--bpm", type=float, default=88)
    ap.add_argument("--seed", type=int, default=4)
    a = ap.parse_args()
    salvar(gerar(a.duracao, a.bpm, a.seed), a.saida)
    print(a.saida)
