"""Monta um tutorial narrado do guia a partir das filmagens reais.
Cada bloco = trechos de vídeo + uma frase narrada + legenda. O vídeo do bloco se estende
(congelando o último quadro) se a narração for mais longa.
Uso: python3 scripts/tambaba/tutorial.py <nome> <voz>
Requer as narrações em guia-tambaba/videos/voz/<nome>_<voz>_<n>.mp3 (scripts/tambaba/tts.ts)."""
import subprocess, sys, tempfile
from pathlib import Path

V = Path("guia-tambaba/videos")
D = V / "drive"
FONTE = "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf"
CLARO = "eq=gamma=1.45:contrast=1.12:saturation=1.15"
SUAVE = "SUAVE"  # câmera lenta com interpolação de quadros (para o timelapse)
FOTOS = Path("guia-tambaba/originais/fotos")

TUTORIAIS = {
    "telao": [
        dict(fala="Para ligar o telão, pegue o controle branco e baixe a tela.",
             legenda="Controle branco: baixe a tela",
             clipes=[("v01", 47.0, 50.0, 1), ("v01", 50.0, 58.5, 2)]),
        dict(fala="Depois, pegue o controle da Epson, chegue bem perto do projetor e aperte o botão azul. Quando ouvir um bipe, ele ligou.",
             legenda="Controle da Epson: bem perto do\nprojetor, aperte o botão azul",
             clipes=[("v12", 0.0, 2.0, 1), ("v12", 3.5, 11.5, 1.6), ("v12", 13.5, 17.5, 1)]),
        dict(fala="Com o controle pequeno preto, abra o YouTube ou o que quiser assistir.",
             legenda="Controle preto: YouTube e apps",
             clipes=[("v12", 26.5, 31.5, 1)]),
        dict(fala="Para o som sair nas caixas, toque no painel da parede até acender a luz verde.",
             legenda="Som: painel da parede,\nluz verde acesa",
             clipes=[("v12", 40.5, 46.0, 1)]),
        dict(fala="Pronto, é só aproveitar!", legenda="Pronto!", clipes=[("v12", 50.0, 52.8, 1)]),
    ],
    "chegada": [
        dict(fala="Depois de passar pela portaria, suba a ladeira até a rotatória.",
             legenda="Suba a ladeira até a rotatória",
             clipes=[("v13", 0.0, 2.0, 0.4, SUAVE)]),
        dict(fala="Na rotatória, vire à esquerda.", legenda="Na rotatória, vire à esquerda",
             clipes=[("v13", 2.0, 3.0, 0.4, SUAVE)]),
        dict(fala="Siga reto até o próximo retorno.", legenda="Siga reto até o próximo retorno",
             clipes=[("v13", 3.0, 5.2, 0.5, SUAVE)]),
        dict(fala="Faça o retorno, e a casa fica à sua direita.", legenda="Faça o retorno:\na casa fica à direita",
             clipes=[("v13", 5.2, 7.1, 0.45, SUAVE)]),
        dict(fala="É a casa com o maior jardim. Seja bem-vindo!", legenda="A casa com o maior jardim!",
             clipes=[("FOTO", "jardim.jpg", 4.0)]),
    ],
    "hidro": [
        dict(fala="Para ligar a hidromassagem, use o quadro de botões da área externa.",
             legenda="Quadro de botões da área externa",
             clipes=[("v01", 3.0, 7.0, 1, CLARO)]),
        dict(fala="O primeiro botão liga a cascata, e o segundo, o ozônio da piscina.",
             legenda="1º cascata · 2º ozônio da piscina",
             clipes=[("v01", 7.0, 12.0, 1, CLARO)]),
        dict(fala="O terceiro liga a hidromassagem. Gire para ligar, e gire de volta para desligar.",
             legenda="3º botão: hidromassagem",
             clipes=[("v01", 12.0, 13.0, 1, CLARO), ("v01", 13.0, 13.04, 1, CLARO, "anel_hidro.png")]),
    ],
}


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


def run(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def montar(nome, voz):
    tmp = Path(tempfile.mkdtemp())
    partes = []
    for i, b in enumerate(TUTORIAIS[nome]):
        # 1. vídeo do bloco
        lista = []
        for j, c in enumerate(b["clipes"]):
            out = tmp / f"b{i}c{j}.mp4"
            if c[0] == "FOTO":  # foto parada com leve aproximação
                _, arq, seg = c
                n = int(seg * 30)
                run(["-loop", "1", "-i", str(FOTOS / arq), "-vf",
                     f"scale=2160:3840:force_original_aspect_ratio=increase,crop=2160:3840,"
                     f"zoompan=z='1+0.08*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps=30,format=yuv420p",
                     "-frames:v", str(n), "-an", "-c:v", "libx264", "-crf", "18", str(out)])
                lista.append(out)
                continue
            src, a, z, vel = c[:4]
            filtro = c[4] if len(c) > 4 else "null"
            anel = c[5] if len(c) > 5 else None
            if filtro == SUAVE:
                vf = f"setpts=PTS/{vel},scale=1080:1920,minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,setsar=1"
            else:
                vf = f"{filtro},setpts=PTS/{vel},scale=1080:1920,fps=30,setsar=1"
            if anel:  # quadro congelado com destaque
                run(["-ss", str(a), "-i", str(D / f"{src}.mp4"), "-i", str(V / "fontes" / anel), "-frames:v", "1",
                     "-filter_complex", f"[0:v]{vf}[b];[b][1:v]overlay[v]", "-map", "[v]", str(tmp / "q.png")])
                run(["-loop", "1", "-t", "1", "-i", str(tmp / "q.png"), "-vf", "fps=30,format=yuv420p", "-an",
                     "-c:v", "libx264", "-crf", "18", str(out)])
            else:
                run(["-ss", str(a), "-t", str(z - a), "-i", str(D / f"{src}.mp4"), "-vf", vf, "-an",
                     "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", str(out)])
            lista.append(out)
        (tmp / f"b{i}.txt").write_text("".join(f"file '{p}'\n" for p in lista))
        bruto = tmp / f"b{i}_bruto.mp4"
        run(["-f", "concat", "-safe", "0", "-i", str(tmp / f"b{i}.txt"), "-c", "copy", str(bruto)])
        # 2. narração e duração do bloco
        audio = V / "voz" / f"{nome}_{voz}_{i}.mp3"
        da, dv = dur(audio) + 0.45, dur(bruto)
        total = max(da, dv)
        leg = tmp / f"leg{i}.txt"
        leg.write_text(b["legenda"])
        parte = tmp / f"p{i}.mp4"
        run(["-i", str(bruto), "-i", str(audio), "-filter_complex",
             f"[0:v]tpad=stop_mode=clone:stop_duration={total:.2f},trim=0:{total:.2f},"
             f"drawtext=fontfile={FONTE}:textfile={leg}:fontsize=60:fontcolor=0x141210:line_spacing=14:"
             f"box=1:boxcolor=0xf8f5e3@0.94:boxborderw=34:x=(w-text_w)/2:y=h-text_h-300[v];"
             f"[1:a]adelay=150:all=1,apad,atrim=0:{total:.2f}[a]",
             "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-ar", "44100", str(parte)])
        partes.append(parte)
    (tmp / "todas.txt").write_text("".join(f"file '{p}'\n" for p in partes))
    saida = V / f"previa_{nome}_{voz}.mp4"
    run(["-f", "concat", "-safe", "0", "-i", str(tmp / "todas.txt"), "-c", "copy", "-movflags", "+faststart", str(saida)])
    print("OK:", saida, f"{dur(saida):.1f}s")


if __name__ == "__main__":
    nome, voz = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3 and sys.argv[3] == "--falas":
        for i, b in enumerate(TUTORIAIS[nome]):
            print(f"{i}\t{b['fala']}")
    else:
        montar(nome, voz)
