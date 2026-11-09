#!/usr/bin/env python3
"""Áudio de um roteiro de arquitetura: voz tratada + efeitos sutis + música com ducking.

Lê o JSON do roteiro (src/arquitetura/*.json) e grava public/arq/<nome>/audio.wav.
"audio" pode ser um trecho ou uma lista de trechos {arquivo, inicio, fim, em}: cada trecho
recebe exatamente o mesmo tratamento de voz e é posicionado no tempo "em" do vídeo.
Uso: .venv/bin/python pipeline/arq_audio.py src/arquitetura/final.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from editar import ffmpeg, limpar_voz, mixar_musica  # noqa: E402
from musica import gerar, salvar  # noqa: E402

# Efeitos sintetizados (sem bibliotecas de terceiros). Volumes já discretos.
SFX = {
    "clique": ("aevalsrc='0.55*sin(2*PI*2600*t)*exp(-t*95)+0.2*sin(2*PI*5300*t)*exp(-t*160)':d=0.07:s=48000",
               "volume=-14dB"),
    "whoosh": ("anoisesrc=color=pink:d=0.75:a=0.8:seed=5:r=48000",
               "highpass=f=350,lowpass=f=4200,volume='pow(sin(PI*t/0.75),3)':eval=frame,volume=-17dB"),
    "ar": ("anoisesrc=color=white:d=0.9:a=0.6:seed=9:r=48000",
           "highpass=f=2500,lowpass=f=9000,volume='min(t/0.35,1)*exp(-max(t-0.35,0)*5)':eval=frame,volume=-24dB"),
}


def faixa(eventos: list[tuple[Path | str, float]], dur: float, destino: Path, lavfi: bool = False) -> None:
    """Posiciona cada fonte no seu tempo e soma tudo numa faixa estéreo de duração fixa."""
    entradas, filtros = [], []
    for i, (src, t) in enumerate(eventos):
        if lavfi:
            fonte, fx = SFX[src]
            entradas += ["-f", "lavfi", "-i", fonte]
            pre = f"{fx},"
        else:
            entradas += ["-i", str(src)]
            pre = ""
        ms = int(t * 1000)
        filtros.append(f"[{i}:a]{pre}aformat=sample_rates=48000:channel_layouts=stereo,adelay={ms}|{ms}[s{i}]")
    n = len(eventos)
    fc = ";".join(filtros) + ";" + "".join(f"[s{i}]" for i in range(n)) + \
        f"amix=inputs={n}:normalize=0,apad,atrim=0:{dur}"
    ffmpeg(*entradas, "-filter_complex", fc, "-ar", "48000", str(destino))


def main(roteiro: Path) -> None:
    r = json.loads(roteiro.read_text(encoding="utf-8"))
    out = Path("public/arq") / roteiro.stem
    out.mkdir(parents=True, exist_ok=True)
    dur = r["duracao"]
    trechos = r["audio"] if isinstance(r["audio"], list) else [{**r["audio"], "em": 0}]

    vozes = []
    for i, a in enumerate(trechos):
        corte, limpa = out / f"corte_{i}.wav", out / f"voz_{i}.wav"
        ffmpeg("-ss", str(a["inicio"]), "-to", str(a["fim"]), "-i", a["arquivo"], "-vn", "-ac", "2",
               "-ar", "48000", str(corte))
        limpar_voz(corte, limpa, -16)  # mesmo tratamento e mesmo nível para todo trecho
        corte.unlink()
        vozes.append((limpa, a["em"]))
    faixa(vozes, dur, out / "voz.wav")
    faixa([(e["tipo"], e["t"]) for e in r["sfx"]], dur, out / "sfx.wav", lavfi=True)

    ffmpeg("-i", str(out / "voz.wav"), "-i", str(out / "sfx.wav"), "-filter_complex",
           "[0:a][1:a]amix=inputs=2:normalize=0:duration=first", "-ar", "48000", str(out / "voz_sfx.wav"))
    salvar(gerar(dur, 80, 7), out / "musica.wav")
    # voz e música mantêm a proporção; "lufs" define o volume final (mais negativo = mais baixo)
    mixar_musica(out / "voz_sfx.wav", out / "musica.wav", out / "audio.wav", dur, -31, r.get("lufs", -14))
    for f in ["voz_sfx.wav", *[v.name for v, _ in vozes]]:
        (out / f).unlink()
    print(out / "audio.wav")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
