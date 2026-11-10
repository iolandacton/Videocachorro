#!/usr/bin/env python3
"""Oficina Sete — montagem: voz tratada + cortes + roteiro (cenas, apoios, legendas, rótulos) + trilha.

1. Voz de cada tomada do protagonista: DeepFilterNet (limite de atenuação) → EQ por correspondência
   (mesmo timbre entre tomadas) → de-esser + compressão leve → normalização.
2. Cortes: trechos escolhidos (por frase), início/fim no ponto de menor energia; pausas longas removidas.
3. Roteiro para o Remotion: protagonista como base, apoios ancorados nas frases que ilustram, legendas
   curtas no estilo da referência e rótulos de detalhe (só com termos ditos na fala).
4. Trilha lo-fi discreta com ducking; volume final −16 LUFS.
Uso: .venv/bin/python pipeline/oficina.py
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import voz_v2 as V  # noqa: E402
from editar import ffmpeg, loudnorm_linear, mixar_musica  # noqa: E402
from musica import gerar, salvar  # noqa: E402

SR = V.SR
D = Path("public/oficina/voz"); D.mkdir(parents=True, exist_ok=True)
V.OUT = D  # arquivos temporários da EQ ficam aqui
T = json.loads(Path("public/oficina/analise/transcricoes.json").read_text())
# correções de leitura (o que o Whisper grafou → o que foi dito); dúvidas marcadas para a cliente confirmar
GRAFIA = {"-cavalho": "carvalho", "-malva,": "malva,", "revertimento": "revestimento", "A?": "A"}

# Trechos do protagonista, na ordem do vídeo: (tomada, primeiras palavras, últimas palavras)
TRECHOS = [
    ("C6211", "Sabe aquela", "o contraste."),
    ("C6211", "Aqui a gente tem", "nesse projeto."),
    ("C6211", "A gente tem a esquadria", "caixa de madeira."),
    ("C6211", "E o projeto pediu", "porta usinada,"),
    ("C6212", "Então aqui a gente", "padrão -cavalho -malva,"),
    ("C6212", "e são trilhos,", "acho fundamental."),
    ("C6212", "A gente diminui", "raja única."),
    ("C6214", "Marcenaria detalhe,", "próximo projeto."),
]
GAP_MESMA, GAP_OUTRA = 0.24, 0.32
# fala ocupa ~83% do vídeo: trilha mais presente que nos vídeos do Yuri (~13 dB abaixo da voz durante a fala)
NIVEL_MUSICA = -24.5  # respiro entre trechos (mesma tomada / tomadas diferentes)
TOMADAS = sorted({t[0] for t in TRECHOS})


def limpa(w: str) -> str:
    return re.sub(r"[^\wà-ú]", "", w.lower())


def achar(ws: list[dict], frase: str, a_partir: int = 0) -> tuple[int, int]:
    alvo = [limpa(x) for x in frase.split()]
    for i in range(a_partir, len(ws) - len(alvo) + 1):
        if [limpa(w["w"]) for w in ws[i:i + len(alvo)]] == alvo:
            return i, i + len(alvo) - 1
    raise SystemExit(f"não achei {frase!r}")


def tratar_vozes() -> dict[str, np.ndarray]:
    df = V.garantir_deepfilter()
    out = {}
    for k in TOMADAS:
        bruto = D / f"{k}_bruto.wav"
        ffmpeg("-i", T[k]["arquivo"], "-vn", "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", str(bruto))
        subprocess.run([str(df), "-D", "-a", "20", "-o", str(D / "df"), str(bruto)], check=True, capture_output=True)
        limpo = D / "df" / bruto.name
        eq, ganhos = V.ajustar_eq(limpo, T[k]["palavras"])
        cadeia = f"highpass=f=70,{eq},{V.DINAMICA}"
        trat = D / f"{k}_tratado.wav"
        ffmpeg("-i", str(limpo), "-af", loudnorm_linear(["-i", str(limpo)], cadeia, -16), "-ar", str(SR), str(trat))
        out[k] = V.ler(trat)
        print(f"  voz {k}: EQ {[round(float(g), 1) for g in ganhos]}")
    return out


def main() -> None:
    vozes = tratar_vozes()
    partes, palavras, cenas_base, t_out = [], [], [], 0.0
    rampa = np.linspace(0, 1, int(0.012 * SR), dtype=np.float32)
    anterior = None
    for idx, (k, ini, fim) in enumerate(TRECHOS):
        ws = T[k]["palavras"]
        i0, _ = achar(ws, ini)
        _, i1 = achar(ws, fim, i0)
        x = vozes[k]
        a = V.ponto_quieto(x, ws[i0]["s"] - 0.30, ws[i0]["s"] - 0.03)
        b = V.ponto_quieto(x, ws[i1]["e"] + 0.04, ws[i1]["e"] + 0.32)
        if anterior is not None:
            g = GAP_MESMA if anterior == k else GAP_OUTRA
            partes.append(np.zeros(int(g * SR), np.float32)); t_out += g
        p = x[int(a * SR):int(b * SR)].copy(); p[:len(rampa)] *= rampa; p[-len(rampa):] *= rampa[::-1]
        partes.append(p)
        cenas_base.append({"video": f"oficina/proc/{k}.mp4", "inicioVideo": round(a, 3), "de": round(t_out, 3),
                           "tomada": k, "trecho": idx})
        for w in ws[i0:i1 + 1]:
            palavras.append({"w": GRAFIA.get(w["w"], w["w"]), "s": round(w["s"] - a + t_out, 3),
                             "e": round(w["e"] - a + t_out, 3), "trecho": idx})
        t_out += b - a
        anterior = k
    voz = np.concatenate(partes)
    V.gravar(voz, D / "voz_editada.wav")
    dur = round(len(voz) / SR + 0.9, 2)   # respiro final para o encerramento
    for c0, c1 in zip(cenas_base, cenas_base[1:]):
        c0["ate"] = c1["de"]
    cenas_base[-1]["ate"] = dur
    # pulo de imagem entre trechos da mesma tomada: dissolve curto (onde não houver apoio cobrindo)
    for c0, c1 in zip(cenas_base, cenas_base[1:]):
        c1["entrada"] = "dissolve" if c0["tomada"] == c1["tomada"] else "corte"

    def T_(frase, n=0):
        alvo = [limpa(x) for x in frase.split()]
        ach = [i for i in range(len(palavras) - len(alvo) + 1) if [limpa(w["w"]) for w in palavras[i:i + len(alvo)]] == alvo]
        return palavras[ach[n]]["s"], palavras[ach[n] + len(alvo) - 1]["e"]

    fim_trecho = {c["trecho"]: c["ate"] for c in cenas_base}
    # Apoios (≈20% do tempo), cada um ilustrando exatamente o que está sendo dito; o áudio do apoio é mudo.
    apoios = [
        {"video": "oficina/proc/C6218.mp4", "inicioVideo": 0.0, "de": T_("Olha só")[0] - 0.1,
         "ate": T_("Olha só")[0] - 0.1 + 2.45},                                    # o painel ripado (a solução)
        {"video": "oficina/proc/C6222.mp4", "inicioVideo": 0.0,
         "de": max(T_("essa porta usinada")[0] - 0.05, fim_trecho[3] + 0.15 - 1.98), "ate": fim_trecho[3] + 0.15,
         "rotulo": ["PORTA", "USINADA"]},                                          # cobre a troca de tomada
        {"video": "oficina/proc/C6220.mp4", "inicioVideo": 0.6, "de": T_("num padrão")[0] - 0.1,
         "ate": max(T_("carvalho malva,")[1] + 0.2, fim_trecho[4] + 0.12)},        # o acabamento das ripas
        {"video": "oficina/proc/C6219.mp4", "inicioVideo": 0.3, "de": T_("Lá em cima")[0] - 0.1,
         "ate": T_("o fitamento,")[1] + 0.25, "rotulo": ["FITAMENTO", "NO TRILHO"]},  # topo da porta e trilho
        {"video": "oficina/proc/C6221.mp4", "inicioVideo": 0.0, "de": T_("mas assim")[0] - 0.1,
         "ate": fim_trecho[6], "saida": "corte", "rotulo": ["PADRÃO DE", "RAJA ÚNICA"]},  # ripas → fechamento
    ]
    for a in apoios:
        a["de"], a["ate"] = round(a["de"], 3), round(a["ate"], 3)

    # Legendas: cada frase (pontuação, pausa > 0,3 s ou troca de trecho) é dividida em linhas EQUILIBRADAS
    # de até ~30 caracteres — nunca palavra solta; sem muletas ("tá"); minúsculas como na referência.
    MULETAS = {"tá", "tá?", "tá,"}
    uteis = [w for w in palavras if w["w"].lower() not in MULETAS]
    frases, cur = [], []
    for i, w in enumerate(uteis):
        cur.append(w)
        prox = uteis[i + 1] if i + 1 < len(uteis) else None
        if prox is None or prox["trecho"] != w["trecho"] or w["w"][-1] in ".,?!:" or prox["s"] - w["e"] > 0.3:
            frases.append(cur); cur = []
    # junta frase de uma palavra só (ex.: "branca,") à anterior quando couber numa linha
    juntas = []
    for f in frases:
        if len(f) == 1 and juntas and juntas[-1][-1]["trecho"] == f[0]["trecho"] and \
                len(" ".join(x["w"] for x in juntas[-1] + f)) <= 50:
            juntas[-1] = juntas[-1] + f
        else:
            juntas.append(f)
    LIGACAO = {"a", "o", "as", "os", "e", "de", "da", "do", "das", "dos", "no", "na", "nos", "nas", "um", "uma",
               "que", "com", "em", "por", "ter", "pra", "para", "se", "é", "foi"}
    from itertools import combinations
    def custo(linhas):
        L = [len(" ".join(x["w"] for x in l)) for l in linhas]
        c = max(L) + 0.3 * (max(L) - min(L))
        for l in linhas[:-1]:
            if limpa(l[-1]["w"]) in LIGACAO: c += 25
        c += sum(40 for l in linhas if len(l) == 1)
        c += sum(30 for l in linhas if l[-1]["e"] - l[0]["s"] < 0.6)   # rápido demais para ler
        return c
    blocos = []
    for f in juntas:
        total = len(" ".join(x["w"] for x in f))
        if total <= 34 or len(f) < 4:
            blocos.append(f); continue
        melhor = None
        for k in range(2, 4):
            for cortes in combinations(range(1, len(f)), k - 1):
                ls = [f[i:j] for i, j in zip((0,) + cortes, cortes + (len(f),))]
                if max(len(" ".join(x["w"] for x in l)) for l in ls) > 36: continue
                cc = custo(ls) + 22 * k
                if melhor is None or cc < melhor[0]: melhor = (cc, ls)
        blocos += melhor[1] if melhor else [f]
    CORRIGE = {"marcenaria detalhe": "marcenaria é detalhe"}   # leitura provável — confirmar com a cliente
    legendas = []
    for k, g in enumerate(blocos):
        texto = " ".join(x["w"] for x in g).rstrip(",")
        texto = texto[0].lower() + texto[1:]
        for a_, b_ in CORRIGE.items():
            texto = texto.replace(a_, b_)
        de = g[0]["s"] - 0.06
        ate = g[-1]["e"] + 0.18
        if k + 1 < len(blocos):
            ate = min(ate + 0.25, blocos[k + 1][0]["s"] - 0.06)
        legendas.append({"de": round(de, 3), "ate": round(ate, 3), "texto": texto})
    for a, b in zip(legendas, legendas[1:]):
        a["ate"] = min(a["ate"], b["de"])

    roteiro = {"_fonte": "Gerado por pipeline/oficina.py", "fps": 30, "duracao": dur, "cenas": cenas_base,
               "apoios": apoios, "legendas": legendas, "fadeFinal": 0.7}
    Path("src/oficina").mkdir(parents=True, exist_ok=True)
    Path("src/oficina/roteiro.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=1))
    (D / "palavras.json").write_text(json.dumps(palavras, ensure_ascii=False, indent=0))

    # Trilha discreta com ducking; mesma trilha lo-fi aprovada nos vídeos anteriores.
    M = Path("public/oficina/mix"); M.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", str(D / "voz_editada.wav"), "-af", f"aformat=channel_layouts=stereo,apad,atrim=0:{dur}",
           "-ar", "48000", str(M / "voz.wav"))
    salvar(gerar(dur, 84, 3), M / "trilha.wav")
    mixar_musica(M / "voz.wav", M / "trilha.wav", M / "audio.wav", dur, NIVEL_MUSICA, -16)

    base = dur - sum(a["ate"] - a["de"] for a in apoios)
    print(f"duração {dur:.1f}s | protagonista {100 * base / dur:.0f}% | apoios {100 * (1 - base / dur):.0f}% | "
          f"{len(legendas)} legendas")
    for c in cenas_base:
        print(f"  {c['de']:6.2f}–{c['ate']:6.2f}  {c['tomada']} (desde {c['inicioVideo']:.2f}s) {c.get('entrada', '')}")
    for a in apoios:
        print(f"  apoio {a['de']:6.2f}–{a['ate']:6.2f}  {a['video'].split('/')[-1]}  {' / '.join(a.get('rotulo', []))}")


if __name__ == "__main__":
    main()
