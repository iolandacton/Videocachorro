# Guia de boas-vindas — Casa Tambaba

Gera o PDF interativo do guia: o PDF original (Canva) + páginas novas de "Como funciona"
(vídeos e passo a passo) no mesmo visual, com todos os ícones clicáveis.

```
node guia-tambaba/build.cjs   # gera guia-tambaba/out/Guia-Casa-Tambaba.pdf
```

- `paginas.html` — páginas novas (hub "Como funciona", chegada, hidromassagem, ping-pong, telão)
- `sobreposicoes.html` — o que é desenhado por cima das páginas originais (ícone novo no menu, atalhos)
- `estilo.css` — cores, fontes e componentes do guia
- `montar.py` — junta tudo ao original e cria os links

Elementos com `data-link="id"` viram links internos; `data-href="url"` viram links externos.

O PDF original fica em `guia-tambaba/originais/guia-original.pdf` e a saída em `guia-tambaba/out/`.
Os dois **não são commitados** (têm senha do Wi-Fi e contatos, e o repositório é público).
