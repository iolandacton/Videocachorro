// Gera o guia interativo da Casa Tambaba em PDF.
//   1. junta guia.html + icones.svg + dados privados (originais/privado.json)
//   2. renderiza no Chromium (Playwright) e anota a posição de cada elemento clicável
//   3. links.py cria os links internos (data-link) e externos (data-href) no PDF
// Uso: node guia-tambaba/build.cjs
const { chromium } = require("playwright");
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const DIR = __dirname;
const OUT = path.join(DIR, "out");
fs.mkdirSync(OUT, { recursive: true });

const privado = JSON.parse(fs.readFileSync(path.join(DIR, "originais", "privado.json"), "utf8"));
let html = fs.readFileSync(path.join(DIR, "guia.html"), "utf8")
  .replace("<!--ICONES-->", fs.readFileSync(path.join(DIR, "icones.svg"), "utf8"))
  .replace("<head>", `<head><base href="file://${DIR}/">`)
  .replace(/\{\{(\w+)\}\}/g, (_, k) => {
    if (!(k in privado)) throw new Error(`Falta ${k} em originais/privado.json`);
    return privado[k];
  });
const tmp = path.join(OUT, "_guia.html");
fs.writeFileSync(tmp, html);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1284, height: 2778 } });
  await page.goto("file://" + tmp, { waitUntil: "networkidle" });
  await page.evaluate(() => document.fonts.ready);
  const paginas = await page.evaluate(() =>
    [...document.querySelectorAll(".page")].map((p) => {
      const base = p.getBoundingClientRect();
      const estouro = p.scrollHeight > p.clientHeight + 1;
      const links = [...p.querySelectorAll("[data-link],[data-href]")].map((el) => {
        const r = el.getBoundingClientRect();
        return { link: el.dataset.link || null, href: el.dataset.href || null,
                 x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height };
      });
      return { id: p.dataset.id, estouro, links };
    })
  );
  for (const p of paginas) if (p.estouro) console.warn(`AVISO: conteúdo passou do fim da página "${p.id}"`);
  await page.pdf({ path: path.join(OUT, "_sem-links.pdf"), preferCSSPageSize: true, printBackground: true });
  await browser.close();
  fs.writeFileSync(path.join(OUT, "_links.json"), JSON.stringify(paginas, null, 2));
  execFileSync("python3", ["-I", path.join(DIR, "links.py")], { stdio: "inherit" });
})();
