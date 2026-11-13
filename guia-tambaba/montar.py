"""Junta as páginas novas e as sobreposições ao PDF original do guia
e cria os links clicáveis. Chamado por build.cjs."""
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, DictionaryObject, FloatObject, NameObject, NumberObject, TextStringObject,
)

DIR = Path(__file__).resolve().parent
OUT = DIR / "out"
ORIGINAL = DIR / "originais" / "guia-original.pdf"
SAIDA = OUT / "Guia-Casa-Tambaba.pdf"

INSERIR_DEPOIS_DA_PAGINA = 10  # depois da 2ª página "Importante"
PAGINA_MENU = 2
PX = 0.75  # 1 px do HTML = 0,75 pt no PDF

info = json.loads((OUT / "_links.json").read_text())
novas = PdfReader(OUT / "_novas.pdf")
sobre = PdfReader(OUT / "_sobreposicoes.pdf")
writer = PdfWriter(clone_from=PdfReader(ORIGINAL))
altura = float(writer.pages[0].mediabox.height)

# 1. Sobreposições desenhadas por cima das páginas originais
for i, p in enumerate(info["sobre"]):
    writer.pages[p["pagina"] - 1].merge_page(sobre.pages[i])

# 2. Páginas novas
for k, pg in enumerate(novas.pages):
    writer.insert_page(pg, INSERIR_DEPOIS_DA_PAGINA + k)


def indice_original(pagina):
    """Índice final (0 = capa) de uma página do PDF original."""
    return pagina - 1 if pagina <= INSERIR_DEPOIS_DA_PAGINA else pagina - 1 + len(novas.pages)


destinos = {"menu": indice_original(PAGINA_MENU)}
for k, p in enumerate(info["novas"]):
    destinos[p["id"]] = INSERIR_DEPOIS_DA_PAGINA + k


def criar_links(indice, links):
    for l in links:
        x1, x2 = l["x"] * PX, (l["x"] + l["w"]) * PX
        y1, y2 = altura - (l["y"] + l["h"]) * PX, altura - l["y"] * PX
        a = DictionaryObject({
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Link"),
            NameObject("/Rect"): ArrayObject([FloatObject(v) for v in (x1, y1, x2, y2)]),
            NameObject("/Border"): ArrayObject([NumberObject(0)] * 3),
        })
        if l["href"]:
            a[NameObject("/A")] = DictionaryObject({
                NameObject("/S"): NameObject("/URI"),
                NameObject("/URI"): TextStringObject(l["href"]),
            })
        else:
            # destino = objeto da página (não o número), como os links do Canva
            alvo = writer.pages[destinos[l["link"]]].indirect_reference
            a[NameObject("/Dest")] = ArrayObject([alvo, NameObject("/Fit")])
        pagina = writer.pages[indice]
        if "/Annots" not in pagina:
            pagina[NameObject("/Annots")] = ArrayObject()
        pagina["/Annots"].get_object().append(writer._add_object(a))


for k, p in enumerate(info["novas"]):
    criar_links(INSERIR_DEPOIS_DA_PAGINA + k, p["links"])
for p in info["sobre"]:
    criar_links(indice_original(p["pagina"]), p["links"])

writer.compress_identical_objects()
with open(SAIDA, "wb") as f:
    writer.write(f)
print(f"OK: {SAIDA} ({len(writer.pages)} páginas, {SAIDA.stat().st_size / 1e6:.1f} MB)")
