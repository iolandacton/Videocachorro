#!/usr/bin/env python3
"""Monta src/arquitetura/final.json (gancho C6282 + áudio 1 + áudio 2) a partir das
transcrições corrigidas. Cada elemento é ancorado numa frase falada, nunca em tempo fixo.

Uso: python3 scripts/arq/roteiro_final.py
"""
import json
from pathlib import Path

SRC = Path("src/arquitetura")
P = {k: json.loads((SRC / f"palavras_{k}.json").read_text()) for k in ("gancho", "audio1", "audio2")}

# Trechos de fala no vídeo final: corta só a deixa "Vai, pode ir" e a frase repetida na emenda.
SEG = {
    "gancho": {"arquivo": "public/originais/yuri_gancho_C6282.mp4", "inicio": 0.0, "fim": 5.6, "em": 0.0},
    "audio1": {"arquivo": "public/originais/arquitetura_audio_1.mp3", "inicio": 1.70, "fim": 33.7, "em": 5.6},
}
SEG["audio2"] = {"arquivo": "public/originais/arquitetura_audio_2.mp3", "inicio": 0.80, "fim": 20.30,
                 "em": SEG["audio1"]["em"] + (SEG["audio1"]["fim"] - SEG["audio1"]["inicio"]) + 0.15}
DUR = round(SEG["audio2"]["em"] + SEG["audio2"]["fim"] - SEG["audio2"]["inicio"] + 0.75, 2)


def _achar(seg, frase, n=0):
    alvo = [w.lower() for w in frase.split()]
    ws = P[seg]
    limpa = lambda s: s.lower().strip(".,?!")
    achados = [i for i in range(len(ws) - len(alvo) + 1)
               if [limpa(w["w"]) for w in ws[i:i + len(alvo)]] == [limpa(a) for a in alvo]]
    if len(achados) <= n:
        raise SystemExit(f"Frase não encontrada em {seg}: {frase!r}")
    i = achados[n]
    return ws[i:i + len(alvo)]


def out(seg, t):
    s = SEG[seg]
    return round(t - s["inicio"] + s["em"], 2)


def T(seg, frase, n=0):  # início da frase no vídeo final
    return out(seg, _achar(seg, frase, n)[0]["s"])


def E(seg, frase, n=0):  # fim da frase no vídeo final
    return out(seg, _achar(seg, frase, n)[-1]["e"])


def leg(seg, frase, destaque=(), folga=0.35):
    ws = _achar(seg, frase)
    return {"de": out(seg, ws[0]["s"]), "ate": round(out(seg, ws[-1]["e"]) + folga, 2),
            "destaque": list(destaque), "palavras": [[w["w"], out(seg, w["s"])] for w in ws]}


A1, A2, G = "audio1", "audio2", "gancho"
cenas = [
    {"video": "originais/yuri_gancho_C6282.mp4", "de": 0, "mov": "parado"},
    {"img": "sala_escura", "de": T(A1, "Preto em excesso") - 0.55, "mov": "pushin", "entrada": "linha-vertical"},
    {"img": "base_clean", "de": T(A1, "Minha base") - 0.15, "mov": "pushin", "entrada": "linha-horizontal"},
    {"split": ["bege", "cinza"], "de": T(A1, "puxando pro bege"), "mov": "parado", "entrada": "split"},
    {"img": "vivencia", "de": T(A1, "mas nada muito escuro") + 0.5, "mov": "lateral", "entrada": "dissolve"},
    {"img": "tijolinho_fake", "de": T(A1, "Revestimento fake") - 0.41, "mov": "lateral", "entrada": "linha-vertical"},
    {"img": "porcelanato_grama_v2", "de": T(A1, "porcelanato que imita") - 0.16, "mov": "pushin", "entrada": "dissolve"},
    {"img": "papel_marmorizado_v2", "de": T(A1, "papel de parede marmorizado") - 0.15, "mov": "pullout",
     "entrada": "linha-horizontal"},
    {"img": "quarto_crianca", "de": T(A1, "Papel de parede só") - 0.2, "mov": "pushin", "entrada": "dissolve"},
    {"img": "papel_descolando", "de": T(A1, "com o tempo ele") - 0.2, "mov": "pushin", "entrada": "linha-vertical"},
    {"img": "pedra_natural", "de": T(A2, "Agora, o que eu") - 0.3, "mov": "pushin", "entrada": "linha-horizontal"},
    {"img": "granito", "de": T(A2, "granito"), "mov": "pushin", "entrada": "corte"},
    {"img": "mesa_pedra", "de": T(A2, "o tampo de mesa"), "mov": "pushin", "entrada": "corte", "luz": True},
    {"img": "atemporal", "de": T(A2, "Projeto bom") - 0.4, "mov": "pullout", "entrada": "linha-vertical"},
    {"img": "base_clean", "de": T(A2, "E aí, você") - 0.15, "mov": "pullout", "entrada": "dissolve"},
]
for a, b in zip(cenas, cenas[1:]):
    a["ate"] = b["de"]
cenas[-1]["ate"] = DUR

legendas = [
    leg(G, "Tem coisas que você nunca vai ver no meu projeto", ["nunca"]),
    leg(G, "e tem coisas que você vai ver em quase todos.", ["quase", "todos"]),
    leg(A1, "eu não uso muito, porque acho que fecha demais o ambiente.", ["fecha", "demais"]),
    leg(A1, "mas nada muito escuro,"),
    leg(A1, "pois acho que dificulta a vivência no ambiente.", ["vivência"]),
    leg(A1, "eu procuro não usar."),
    leg(A1, "Papel de parede só se for algo muito personalizado,", ["personalizado"]),
    leg(A1, "tipo um quarto de criança,"),
    leg(A1, "com o tempo ele desgasta, descola,", ["desgasta", "descola"]),
    leg(A2, "Projeto bom pra mim é aquele que continua bonito daqui alguns anos.", ["continua", "bonito"]),
    leg(A2, "E aí, você usaria alguma dessas coisas na sua casa?", ["sua", "casa"], folga=0.9),
]

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
    {"esq": "sofisticada", "tEsq": T(A2, "sofisticada"), "dir": "durabilidade", "tDir": T(A2, "durabilidade"),
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

roteiro = {"_fonte": "Gerado por scripts/arq/roteiro_final.py — não editar à mão.",
           "fps": 30, "duracao": DUR, "lufs": -16, "audio": list(SEG.values()), "cenas": cenas,
           "legendas": legendas, "palavrasChave": chaves, "pares": pares, "listas": listas, "sfx": sfx}
(SRC / "final.json").write_text(json.dumps(roteiro, ensure_ascii=False, indent=1))
print(f"final.json: {DUR}s, {len(cenas)} cenas, {len(legendas)} legendas, {len(sfx)} efeitos")
for c in cenas:
    print(f"  {c['de']:6.2f}–{c['ate']:6.2f}  {c.get('img') or c.get('video') or c.get('split')}  ({c.get('entrada', '-')})")
