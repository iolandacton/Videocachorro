#!/usr/bin/env python3
"""Roteiro v2 (cópia de trabalho — NÃO altera final.json aprovado).

Mesmas cenas, imagens, listas e palavras-chave aprovadas, mas ancoradas na fala tratada e editada
(public/arq_v2/voz/palavras.json), legendas curtas e centralizadas (2–5 palavras) e os takes
reais do Yuri depois de "Projeto bom pra mim".
Uso: python3 scripts/arq/roteiro_v2.py  →  src/arquitetura/v2/final_v2.json
"""
import json
from pathlib import Path

VOZ = Path("public/arq_v2/voz")
PAL = json.loads((VOZ / "palavras.json").read_text())
CORTES = {c["fonte"]: c for c in json.loads((VOZ / "cortes.json").read_text())}
INICIO_GANCHO = CORTES["gancho"]["mantido"][0][0]  # o vídeo do gancho começa onde a fala foi cortada
import subprocess
DUR_VOZ = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                                str(VOZ / "voz_tratada.wav")], capture_output=True, text=True).stdout)
DUR = round(DUR_VOZ + 0.6, 2)


def _achar(seg, frase, n=0):
    ws = [w for w in PAL if w["fonte"] == seg]
    limpa = lambda s: s.lower().strip(".,?!")
    alvo = [limpa(a) for a in frase.split()]
    achados = [i for i in range(len(ws) - len(alvo) + 1) if [limpa(w["w"]) for w in ws[i:i + len(alvo)]] == alvo]
    if len(achados) <= n:
        raise SystemExit(f"Frase não encontrada em {seg}: {frase!r}")
    return ws[achados[n]:achados[n] + len(alvo)]


def T(seg, frase, n=0):
    return round(_achar(seg, frase, n)[0]["s"], 2)


def E(seg, frase, n=0):
    return round(_achar(seg, frase, n)[-1]["e"], 2)


def blocos(seg, frase, destaque=(), folga=0.35):
    """Divide a frase em blocos de 2–5 palavras: quebra na pontuação, em pausas e no limite de tamanho."""
    if "|" in frase:
        partes = [x.split() for x in frase.split("|")]
        ws = _achar(seg, " ".join(sum(partes, [])))
        grupos, i = [], 0
        for pt in partes:
            grupos.append(ws[i:i + len(pt)])
            i += len(pt)
        return _montar(grupos, destaque, folga)
    ws = _achar(seg, frase)
    grupos, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        prox = ws[i + 1] if i + 1 < len(ws) else None
        pont = w["w"][-1] in ".,?!"
        pausa = prox is not None and prox["s"] - w["e"] > 0.25
        if prox is None or len(cur) == 5 or (len(cur) >= 2 and (pont or pausa)) or \
                (len(cur) >= 3 and len(" ".join(x["w"] for x in cur + [prox])) > 30):
            grupos.append(cur)
            cur = []
    if len(grupos) > 1 and len(grupos[-1]) == 1:  # nada de palavra sozinha no fim
        ultimo = grupos.pop()
        grupos[-1] += ultimo
    return _montar(grupos, destaque, folga)


def _montar(grupos, destaque, folga):
    out = []
    for k, g in enumerate(grupos):
        de = round(g[0]["s"] - 0.08, 2)
        ate = round(grupos[k + 1][0]["s"] - 0.08, 2) if k + 1 < len(grupos) else round(g[-1]["e"] + folga, 2)
        out.append({"de": de, "ate": ate, "destaque": list(destaque), "palavras": [[w["w"], round(w["s"], 2)] for w in g]})
    return out


A1, A2, G = "audio1", "audio2", "gancho"
cenas = [
    {"video": "originais/yuri_gancho_C6282.mp4", "inicioVideo": INICIO_GANCHO, "de": 0, "mov": "parado"},
    {"img": "sala_escura", "de": T(A1, "Preto em excesso") - 0.55, "mov": "pushin", "entrada": "linha-vertical"},
    {"img": "base_clean", "de": T(A1, "Minha base") - 0.15, "mov": "pushin", "entrada": "linha-horizontal"},
    {"split": ["bege", "cinza"], "de": T(A1, "puxando pro bege"), "mov": "parado", "entrada": "split"},
    {"img": "vivencia", "de": T(A1, "mas nada muito escuro") + 0.5, "mov": "lateral", "entrada": "dissolve"},
    {"img": "tijolinho_fake", "de": T(A1, "Revestimento fake") - 0.41, "mov": "lateral", "entrada": "linha-vertical"},
    {"img": "porcelanato_grama_v3", "de": T(A1, "porcelanato que imita") - 0.16, "mov": "pushin", "entrada": "dissolve"},
    {"img": "papel_marmorizado_v2", "de": T(A1, "papel de parede marmorizado") - 0.15, "mov": "pullout",
     "entrada": "linha-horizontal"},
    {"img": "quarto_crianca", "de": T(A1, "Papel de parede só") - 0.2, "mov": "pushin", "entrada": "dissolve"},
    {"img": "papel_descolando", "de": T(A1, "com o tempo ele") - 0.2, "mov": "pushin", "entrada": "linha-vertical"},
    {"img": "pedra_natural", "de": T(A2, "Agora, o que eu") - 0.3, "mov": "pushin", "entrada": "linha-horizontal"},
    {"img": "granito", "de": T(A2, "granito"), "mov": "pushin", "entrada": "corte"},
    {"img": "mesa_pedra", "de": T(A2, "o tampo de mesa"), "mov": "pushin", "entrada": "corte", "luz": True},
    {"img": "atemporal", "de": T(A2, "Projeto bom") - 0.4, "mov": "pullout", "entrada": "linha-vertical"},
    # takes reais do Yuri depois de "Projeto bom pra mim" — cortes secos nas fronteiras de frase
    {"video": "arq_v2/takes/IMG_2722.mp4", "inicioVideo": 0.6, "de": T(A2, "é aquele") - 0.05, "mov": "parado",
     "entrada": "dissolve"},
    {"video": "arq_v2/takes/IMG_2721.mp4", "inicioVideo": 2.2, "de": T(A2, "daqui alguns") - 0.05, "mov": "parado",
     "entrada": "corte"},
    {"video": "arq_v2/takes/IMG_2723.mp4", "inicioVideo": 0.15, "de": T(A2, "E aí, você") - 0.08, "mov": "parado",
     "entrada": "corte"},
    {"video": "arq_v2/takes/IMG_2720.mp4", "inicioVideo": 0.0, "de": T(A2, "dessas coisas") - 0.05, "mov": "parado",
     "entrada": "corte"},
]
for a, b in zip(cenas, cenas[1:]):
    a["ate"] = b["de"]
cenas[-1]["ate"] = DUR

legendas = [b for frase in [
    blocos(G, "Tem coisas que | você nunca vai ver | no meu projeto", ["nunca"]),
    blocos(G, "e tem coisas que | você vai ver | em quase todos.", ["quase", "todos"]),
    blocos(A1, "eu não uso muito, | porque acho que | fecha demais o ambiente.", ["fecha", "demais"]),
    blocos(A1, "mas nada muito escuro,"),
    blocos(A1, "pois acho que dificulta | a vivência no ambiente.", ["vivência"]),
    blocos(A1, "eu procuro não usar."),
    blocos(A1, "Papel de parede | só se for algo | muito personalizado,", ["personalizado"]),
    blocos(A1, "tipo um quarto de criança,"),
    blocos(A1, "com o tempo | ele desgasta, descola,", ["desgasta", "descola"]),
    blocos(A2, "Projeto bom pra mim | é aquele que | continua bonito | daqui alguns anos.", ["continua", "bonito"]),
    blocos(A2, "E aí, você usaria | alguma dessas coisas | na sua casa?", ["sua", "casa"], folga=0.9),
] for b in frase]
for a, b in zip(legendas, legendas[1:]):  # nunca duas legendas ao mesmo tempo
    a["ate"] = min(a["ate"], b["de"])

chaves = [
    {"linha1": "MINHA BASE", "t1": T(A1, "Minha base"), "linha2": "CLEAN", "t2": T(A1, "clean"),
     "ate": T(A1, "puxando") - 0.1},
    {"linha1": "REVESTIMENTO", "t1": T(A1, "Revestimento"), "linha2": "FAKE", "t2": T(A1, "fake,"),
     "ate": T(A1, "tijolinho") - 0.1},
    {"linha1": "TEMPO ÚTIL", "t1": T(A1, "tempo útil"), "linha2": "MUITO\nBAIXO", "t2": T(A1, "muito baixo"),
     "ate": E(A1, "baixo.") + 0.6},
    {"linha1": "O QUE EU AMO USAR", "t1": T(A2, "o que eu amo usar"), "linha2": "COISAS\nNATURAIS",
     "t2": T(A2, "coisas naturais"), "ate": T(A2, "tipo pedra") + 0.05},
]
pares = [
    {"esq": "bege", "tEsq": T(A1, "bege"), "dir": "cinza", "tDir": T(A1, "cinza,"), "ate": T(A1, "mas nada") + 0.3},
    {"esq": "sofisticada", "tEsq": T(A2, "sofisticada"), "dir": "durabilidade", "tDir": T(A2, "durabilidade"), "layout": "diagonal",
     "ate": E(A2, "maior.") + 0.4},
]
listas = [
    {"tipo": "x", "ate": E(A1, "eu procuro não usar.") + 0.6, "itens": [
        {"texto": "Preto em excesso", "t": T(A1, "Preto em excesso")},
        {"texto": "Tijolinho fake", "t": T(A1, "tijolinho fake")},
        {"texto": "Porcelanato que imita grama", "t": T(A1, "porcelanato que imita")},
        {"texto": "Papel de parede marmorizado", "t": T(A1, "papel de parede marmorizado")},
    ]},
    {"tipo": "check", "ate": T(A2, "Projeto bom") - 0.2, "itens": [
        {"texto": "Pedra natural", "t": T(A2, "pedra natural")},
        {"texto": "Granito", "t": T(A2, "granito")},
        {"texto": "Tampo de mesa em pedra", "t": T(A2, "o tampo de mesa")},
    ]},
]
# Efeitos: só em transições importantes, ícones e entrada de palavras-chave.
sfx = [{"t": T(A1, "Preto em excesso") - 0.67, "tipo": "whoosh"}]
sfx += [{"t": i["t"], "tipo": "clique"} for l in listas for i in l["itens"]]
sfx += [{"t": k["t1"] - 0.08, "tipo": "ar"} for k in chaves]
sfx += [{"t": T(A1, "Revestimento fake") - 0.55, "tipo": "whoosh"},
        {"t": T(A1, "papel de parede marmorizado") - 0.3, "tipo": "whoosh"},
        {"t": T(A2, "Agora, o que eu") - 0.42, "tipo": "whoosh"},
        {"t": T(A2, "Projeto bom") - 0.5, "tipo": "whoosh"}]
sfx.sort(key=lambda s: s["t"])

roteiro = {"_fonte": "Gerado por scripts/arq/roteiro_v2.py — não editar à mão.",
           "fps": 30, "duracao": DUR, "lufs": -16, "cenas": cenas, "legendas": legendas,
           "palavrasChave": chaves, "pares": pares, "listas": listas, "sfx": sfx}
destino = Path("src/arquitetura/v2/final_v2.json")
destino.parent.mkdir(parents=True, exist_ok=True)
destino.write_text(json.dumps(roteiro, ensure_ascii=False, indent=1))
print(f"final_v2.json: {DUR}s, {len(cenas)} cenas, {len(legendas)} blocos de legenda, {len(sfx)} efeitos")
for c in cenas[-6:]:
    print(f"  {c['de']:6.2f}–{c['ate']:6.2f}  {c.get('img') or c.get('video')}")
for l in legendas:
    print(f"  {l['de']:6.2f}–{l['ate']:6.2f}  {' '.join(w for w, _ in l['palavras'])}")
