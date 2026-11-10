#!/usr/bin/env python3
"""Áudio da versão completa (vídeo v3 + encerramento com assinatura): mesma voz, mesmos efeitos e a
mesma trilha lo-fi no mesmo nível da versão aprovada — a trilha continua sob a assinatura e termina em fade.
Uso: .venv/bin/python pipeline/audio_com_outro.py [segundos_do_encerramento]
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from arq_audio_v2 import NIVEL_MUSICA  # noqa: E402  (mesmo nível aprovado)
from editar import ffmpeg, mixar_musica  # noqa: E402
from musica import gerar, salvar  # noqa: E402

OUTRO = float(sys.argv[1]) if len(sys.argv) > 1 else 5.0
r = json.loads(Path("src/arquitetura/v2/final_v3.json").read_text())
total = round(r["duracao"] + OUTRO, 3)
D = Path("public/arq_v2/mix_completo"); D.mkdir(parents=True, exist_ok=True)
ffmpeg("-i", "public/arq_v2/mix/voz_sfx.wav", "-af", f"apad,atrim=0:{total}", "-ar", "48000", str(D / "voz_sfx.wav"))
salvar(gerar(total, 84, 3), D / "trilha_lofi.wav")  # mesma trilha (bpm 84, seed 3), só mais longa
mixar_musica(D / "voz_sfx.wav", D / "trilha_lofi.wav", D / "audio.wav", total, NIVEL_MUSICA, r["lufs"])
print(D / "audio.wav", total)
