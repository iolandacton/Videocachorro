#!/usr/bin/env python3
"""Mix v2 (cópia de trabalho; o arq_audio.py da versão aprovada não é alterado).

voz tratada e editada (pipeline/voz_v2.py) + efeitos sutis + trilha lo-fi do primeiro vídeo (C6282)
com ducking suave. (pipeline/musica_indie.py continua disponível como alternativa.)
Uso: .venv/bin/python pipeline/arq_audio_v2.py  →  public/arq_v2/mix/audio.wav
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from arq_audio import faixa  # noqa: E402  (mesmos efeitos sintetizados da versão aprovada)
from editar import ffmpeg, mixar_musica  # noqa: E402
from musica import gerar, salvar  # noqa: E402  (mesma trilha do vídeo de 6 s)

MIX = Path("public/arq_v2/mix")
NIVEL_MUSICA = -30.5  # LUFS da trilha antes do ducking: ~19 dB abaixo da voz na fala (2 dB abaixo do vídeo de 6 s)


def main() -> None:
    r = json.loads(Path("src/arquitetura/v2/final_v2.json").read_text())
    dur = r["duracao"]
    MIX.mkdir(parents=True, exist_ok=True)
    voz = MIX / "voz.wav"
    ffmpeg("-i", "public/arq_v2/voz/voz_tratada.wav", "-af", f"aformat=channel_layouts=stereo,apad,atrim=0:{dur}",
           "-ar", "48000", str(voz))
    faixa([(e["tipo"], e["t"]) for e in r["sfx"]], dur, MIX / "sfx.wav", lavfi=True)
    ffmpeg("-i", str(voz), "-i", str(MIX / "sfx.wav"), "-filter_complex",
           "[0:a][1:a]amix=inputs=2:normalize=0:duration=first", "-ar", "48000", str(MIX / "voz_sfx.wav"))
    salvar(gerar(dur, 84, 3), MIX / "trilha_lofi.wav")  # bpm 84, seed 3 = trilha do vídeo de 6 s
    mixar_musica(MIX / "voz_sfx.wav", MIX / "trilha_lofi.wav", MIX / "audio.wav", dur, NIVEL_MUSICA, r["lufs"])
    print(MIX / "audio.wav")


if __name__ == "__main__":
    main()
