# Guia de boas-vindas — Casa Tambaba

Gera o PDF interativo do guia (formato de celular, 25 páginas), no visual do guia original,
com todos os ícones e botões clicáveis.

```
node guia-tambaba/build.cjs   # gera guia-tambaba/out/Guia-Casa-Tambaba.pdf
```

- `guia.html` — todas as páginas (uma `<section class="page" data-id="...">` por página)
- `estilo.css` — cores, fontes e componentes
- `icones.svg` — todos os ícones, no mesmo traço
- `build.cjs` — renderiza no Chromium e anota as áreas clicáveis
- `links.py` — cria os links no PDF

Elementos com `data-link="id-da-pagina"` viram links internos; `data-href="url"` viram links externos.

Dados pessoais (senha do Wi-Fi, telefones, e-mail) entram como `{{CHAVE}}` no HTML e vêm de
`originais/privado.json`. As fotos ficam em `originais/fotos/`. A pasta `originais/` e a saída `out/`
**não são commitadas**, porque o repositório é público.
