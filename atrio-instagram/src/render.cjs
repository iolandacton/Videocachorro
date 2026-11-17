const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [,, html, out] = process.argv;
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  await p.goto('file://' + path.resolve(html));
  await p.waitForTimeout(400);
  await (await p.$('#art')).screenshot({ path: out });
  await b.close();
})();
