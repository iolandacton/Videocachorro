"""Monta a prévia narrada de um vídeo do guia: vídeo + narração + legendas no visual do guia.
Uso: python3 scripts/tambaba/previa.py <nome>   (configurações em PREVIAS abaixo)"""
import subprocess, sys, tempfile, os
from pathlib import Path

V = Path("guia-tambaba/videos")
FONTE = "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"

PREVIAS = {
    # legendas: (início, fim, texto) em segundos da narração
    "pingpong": dict(
        video=V / "pingpong_animacao.mp4", lento=1.2, atraso_voz=0.4,
        vozes={"Rachel": [(0.0, 4.8, "Tire as duas partes do tampo,\numa de cada vez"),
                          (4.8, 9.15, "Guarde as duas em pé no suporte\npreto, encostado na parede"),
                          (9.15, 99, "Nunca deixe o tampo no chão")]},
    ),
}


def montar(nome, voz):
    cfg = PREVIAS[nome]
    audio = V / "voz" / f"{nome}_{voz}.mp3"
    dur_voz = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)]))
    total = dur_voz + cfg["atraso_voz"] + 0.7
    tmp = Path(tempfile.mkdtemp())
    filtros = [f"[0:v]setpts={cfg['lento']}*PTS,scale=1080:1920:flags=lanczos,tpad=stop_mode=clone:stop_duration=30,trim=0:{total:.2f},setsar=1[v0]"]
    ultimo = "v0"
    for i, (a, b, texto) in enumerate(cfg["vozes"][voz]):
        arq = tmp / f"leg{i}.txt"
        arq.write_text(texto)
        a2, b2 = a + cfg["atraso_voz"], min(b + cfg["atraso_voz"], total)
        filtros.append(
            f"[{ultimo}]drawtext=fontfile={FONTE}:textfile={arq}:fontsize=58:fontcolor=0x141210:line_spacing=14:"
            f"box=1:boxcolor=0xf8f5e3@0.94:boxborderw=34:x=(w-text_w)/2:y=h-text_h-300:"
            f"enable='between(t,{a2:.2f},{b2:.2f})'[v{i+1}]")
        ultimo = f"v{i+1}"
    saida = V / f"previa_{nome}_{voz}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(cfg["video"]), "-i", str(audio),
                    "-filter_complex", ";".join(filtros) + f";[1:a]adelay={int(cfg['atraso_voz']*1000)}:all=1,apad[a]",
                    "-map", f"[{ultimo}]", "-map", "[a]", "-t", f"{total:.2f}",
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", str(saida)], check=True)
    print("OK:", saida, f"{total:.1f}s")


if __name__ == "__main__":
    nome = sys.argv[1]
    for voz in PREVIAS[nome]["vozes"]:
        montar(nome, voz)
