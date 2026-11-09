#!/usr/bin/env python3
"""Edição automática local: áudio limpo, estabilização, cor, legendas PT-BR e export.

Tudo roda na máquina (FFmpeg + faster-whisper). Não chama APIs pagas.

Uso:
  .venv/bin/python pipeline/editar.py VIDEO [--modelo medium] [--res 1080|4k]
                                            [--srt revisada.srt] [--sem-estabilizar]
Saída em out/<nome>/: final.mp4, legendas.srt, transcricao.json, comparacao.jpg
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Cor "natural": recupera realces estourados, dá contraste suave, aquece a pele.
GRADE = (
    "curves=all='0/0 0.25/0.235 0.5/0.5 0.75/0.765 0.92/0.9 1/0.955',"
    "eq=contrast=1.04:saturation=1.18:gamma=0.98,"
    "colorbalance=rs=0.01:bs=-0.012:rm=0.015:bm=-0.015"
)
# Legenda discreta: Inter, branca, contorno fino, terço inferior acima da UI do Reels.
ASS_HEADER = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Discreta,Inter,52,&H00FFFFFF,&H00FFFFFF,&H70000000,&H64000000,0,0,0,0,100,100,0,0,1,2.2,1.2,2,90,90,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
MAX_CHARS, MAX_DUR, PAUSA = 34, 2.8, 0.45
# Download HTTP simples do modelo (o protocolo Xet usa hosts que o proxy pode cortar).
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw)


def ffmpeg(*args: str, **kw) -> str:
    return run(["ffmpeg", "-hide_banner", "-nostdin", "-y", *args], **kw).stderr


def probe(path: Path) -> dict:
    out = run(["ffprobe", "-v", "error", "-print_format", "json", "-show_streams",
               "-show_format", str(path)]).stdout
    return json.loads(out)


# ---------- 1. Áudio ----------
def loudnorm_linear(entrada: list[str], cadeia: str, alvo: float) -> str:
    """Devolve a cadeia + loudnorm em modo linear (ganho fixo: não levanta o ruído das pausas)."""
    medida = ffmpeg(*entrada, "-af", f"{cadeia},loudnorm=I={alvo}:TP=-1.5:LRA=11:print_format=json",
                    "-f", "null", "-")
    j = json.loads(medida[medida.rindex("{"):medida.rindex("}") + 1])
    return (f"{cadeia},loudnorm=I={alvo}:TP=-1.5:LRA=11:measured_I={j['input_i']}:"
            f"measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
            f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")


def limpar_voz(src: Path, dst: Path, alvo: float) -> dict:
    """Ruído de banda larga (afftdn) + ruído de sala (anlmdn) + EQ de clareza + compressão
    leve + gate DEPOIS da compressão (silencia reverberação/fundo entre frases)."""
    stats = ffmpeg("-i", str(src), "-vn", "-af", "astats=metadata=0", "-f", "null", "-")
    m = re.findall(r"Noise floor dB: (-?[\d.]+)", stats)
    piso = max(-70.0, min(-25.0, float(m[-1]) - 10)) if m else -50.0
    cadeia = (f"highpass=f=90,afftdn=nr=12:nf={piso:.0f}:tn=1,anlmdn=s=3:p=0.002:r=0.006,"
              "equalizer=f=280:t=q:w=1.2:g=-2,equalizer=f=3200:t=q:w=1.5:g=2,"
              "acompressor=threshold=-22dB:ratio=2.5:attack=8:release=160:makeup=2,"
              "agate=threshold=0.03:ratio=3:range=0.1:attack=5:release=300:knee=4")
    ffmpeg("-i", str(src), "-vn", "-af", loudnorm_linear(["-i", str(src), "-vn"], cadeia, alvo),
           "-ar", "48000", "-ac", "2", str(dst))
    return {"piso_ruido_db": piso}


def mixar_musica(voz: Path, musica: Path, dst: Path, dur: float, nivel_lufs: float) -> None:
    """Música em loop sob a voz, com ducking (abaixa sozinha quando há fala), fades e limiter."""
    ajuste = nivel_lufs - lufs(musica)
    fc = (f"[1:a]volume={ajuste:.2f}dB,atrim=0:{dur:.3f},afade=t=in:d=1,"
          f"afade=t=out:st={max(dur - 1.8, 0):.3f}:d=1.8,aformat=sample_rates=48000:channel_layouts=stereo[m];"
          "[0:a]asplit=2[v][sc];"
          "[m][sc]sidechaincompress=threshold=0.05:ratio=2:attack=40:release=600:knee=4[md];"
          "[v][md]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.84:level=false")
    tmp = dst.with_suffix(".tmp.wav")
    ffmpeg("-i", str(voz), "-stream_loop", "-1", "-i", str(musica), "-filter_complex", fc,
           "-ar", "48000", str(tmp))
    ffmpeg("-i", str(tmp), "-af", loudnorm_linear(["-i", str(tmp)], "anull", -14), "-ar", "48000",
           str(dst))
    tmp.unlink()


# ---------- 2. Estabilização ----------
def detectar_tremor(src: Path, trf: Path) -> None:
    ffmpeg("-i", str(src), "-vf", f"vidstabdetect=shakiness=5:accuracy=15:result={trf.name}",
           "-f", "null", "-", cwd=trf.parent)


# ---------- 3. Transcrição e legendas ----------
def transcrever(audio: Path, modelo: str) -> list[dict]:
    import numpy as np
    from faster_whisper import WhisperModel

    # Decodifica com o FFmpeg (16 kHz mono) em vez do PyAV: evita incompatibilidade de versões.
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(audio), "-f", "f32le",
                          "-ac", "1", "-ar", "16000", "-"], check=True, capture_output=True).stdout
    wm = WhisperModel(modelo, device="cpu", compute_type="int8")
    segs, _ = wm.transcribe(np.frombuffer(pcm, np.float32), language="pt", word_timestamps=True,
                            vad_filter=True, beam_size=5)
    return [{"w": w.word.strip(), "s": round(w.start, 3), "e": round(w.end, 3)}
            for s in segs for w in (s.words or []) if w.word.strip()]


def agrupar(palavras: list[dict]) -> list[dict]:
    """Junta palavras em blocos curtos: quebra em pausa, pontuação, tamanho ou duração."""
    cues, cur = [], []
    for i, p in enumerate(palavras):
        cur.append(p)
        texto = " ".join(x["w"] for x in cur)
        prox = palavras[i + 1] if i + 1 < len(palavras) else None
        fim = (prox is None or prox["s"] - p["e"] > PAUSA or p["w"][-1] in ".?!"
               or len(texto) + 1 + len(prox["w"]) > MAX_CHARS
               or prox["e"] - cur[0]["s"] > MAX_DUR)
        if fim:
            cues.append({"s": cur[0]["s"], "e": p["e"], "t": texto})
            cur = []
    for a, b in zip(cues, cues[1:]):  # segura a legenda até a próxima (sem piscar)
        if b["s"] - a["e"] < 0.3:
            a["e"] = b["s"]
    return cues


def _ts(t: float, sep: str = ",", cs: bool = False) -> str:
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    if cs:
        return f"{int(h)}:{int(m):02d}:{s:05.2f}"
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}{sep}{int(round((s % 1) * 1000)):03d}"


def salvar_srt(cues: list[dict], path: Path) -> None:
    path.write_text("".join(f"{i}\n{_ts(c['s'])} --> {_ts(c['e'])}\n{c['t']}\n\n"
                            for i, c in enumerate(cues, 1)), encoding="utf-8")


def ler_srt(path: Path) -> list[dict]:
    def seg(x: str) -> float:
        h, m, s = x.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    cues = []
    for bloco in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
        linhas = bloco.strip().splitlines()
        if len(linhas) >= 3 and "-->" in linhas[1]:
            a, b = [x.strip() for x in linhas[1].split("-->")]
            cues.append({"s": seg(a), "e": seg(b), "t": " ".join(linhas[2:])})
    return cues


def salvar_ass(cues: list[dict], path: Path) -> None:
    ev = "".join(f"Dialogue: 0,{_ts(c['s'], cs=True)},{_ts(c['e'], cs=True)},Discreta,,0,0,0,,"
                 f"{{\\fad(80,80)}}{c['t']}\n" for c in cues)
    path.write_text(ASS_HEADER + ev, encoding="utf-8")


# ---------- 4. Verificação ----------
def lufs(path: Path) -> float:
    r = ffmpeg("-i", str(path), "-af", "ebur128", "-f", "null", "-")
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--modelo", default="medium", help="tiny|base|small|medium|large-v3")
    ap.add_argument("--res", choices=["1080", "4k"], default="1080")
    ap.add_argument("--srt", type=Path, help="usar legenda revisada em vez de transcrever")
    ap.add_argument("--sem-estabilizar", action="store_true")
    ap.add_argument("--sem-legendas", action="store_true")
    ap.add_argument("--musica", default="gerar", help="gerar | nenhuma | caminho de um arquivo de áudio")
    ap.add_argument("--nivel-musica", type=float, default=-31,
                    help="loudness da música antes do ducking (LUFS); voz fica em -16")
    a = ap.parse_args()

    src = a.video.resolve()
    v = next(s for s in probe(src)["streams"] if s["codec_type"] == "video")
    vertical = int(v["height"]) >= int(v["width"])
    out = Path("out") / re.sub(r"[^\w-]+", "_", src.stem)
    out.mkdir(parents=True, exist_ok=True)
    print(f"• Fonte: {v['width']}x{v['height']} → {out}/")

    dur = float(probe(src)["format"]["duration"])
    com_musica = a.musica != "nenhuma"
    print("• Voz: redução de ruído, EQ, compressão e gate")
    info = limpar_voz(src, out / "audio_limpo.wav", -16 if com_musica else -14)
    audio_final = "audio_limpo.wav"
    if com_musica:
        if a.musica == "gerar":
            from musica import gerar, salvar
            trilha = out / "musica.wav"
            salvar(gerar(dur, 84, 3), trilha)
            print("• Música: trilha lo-fi original gerada")
        else:
            trilha = Path(a.musica).resolve()
            print(f"• Música: {trilha.name}")
        mixar_musica(out / "audio_limpo.wav", trilha, out / "audio_final.wav", dur, a.nivel_musica)
        audio_final = "audio_final.wav"

    vf = []
    if not a.sem_estabilizar:
        print("• Estabilização: analisando tremor")
        detectar_tremor(src, out / "tremor.trf")
        vf += ["vidstabtransform=input=tremor.trf:smoothing=12:optzoom=1:interpol=bicubic",
               "unsharp=5:5:0.4:3:3:0.2"]
    vf.append(GRADE)
    if a.res == "4k":
        vf.append(f"scale={'2160:3840' if vertical else '3840:2160'}:flags=lanczos")

    if not a.sem_legendas:
        if a.srt:
            cues = ler_srt(a.srt.resolve())
            print(f"• Legendas: usando {a.srt} ({len(cues)} blocos)")
        else:
            print(f"• Transcrição: faster-whisper '{a.modelo}' (CPU, PT-BR)")
            palavras = transcrever(out / "audio_limpo.wav", a.modelo)
            (out / "transcricao.json").write_text(
                json.dumps(palavras, ensure_ascii=False, indent=1), encoding="utf-8")
            cues = agrupar(palavras)
            salvar_srt(cues, out / "legendas.srt")
            print(f"  texto: {' '.join(c['t'] for c in cues)}")
        salvar_ass(cues, out / "legendas.ass")
        vf.append("ass=legendas.ass")

    print(f"• Export {a.res}: x264 CRF 17, AAC 192k")
    ffmpeg("-i", str(src), "-i", audio_final, "-map", "0:v:0", "-map", "1:a:0",
           "-vf", ",".join(vf), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
           "-profile:v", "high", "-pix_fmt", "yuv420p", "-color_primaries", "bt709",
           "-color_trc", "bt709", "-colorspace", "bt709", "-movflags", "+faststart",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "final.mp4", cwd=out)

    meio = float(probe(out / "final.mp4")["format"]["duration"]) / 2
    ffmpeg("-ss", f"{meio:.2f}", "-i", str(src), "-ss", f"{meio:.2f}", "-i", str(out / "final.mp4"),
           "-filter_complex", "[0:v]scale=540:-2[a];[1:v]scale=540:-2[b];[a][b]hstack",
           "-frames:v", "1", str(out / "comparacao.jpg"))

    fv = next(s for s in probe(out / "final.mp4")["streams"] if s["codec_type"] == "video")
    print(f"✓ {out}/final.mp4  {fv['width']}x{fv['height']}  "
          f"loudness final {lufs(out / 'final.mp4'):.1f} LUFS  (piso de ruído {info['piso_ruido_db']:.0f} dB)")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as e:
        sys.exit(f"Falhou: {' '.join(e.cmd[:6])}…\n{e.stderr[-1500:]}")
