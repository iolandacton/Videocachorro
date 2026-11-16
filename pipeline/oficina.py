#!/usr/bin/env python3
"""Oficina Sete — montagem: voz tratada + cortes + roteiro (cenas, apoios, legendas, rótulos) + trilha.

1. Voz de cada tomada do protagonista: DeepFilterNet (limite de atenuação) → EQ por correspondência
   (mesmo timbre entre tomadas) → de-esser + compressão leve → normalização.
2. Cortes: trechos escolhidos (por frase), início/fim no ponto de menor energia; pausas longas removidas.
3. Roteiro para o Remotion: protagonista como base, apoios ancorados nas frases que ilustram, legendas
   curtas no estilo da referência e rótulos de detalhe (só com termos ditos na fala).
4. Trilha lo-fi discreta com ducking; volume final −16 LUFS.
Uso: .venv/bin/python pipeline/oficina.py          (v4 aprovada — arquivos de 512x910)
     .venv/bin/python pipeline/oficina.py --v5     (ajustes pedidos sobre a versão dos originais da câmera)

v5 (mesma edição, mesma voz tratada, mesmas legendas/estilo):
  • "…acho fundamental." → "A gente diminui…": os dois trechos são CONTÍNUOS na tomada; o corte (que voltava
    0,4 s no mesmo plano) deixa de existir — a fala segue sem emenda;
  • troca de tomada antes de "Marcenaria é detalhe": virada de página (com som de papel) no lugar do corte seco;
  • imagem da porta usinada: câmera lenta real (todos os quadros do original 59,94p) e quase o dobro do tempo.

v6 / v6b (--v6 com virada de página no fechamento, --v6b sem):
  • imagens do "gimbal virtual" (scripts/oficina/gimbal_*.py): câmera suave e apresentador mais centralizado;
  • a pedido da cliente, os takes só do móvel (em câmera lenta real) entram sobre as falas que eles ilustram;
  • as trocas de tomada ficam SEMPRE escondidas sob uma imagem de detalhe já opaca (sem "relâmpago").
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
VER = next((v for v in ("v5", "v6", "v6b") if f"--{v}" in sys.argv), None)
V5 = VER is not None            # v5 em diante: trechos contínuos unidos, 29,97 fps, voz aprovada reaproveitada
V6 = VER in ("v6", "v6b")       # v6: gimbal virtual + imagens de detalhe sobre a fala; v6b = sem a virada de página
SUF = f"_{VER}" if VER else ""
PASTA = "oficina/gimbal" if V6 else "oficina/cam" if V5 else "oficina/proc"
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
FANTASMAS = {"Tchau!"}   # palavra que o Whisper "ouviu" num estalo entre duas frases — não foi dita
GAP_MESMA, GAP_OUTRA = 0.24, 0.32
# fala ocupa ~83% do vídeo: trilha mais presente que nos vídeos do Yuri (~13 dB abaixo da voz durante a fala)
NIVEL_MUSICA = -24.5  # respiro entre trechos (mesma tomada / tomadas diferentes)
if V5:   # "e são trilhos … fundamental." + "A gente diminui … raja única." = um trecho só (contínuo na tomada)
    TRECHOS[5:7] = [("C6212", "e são trilhos,", "raja única.")]
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
        trat = D / f"{k}_tratado.wav"
        if V5 and trat.exists():      # v5 reaproveita exatamente a voz já aprovada
            out[k] = V.ler(trat); continue
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
        cenas_base.append({"video": f"{PASTA}/{k}.mp4", "inicioVideo": round(a, 3), "de": round(t_out, 3),
                           "tomada": k, "trecho": idx})
        for w in ws[i0:i1 + 1]:
            if w["w"] in FANTASMAS:
                continue
            palavras.append({"w": GRAFIA.get(w["w"], w["w"]), "s": round(w["s"] - a + t_out, 3),
                             "e": round(w["e"] - a + t_out, 3), "trecho": idx})
        t_out += b - a
        anterior = k
    voz = np.concatenate(partes)
    V.gravar(voz, D / f"voz_editada{SUF}.wav")
    dur = round(len(voz) / SR + 0.9, 2)   # respiro final para o encerramento
    for c0, c1 in zip(cenas_base, cenas_base[1:]):
        c0["ate"] = c1["de"]
    cenas_base[-1]["ate"] = dur
    # emendas entre trechos: corte seco. (Dissolve dentro da MESMA tomada sobrepõe dois momentos do plano em
    # movimento e as bordas rígidas parecem dobrar/esticar — deformação artificial; removido na v4.)
    for c1 in cenas_base[1:]:
        c1["entrada"] = "corte"
    if VER in ("v5", "v6"):   # troca de tomada para o fechamento: virada de página
        cenas_base[-1]["entrada"] = "pagina"

    def T_(frase, n=0):
        alvo = [limpa(x) for x in frase.split()]
        ach = [i for i in range(len(palavras) - len(alvo) + 1) if [limpa(w["w"]) for w in palavras[i:i + len(alvo)]] == alvo]
        return palavras[ach[n]]["s"], palavras[ach[n] + len(alvo) - 1]["e"]

    fim_trecho = {c["trecho"]: c["ate"] for c in cenas_base}
    # Apoios (≈20% do tempo), cada um ilustrando exatamente o que está sendo dito; o áudio do apoio é mudo.
    # Apoios: só takes originais sem estabilização, no trecho MAIS FIRME de cada um (medido quadro a quadro).
    # C6220/C6221 (tremor forte no original) e C6223 (reflexo de quem filma) ficam de fora.
    apoios = [
        {"video": f"{PASTA}/C6218.mp4", "inicioVideo": 0.13, "de": T_("Olha só")[0] - 0.1,
         "ate": T_("Olha só")[0] - 0.1 + 2.3},                                     # o painel ripado (a solução)
        {"video": f"{PASTA}/C6222{'_lento' if V5 else ''}.mp4", "inicioVideo": 0.4 if V5 else 0.2,   # v5: câmera lenta 50%
         "de": fim_trecho[3] + 0.15 - (3.2 if V5 else 1.7), "ate": fim_trecho[3] + 0.15,
         "rotulo": ["PORTA", "USINADA"]},                                          # cobre a troca de tomada
        {"video": f"{PASTA}/C6219.mp4", "inicioVideo": 0.67, "de": T_("Lá em cima")[0] - 0.1,
         "ate": T_("Lá em cima")[0] - 0.1 + 2.0, "rotulo": ["FITAMENTO", "NO TRILHO"]},  # topo da porta e trilho
    ]
    if V6:
        # Detalhes em câmera lenta real (arquivo _lento: 2 s de arquivo = 1 s do take). Cada um entra na fala que
        # ilustra; quando cobre uma troca de trecho, só começa a sair 0,12 s DEPOIS do corte (0,40 − 0,28 de fade).
        L = lambda k: f"{PASTA}/{k}_lento.mp4"
        corte = lambda i: fim_trecho[i] + 0.40
        fecho = cenas_base[-1]["de"]
        apoios = [
            {"video": L("C6218"), "inicioVideo": 0.26, "de": T_("Olha só")[0] - 0.1, "ate": T_("Olha só")[0] + 2.2},
            {"video": L("C6215"), "inicioVideo": 0.6, "de": T_("não muito")[0] - 0.13, "ate": corte(2)},      # esquadria branca × madeira
            {"video": L("C6222"), "inicioVideo": 0.4, "de": T_("essa porta")[0] + 0.14, "ate": corte(3),
             "rotulo": ["PORTA", "USINADA"]},
            {"video": L("C6216"), "inicioVideo": 0.6, "de": T_("são duas")[0] - 0.1, "ate": corte(4)},        # portas usinadas / carvalho
            {"video": L("C6219"), "inicioVideo": 0.3, "de": T_("e a gente tem o")[0] - 0.05, "ate": T_("desse trilho")[1] + 0.2},
            {"video": L("C6219"), "inicioVideo": 3.0, "de": T_("Lá em cima")[0] - 0.1, "ate": T_("o fitamento")[1] + 0.25,
             "rotulo": ["FITAMENTO", "NO TRILHO"]},
            {"video": L("C6220"), "inicioVideo": 0.5, "de": T_("Faz várias")[0] - 0.1, "ate": T_("mas assim")[0] + 0.6,
             "saida": "corte"},                                                                               # veio / emendas
            {"video": L("C6221"), "inicioVideo": 0.6, "de": T_("mas assim")[0] + 0.3, "ate": fecho + 0.45,     # raja única → fechamento
             **({"saida": "pagina"} if VER == "v6" else {})},
            {"video": L("C6217"), "inicioVideo": 0.6, "de": T_("eu acho uma")[0] - 0.1, "ate": T_("ter no")[0] - 0.07},
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

    total = dur
    if V6:   # encerramento com a logo (src/oficina/OutroOficina.tsx, 6 s): entra em dissolve logo após a última fala
        outro_de = round(palavras[-1]["e"] + 0.35, 3)
        total = round(outro_de + 6.0, 3)
    roteiro = {"_fonte": "Gerado por pipeline/oficina.py", "fps": 30000 / 1001 if V5 else 30, "duracao": dur, "cenas": cenas_base,
               "apoios": apoios, "legendas": legendas, "fadeFinal": 0.7}
    if V6:
        roteiro["outro"] = {"de": outro_de}
    Path("src/oficina").mkdir(parents=True, exist_ok=True)
    Path(f"src/oficina/roteiro{SUF}.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=1))
    (D / f"palavras{SUF}.json").write_text(json.dumps(palavras, ensure_ascii=False, indent=0))

    # Trilha discreta com ducking; mesma trilha lo-fi aprovada nos vídeos anteriores.
    dur_fala = dur
    dur = total   # daqui em diante: duração do áudio (inclui o encerramento, com a trilha seguindo até o fim)
    M = Path(f"public/oficina/mix{SUF}"); M.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", str(D / f"voz_editada{SUF}.wav"), "-af", f"aformat=channel_layouts=stereo,apad,atrim=0:{dur}",
           "-ar", "48000", str(M / "voz.wav"))
    # Efeitos sonoros discretos, só onde há ação visual: tick quando o rótulo surge; whoosh na entrada da solução.
    SFX = {"tick": ("public/oficina/sfx/mixkit_1120.mp3", 0.10, -12.0),    # (arquivo, pico após o início, ganho dB)
           "whoosh": ("public/oficina/sfx/mixkit_1489.mp3", 0.71, -21.0),
           "pagina": ("public/oficina/sfx/mixkit_1105.mp3", 0.33, -10.0)}   # "Big paper page turn"
    eventos = [("whoosh", apoios[0]["de"] + 0.15)]
    eventos += [("tick", a["de"] + 0.35) for a in apoios if a.get("rotulo")]
    eventos += [("pagina", c["de"] - 0.12) for c in cenas_base if c.get("entrada") == "pagina"]
    if V6:
        SFX["logo"] = ("public/oficina/sfx/mixkit_1489.mp3", 0.71, -24.0)   # sopro bem discreto quando a logo se revela
        eventos.append(("logo", outro_de + 3.5))
    ent, fil = [], []
    for j, (tipo, t_pico) in enumerate(eventos):
        arq, pico, ganho = SFX[tipo]
        ms = max(0, int((t_pico - pico) * 1000))
        ent += ["-i", arq]
        fil.append(f"[{j}:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={ganho}dB,adelay={ms}|{ms}[s{j}]")
    fc = ";".join(fil) + ";" + "".join(f"[s{j}]" for j in range(len(eventos))) + \
        f"amix=inputs={len(eventos)}:normalize=0,apad,atrim=0:{dur}"
    ffmpeg(*ent, "-filter_complex", fc, "-ar", "48000", str(M / "sfx.wav"))
    ffmpeg("-i", str(M / "voz.wav"), "-i", str(M / "sfx.wav"), "-filter_complex",
           "[0:a][1:a]amix=inputs=2:normalize=0:duration=first", "-ar", "48000", str(M / "voz_sfx.wav"))
    roteiro["sfx"] = [{"tipo": t, "pico": round(x, 2)} for t, x in eventos]
    Path(f"src/oficina/roteiro{SUF}.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=1))
    salvar(gerar(dur, 84, 3), M / "trilha.wav")
    mixar_musica(M / "voz_sfx.wav", M / "trilha.wav", M / "audio.wav", dur, NIVEL_MUSICA, -16)

    base = dur_fala - sum(a["ate"] - a["de"] for a in apoios)
    print(f"duração {dur:.1f}s | protagonista {100 * base / dur_fala:.0f}% | apoios {100 * (1 - base / dur_fala):.0f}% | "
          f"{len(legendas)} legendas")
    for c in cenas_base:
        print(f"  {c['de']:6.2f}–{c['ate']:6.2f}  {c['tomada']} (desde {c['inicioVideo']:.2f}s) {c.get('entrada', '')}")
    for a in apoios:
        print(f"  apoio {a['de']:6.2f}–{a['ate']:6.2f}  {a['video'].split('/')[-1]}  {' / '.join(a.get('rotulo', []))}")


if __name__ == "__main__":
    main()
