#!/usr/bin/env python3
"""Oficina Sete — aplica o "gimbal virtual" nos ORIGINAIS 4K e gera os intermediários 1080x1920.
Para cada quadro: uma única transformação GLOBAL (desloca + gira + aproxima a janela inteira; bicúbica) do
original 2160x3840 para 1620x2880, depois redução lanczos para 1080x1920 e a MESMA cor aprovada.
Como a janela tem sempre mais pixels que a saída, não há ampliação: a nitidez do original é mantida.
Sem deformação localizada, sem IA, sem interpolação de quadros.
Uso: python3 scripts/oficina/gimbal_aplicar.py [--cor] TAKE[:lento] ...      (python do sistema: usa Pillow)
     saída: public/oficina/gimbal/<TAKE>[_lento].mp4
     --cor: colorimetria v8 (scripts/oficina/cor.py: recupera as altas luzes do original de 10 bits, mais
            densidade e ombro suave) no lugar da cor antiga; saída em public/oficina/grade/
"""
import json, math, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import cor as COR

# --cor (perfil v8, saída em grade/) ou --cor=v9 (perfil v9, saída em grade9/)
PERFIL = next((a.partition("=")[2] or "v8" for a in sys.argv if a.startswith("--cor")), None)
NOVA_COR = PERFIL is not None

SW, SH, OW, OH = 2160, 3840, 1620, 2880
D = Path("public/oficina/gimbal")
SAIDA = Path("public/oficina/grade" + ("" if PERFIL == "v8" else PERFIL[1:])) if NOVA_COR else D
SAIDA.mkdir(parents=True, exist_ok=True)
NEUTRO = json.load(open("public/oficina/analise/neutros.json"))
ALVO = (206.0, 195.0, 190.0)
LOOK = "curves=all='0/0 0.25/0.24 0.5/0.51 0.8/0.82 0.94/0.93 1/0.97',eq=contrast=1.03:saturation=0.95"


def aplicar(item):
    take, _, modo = item.partition(":")
    lento = modo == "lento"
    nome = take + ("_lento" if lento else "")
    J = json.load(open(D / f"{nome}_janela.json"))
    r, g, b = NEUTRO[take]
    ganho = [max(0.85, min(1.25, ALVO[i] / v)) for i, v in enumerate((r, g, b))]
    cor = f"colorchannelmixer=rr={ganho[0]:.4f}:gg={ganho[1]:.4f}:bb={ganho[2]:.4f}"
    dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", f"public/oficina/camera/{take}.MP4", "-an", "-vf",
                            ("" if lento else "select='not(mod(n\\,2))',") +
                            (COR.filtro(take, PERFIL) + "," if NOVA_COR else "") +
                            "scale=iw:ih:flags=bicubic+accurate_rnd+full_chroma_int:sws_dither=ed,format=rgb24",
                            "-vsync", "0", "-f", "rawvideo", "-"], stdout=subprocess.PIPE, bufsize=SW * SH * 3)
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}",
                            "-r", "30000/1001", "-i", "-", "-vf",
                            "scale=1080:1920:flags=lanczos+accurate_rnd+full_chroma_int," +
                            ("" if NOVA_COR else f"{cor},{LOOK},") + "format=yuv420p",
                            "-c:v", "libx264", "-preset", "veryfast", "-qp", "0", "-pix_fmt", "yuv420p",
                            str(SAIDA / f"{nome}.mp4")], stdin=subprocess.PIPE)
    n = 0
    while n < len(J["cx"]):
        raw = dec.stdout.read(SW * SH * 3)
        if len(raw) < SW * SH * 3:
            break
        k = SW / J["zoom"][n] * (1 + J["esc"][n]) / OW          # px do original por px de saída
        a = math.radians(J["ang"][n]); c, s = math.cos(a) * k, math.sin(a) * k
        cx, cy = J["cx"][n], J["cy"][n]
        # saída (u,v) → original: p = centro + k·R(a)·(u − OW/2, v − OH/2)
        co = (c, -s, cx - c * OW / 2 + s * OH / 2, s, c, cy - s * OW / 2 - c * OH / 2)
        for u, v in ((0, 0), (OW, 0), (0, OH), (OW, OH)):        # a janela nunca sai do quadro original
            x, y = co[0] * u + co[1] * v + co[2], co[3] * u + co[4] * v + co[5]
            assert -1.5 <= x <= SW + 1.5 and -1.5 <= y <= SH + 1.5, (nome, n, x, y)
        im = Image.frombuffer("RGB", (SW, SH), raw, "raw", "RGB", 0, 1)
        enc.stdin.write(im.transform((OW, OH), Image.AFFINE, co, resample=Image.BICUBIC).tobytes())
        n += 1
    enc.stdin.close(); enc.wait(); dec.kill()
    return f"{nome}: {n} quadros"


if __name__ == "__main__":
    with ThreadPoolExecutor(3) as ex:
        for r in ex.map(aplicar, [a for a in sys.argv[1:] if not a.startswith("--")]):
            print(r, flush=True)
