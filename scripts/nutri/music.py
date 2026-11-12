"""Troca a música de fundo do reel: nível padronizado e tempo forte alinhado a "estradiol".
Uso: python -I scripts/nutri/music.py <musica.mp3>   → public/nutri/full/musica.wav
"""
import json, os, subprocess, sys, warnings
import numpy as np, librosa
warnings.filterwarnings("ignore")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
d = json.load(open(os.path.join(ROOT, "src", "nutri", "reel.json")))
E, total = d["ev"]["estradiol"], d["totalFrames"] / d["fps"]
y, sr = librosa.load(sys.argv[1], sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
bt = librosa.frames_to_time(beats, sr=sr); st = librosa.onset.onset_strength(y=y, sr=sr)[beats]
phase = int(np.argmax([st[k::4].mean() for k in range(4)]))
offset = round(float([b for i, b in enumerate(bt) if i % 4 == phase and b >= E][0] - E), 3)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(offset), "-t", str(total + 0.5), "-i", sys.argv[1],
                "-af", "loudnorm=I=-16:TP=-2:LRA=11", "-ar", "48000", "-ac", "2",
                os.path.join(ROOT, "public", "nutri", "full", "musica.wav")], check=True)
print(f"{os.path.basename(sys.argv[1])}: {float(np.atleast_1d(tempo)[0]):.1f} BPM, começa em {offset}s do arquivo")
