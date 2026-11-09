#!/usr/bin/env python3
"""Gera uma trilha lo-fi descontraída original (sem licença de terceiros).

Piano elétrico em acordes com sétima, baixo suave, bateria leve com swing e chiado de vinil.
Uso: python pipeline/musica.py SAIDA.wav --duracao 30 [--bpm 84] [--seed 3]
"""
from __future__ import annotations

import argparse
import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000
# Cmaj7 → Am7 → Fmaj7 → G6: progressão I–vi–IV–V, leve e "ensolarada".
ACORDES = [(48, [60, 64, 67, 71]), (45, [57, 60, 64, 67]), (41, [57, 60, 64, 65]), (43, [55, 59, 62, 64])]


def hz(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n: int, ataque: float, decai: float) -> np.ndarray:
    t = np.arange(n) / SR
    return np.minimum(t / ataque, 1.0) * np.exp(-t * decai)


def piano(midi: int, dur: float, vel: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    som = sum(a * np.sin(2 * np.pi * f * h * t) * np.exp(-t * (1.6 + 1.4 * h))
              for h, a in ((1, 1.0), (2, 0.45), (3, 0.18), (4, 0.08)))
    som *= 1 + 0.08 * np.sin(2 * np.pi * 4.8 * t)  # tremolo de Rhodes
    return vel * som * np.minimum(t / 0.006, 1) * np.minimum((dur - t) / 0.05, 1).clip(0)


def baixo(midi: int, dur: float) -> np.ndarray:
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = hz(midi)
    return (np.sin(2 * np.pi * f * t) + 0.25 * np.sin(4 * np.pi * f * t)) * env(n, 0.01, 1.8) \
        * np.minimum((dur - t) / 0.04, 1).clip(0)


def bumbo() -> np.ndarray:
    n = int(0.35 * SR)
    t = np.arange(n) / SR
    fase = 2 * np.pi * np.cumsum(50 + 70 * np.exp(-t * 30)) / SR
    return np.sin(fase) * env(n, 0.002, 11)


def ruido_filtrado(rng, dur: float, decai: float, passa_alta: bool) -> np.ndarray:
    n = int(dur * SR)
    r = rng.standard_normal(n)
    r = np.diff(r, prepend=0) if passa_alta else np.convolve(r, np.ones(6) / 6, "same")
    return r * env(n, 0.001, decai)


def gerar(duracao: float, bpm: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    beat = 60 / bpm
    compasso = 4 * beat
    total = int((duracao + 2) * SR)
    L, R = np.zeros(total), np.zeros(total)

    def por(sinal: np.ndarray, t0: float, gl: float, gr: float | None = None) -> None:
        i = int(t0 * SR)
        if i >= total:
            return
        s = sinal[: total - i]
        L[i:i + len(s)] += gl * s
        R[i:i + len(s)] += (gl if gr is None else gr) * s

    nc = int(np.ceil((duracao + 2) / compasso))
    for c in range(nc):
        t0 = c * compasso
        raiz, notas = ACORDES[c % len(ACORDES)]
        # acordes: tempo 1 (longo) e "e" do 2 (curto), com leve dedilhado
        for tt, dur, vel in ((0, 2.2 * beat, 0.16), (1.5 * beat, 1.2 * beat, 0.10), (3 * beat, 0.9 * beat, 0.07)):
            for k, nota in enumerate(notas):
                pan = 0.35 + 0.1 * k
                por(piano(nota, dur, vel * rng.uniform(0.85, 1.0)), t0 + tt + 0.012 * k, 1 - pan, pan)
        por(baixo(raiz, 1.9 * beat), t0, 0.32)
        por(baixo(raiz + 7, 0.9 * beat), t0 + 2.5 * beat, 0.24)
        for b in (0, 2.5):
            por(bumbo(), t0 + b * beat, 0.42)
        for b in (1, 3):  # aro/caixa abafada
            por(ruido_filtrado(rng, 0.18, 28, False), t0 + b * beat, 0.07)
        for k in range(8):  # chimbal com swing
            atraso = (0.16 if k % 2 else 0) * beat
            por(ruido_filtrado(rng, 0.06, 70, True), t0 + k * beat / 2 + atraso, 0.035 if k % 2 else 0.05,
                0.05 if k % 2 else 0.035)

    # chiado de vinil discreto
    estalos = (rng.random(total) > 0.9996) * rng.uniform(-0.05, 0.05, total)
    chiado = np.convolve(rng.standard_normal(total), np.ones(40) / 40, "same") * 0.012 + estalos
    L += chiado
    R += np.roll(chiado, 97)
    mix = np.stack([L, R], 1)
    return mix / (np.abs(mix).max() + 1e-9) * 0.8


def salvar(mix: np.ndarray, destino: Path) -> None:
    bruto = destino.with_suffix(".raw.wav")
    with wave.open(str(bruto), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((mix * 32767).astype("<i2").tobytes())
    # timbre "lo-fi": tira agudos, adiciona sala curta
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(bruto), "-af",
                    "lowpass=f=6500,highpass=f=40,aecho=0.85:0.6:45|90:0.18|0.1",
                    str(destino)], check=True)
    bruto.unlink()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--duracao", type=float, required=True)
    ap.add_argument("--bpm", type=float, default=84)
    ap.add_argument("--seed", type=int, default=3)
    a = ap.parse_args()
    salvar(gerar(a.duracao, a.bpm, a.seed), a.saida)
    print(a.saida)
