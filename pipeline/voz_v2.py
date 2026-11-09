#!/usr/bin/env python3
"""Voz v2: tratamento profissional a partir dos ÁUDIOS ORIGINAIS (nada pré-processado).

Para cada fonte:
  1. decodifica o original (48 kHz mono)
  2. DeepFilterNet 3 (redução de ruído neural) com limite de atenuação — evita voz robótica
  3. EQ por correspondência: mede o espectro da fala e corrige rumo a uma curva de referência
     (±4 dB no máximo), para as três fontes terem o mesmo timbre; tira o "abafado"
  4. de-esser leve, compressão moderada, normalização linear
Depois edita: remove deixas/falsas partidas e encurta pausas longas, cortando sempre no ponto
de menor energia (nunca no meio de sílaba) e preservando a respiração antes da próxima frase.

Saída em public/arq_v2/voz/: voz_tratada.wav, voz_original_editada.wav (mesmos cortes, sem
tratamento — para comparação), palavras.json (tempos já no vídeo novo) e cortes.json.
Uso: .venv/bin/python pipeline/voz_v2.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from editar import ffmpeg, loudnorm_linear  # noqa: E402

SR = 48000
OUT = Path("public/arq_v2/voz")
DF_BIN = Path(".tools/deep-filter")
DF_URL = "https://github.com/Rikorose/DeepFilterNet/releases/download/v0.5.6/deep-filter-0.5.6-x86_64-unknown-linux-musl"
DF_SHA = "70775e251eee44c0f2451a1e833326cf8bcbbe304d3e7cd12851e6fce72ef7da"

# Fontes na ordem do vídeo. "janela" = trecho útil (fora dela: deixa "Vai, pode ir" e a frase
# repetida "Agora o que eu amo usar" no fim do áudio 1).
FONTES = [
    {"id": "gancho", "arquivo": "public/originais/yuri_gancho_C6282.mp4", "palavras": "src/arquitetura/palavras_gancho.json"},
    {"id": "audio1", "arquivo": "public/originais/arquitetura_audio_1.mp3", "palavras": "src/arquitetura/palavras_audio1.json",
     "ate_palavra": "baixo."},
    {"id": "audio2", "arquivo": "public/originais/arquitetura_audio_2.mp3", "palavras": "src/arquitetura/palavras_audio2.json"},
]
PAUSA_MAX = 0.65      # pausas maiores que isso são encurtadas…
DEPOIS = 0.18         # …mantendo o fim natural da palavra anterior
ANTES = 0.32          # …e a respiração antes da próxima
ENTRE_FONTES = 0.30   # respiro entre gancho/áudio 1/áudio 2
FADE = 0.012          # micro-fade em cada corte (sem estalo)
# de-esser leve + compressão moderada (a EQ é ajustada já medindo o resultado desta cadeia)
DINAMICA = "deesser=i=0.35:m=0.5:f=0.5:s=o,acompressor=threshold=-20dB:ratio=2.2:attack=12:release=160:knee=6:makeup=1.5"

# Curva de referência (energia relativa por banda, dB) de uma voz masculina clara e presente.
BANDAS = [(80, 160), (160, 320), (320, 640), (640, 1250), (1250, 2500), (2500, 5000), (5000, 8000), (8000, 12000)]
ALVO = [-12.0, -8.0, -4.5, -6.5, -13.5, -19.5, -25.5, -31.0]
LIMITE = [3, 4, 4, 4, 4, 4, 4, 3]


def garantir_deepfilter() -> Path:
    if not DF_BIN.exists():
        DF_BIN.parent.mkdir(exist_ok=True)
        urllib.request.urlretrieve(DF_URL, DF_BIN)
    if hashlib.sha256(DF_BIN.read_bytes()).hexdigest() != DF_SHA:
        DF_BIN.unlink()
        raise SystemExit("deep-filter com hash inesperado; removido por segurança.")
    DF_BIN.chmod(0o755)
    return DF_BIN


def ler(p: Path) -> np.ndarray:
    return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(p), "-f", "f32le", "-ac", "1",
                                         "-ar", str(SR), "-"], check=True, capture_output=True).stdout, np.float32)


def gravar(x: np.ndarray, p: Path) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-",
                    "-c:a", "pcm_s16le", str(p)], input=x.astype(np.float32).tobytes(), check=True)


def espectro(x: np.ndarray, palavras: list[dict]) -> list[float]:
    m = np.zeros(len(x), bool)
    for w in palavras:
        m[int(w["s"] * SR):int(w["e"] * SR)] = True
    s, n = x[m], 4096
    P = np.mean([np.abs(np.fft.rfft(s[i:i + n] * np.hanning(n))) ** 2 for i in range(0, len(s) - n, n // 2)], 0)
    f = np.fft.rfftfreq(n, 1 / SR)
    tot = P[(f > 80) & (f < 12000)].sum()
    return [10 * np.log10(P[(f >= a) & (f < b)].sum() / tot + 1e-12) for a, b in BANDAS]


def cadeia_eq(medido: list[float]) -> tuple[str, list[float]]:
    ganhos = [float(np.clip(a - m, -l, l)) for a, m, l in zip(ALVO, medido, LIMITE)]
    ganhos = [g - np.mean(ganhos) for g in ganhos]  # só o equilíbrio muda; o volume vem depois
    filtros = [f"equalizer=f={np.sqrt(a * b):.0f}:t=o:w=1:g={g:.1f}" for (a, b), g in zip(BANDAS, ganhos) if abs(g) >= 0.5]
    return ",".join(filtros) or "anull", ganhos


def ajustar_eq(limpo: Path, ws: list[dict], passadas: int = 3) -> tuple[str, list[float]]:
    """EQ iterativa: aplica, mede o resultado e corrige de novo (filtros vizinhos se somam)."""
    base = np.array(espectro(ler(limpo), ws))
    ganhos = np.zeros(len(BANDAS))
    teste = OUT / "eq_teste.wav"
    for _ in range(passadas):
        medido = base if not ganhos.any() else np.array(espectro(ler(teste), ws))
        erro = np.array(ALVO) - medido
        erro -= erro.mean()
        ganhos = np.clip(ganhos + 0.7 * erro, -np.array(LIMITE), np.array(LIMITE))
        ganhos -= ganhos.mean()
        filtros = ",".join(f"equalizer=f={np.sqrt(a * b):.0f}:t=o:w=1:g={g:.2f}"
                           for (a, b), g in zip(BANDAS, ganhos) if abs(g) >= 0.3) or "anull"
        ffmpeg("-i", str(limpo), "-af", f"highpass=f=70,{filtros},{DINAMICA}", str(teste))
    teste.unlink()
    return filtros, list(ganhos)


def ponto_quieto(x: np.ndarray, a: float, b: float) -> float:
    """Instante de menor energia (janelas de 10 ms) entre a e b — onde o corte é inaudível."""
    a, b = max(a, 0), min(b, len(x) / SR)
    if b - a < 0.02:
        return (a + b) / 2
    h = int(0.01 * SR)
    seg = x[int(a * SR):int(b * SR)]
    e = [np.sum(seg[i:i + h] ** 2) for i in range(0, len(seg) - h, h // 2)]
    return a + (int(np.argmin(e)) * (h // 2) + h // 2) / SR


def trechos(x: np.ndarray, ws: list[dict]) -> tuple[list[tuple[float, float]], list[dict]]:
    """Trechos mantidos (em s da fonte) e registro do que saiu."""
    ini = ponto_quieto(x, ws[0]["s"] - 0.35, ws[0]["s"] - 0.04)
    manter, saiu, a = [], [], ini
    for w0, w1 in zip(ws, ws[1:]):
        gap = w1["s"] - w0["e"]
        if gap > PAUSA_MAX:
            c1 = ponto_quieto(x, w0["e"] + DEPOIS - 0.06, w0["e"] + DEPOIS + 0.08)
            c2 = ponto_quieto(x, w1["s"] - ANTES - 0.08, w1["s"] - ANTES + 0.06)
            manter.append((a, c1))
            saiu.append({"de": round(c1, 2), "ate": round(c2, 2), "motivo": f"pausa de {gap:.2f}s encurtada"})
            a = c2
    fim = ponto_quieto(x, ws[-1]["e"] + 0.05, ws[-1]["e"] + 0.4)
    manter.append((a, fim))
    return manter, saiu


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = garantir_deepfilter()
    tratada, original, palavras, cortes = [], [], [], []
    t_out = 0.0
    for k, fonte in enumerate(FONTES):
        ws = json.loads(Path(fonte["palavras"]).read_text())
        if "ate_palavra" in fonte:
            ws = ws[:[w["w"] for w in ws].index(fonte["ate_palavra"]) + 1]
        bruto = OUT / f"{fonte['id']}_bruto.wav"
        ffmpeg("-i", fonte["arquivo"], "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(bruto))
        # 2. DeepFilterNet com teto de 22 dB de atenuação: tira o ruído sem "lavar" a voz
        subprocess.run([str(df), "-D", "-a", "22", "-o", str(OUT / "df"), str(bruto)], check=True,
                       capture_output=True)
        limpo = OUT / "df" / bruto.name
        # 3–4. EQ por correspondência + de-esser + compressão moderada + normalização linear
        eq, ganhos = ajustar_eq(limpo, ws)
        cadeia = f"highpass=f=70,{eq},{DINAMICA}"
        fim_trat = OUT / f"{fonte['id']}_tratado.wav"
        ffmpeg("-i", str(limpo), "-af", loudnorm_linear(["-i", str(limpo)], cadeia, -16), "-ar", str(SR),
               str(fim_trat))
        xt, xo = ler(fim_trat), ler(bruto)
        manter, saiu = trechos(xt, ws)
        cortes.append({"fonte": fonte["id"], "eq_db": dict(zip([f"{a}-{b}" for a, b in BANDAS],
                                                             [round(g, 1) for g in ganhos])),
                       "mantido": [[round(a, 2), round(b, 2)] for a, b in manter], "removido": saiu})
        if k:
            gap = np.zeros(int(ENTRE_FONTES * SR), np.float32)
            tratada.append(gap); original.append(gap); t_out += ENTRE_FONTES
        rampa = np.linspace(0, 1, int(FADE * SR), dtype=np.float32)
        for a, b in manter:
            for dst, x in ((tratada, xt), (original, xo)):
                p = x[int(a * SR):int(b * SR)].copy()
                p[:len(rampa)] *= rampa
                p[-len(rampa):] *= rampa[::-1]
                dst.append(p)
            palavras += [{**w, "fonte": fonte["id"], "s": round(w["s"] - a + t_out, 3),
                          "e": round(w["e"] - a + t_out, 3)} for w in ws if a <= w["s"] < b]
            t_out += b - a
    gravar(np.concatenate(tratada), OUT / "voz_tratada.wav")
    gravar(np.concatenate(original), OUT / "voz_original_editada.wav")
    (OUT / "palavras.json").write_text(json.dumps(palavras, ensure_ascii=False, indent=0))
    (OUT / "cortes.json").write_text(json.dumps(cortes, ensure_ascii=False, indent=1))
    print(f"voz v2: {t_out:.2f}s, {len(palavras)} palavras")
    for c in cortes:
        print(f"  {c['fonte']}: EQ {c['eq_db']}")
        for r in c["removido"]:
            print(f"    − {r['de']:.2f}–{r['ate']:.2f}  {r['motivo']}")


if __name__ == "__main__":
    main()
