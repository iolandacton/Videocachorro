// Gera o guia interativo da Casa Tambaba:
//   1. renderiza paginas.html e sobreposicoes.html em PDF (Chromium/Playwright)
//   2. anota a posição de cada elemento clicável (data-link / data-href)
//   3. chama montar.py, que junta tudo ao PDF original e cria os links
// Uso: node guia-tambaba/build.cjs
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const DIR = __dirname;
const OUT = path.join(DIR, "out");
fs.mkdirSync(OUT, { recursive: true });

async function render(page, html, pdfName, transparent) {
  await page.goto("file://" + path.join(DIR, html), { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  const pages = await page.evaluate(() =>
    [...document.querySelectorAll(".page")].map((p) => {
      const base = p.getBoundingClientRect();
      const links = [...p.querySelectorAll("[data-link],[data-href]")].map((el) => {
        const r = el.getBoundingClientRect();
        return {
          link: el.dataset.link || null,
          href: el.dataset.href || null,
          x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height,
        };
      });
      return { id: p.dataset.id || null, pagina: p.dataset.pagina ? Number(p.dataset.pagina) : null, links };
    })
  );
  await page.pdf({
    path: path.join(OUT, pdfName),
    preferCSSPageSize: true,
    printBackground: true,
    omitBackground: transparent,
  });
  return pages;
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1284, height: 2778 } });
  const novas = await render(page, "paginas.html", "_novas.pdf", false);
  const sobre = await render(page, "sobreposicoes.html", "_sobreposicoes.pdf", true);
  await browser.close();
  fs.writeFileSync(path.join(OUT, "_links.json"), JSON.stringify({ novas, sobre }, null, 2));
  execFileSync("python3", ["-I", path.join(DIR, "montar.py")], { stdio: "inherit" });
})();
