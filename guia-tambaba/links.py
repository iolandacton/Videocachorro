"""Cria os links clicáveis no PDF gerado por build.cjs."""
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, DictionaryObject, FloatObject, NameObject, NumberObject, TextStringObject,
)

OUT = Path(__file__).resolve().parent / "out"
SAIDA = OUT / "Guia-Casa-Tambaba.pdf"
PX = 0.75  # 1 px do HTML = 0,75 pt no PDF

paginas = json.loads((OUT / "_links.json").read_text())
writer = PdfWriter(clone_from=PdfReader(OUT / "_sem-links.pdf"))
assert len(writer.pages) == len(paginas), (len(writer.pages), len(paginas))
indice = {p["id"]: i for i, p in enumerate(paginas)}

for i, p in enumerate(paginas):
    pagina = writer.pages[i]
    altura = float(pagina.mediabox.height)
    for l in p["links"]:
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
            alvo = writer.pages[indice[l["link"]]].indirect_reference
            a[NameObject("/Dest")] = ArrayObject([alvo, NameObject("/Fit")])
        if "/Annots" not in pagina:
            pagina[NameObject("/Annots")] = ArrayObject()
        pagina["/Annots"].get_object().append(writer._add_object(a))

writer.add_metadata({"/Title": "Guia de boas-vindas - Casa Tambaba"})
with open(SAIDA, "wb") as f:
    writer.write(f)
print(f"OK: {SAIDA} ({len(writer.pages)} páginas, {SAIDA.stat().st_size / 1e6:.1f} MB)")
