// Monta as cinco artes do carrossel "O que fazemos" (1080 x 1350) a partir das cenas em img/.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const head = `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><style>
@font-face { font-family: Montserrat; font-weight: 300; src: url(fonts/montserrat-latin-300-normal.woff2) format('woff2'); }
@font-face { font-family: Montserrat; font-weight: 400; src: url(fonts/montserrat-latin-400-normal.woff2) format('woff2'); }
@font-face { font-family: Montserrat; font-weight: 500; src: url(fonts/montserrat-latin-500-normal.woff2) format('woff2'); }
:root { --off: 243,237,226; }
html, body { margin: 0; background: #000; }
.art { position: relative; width: 1080px; height: 1350px; overflow: hidden; background: #060606; font-family: Montserrat, sans-serif; color: rgb(var(--off)); }
.layer { position: absolute; inset: 0; }
.scene { background-size: cover; background-repeat: no-repeat; }
.shade { background:
  linear-gradient(0deg, rgba(0,0,0,.94) 0%, rgba(0,0,0,.80) 18%, rgba(0,0,0,.30) 40%, transparent 56%),
  linear-gradient(180deg, rgba(0,0,0,.62) 0%, transparent 20%),
  radial-gradient(130% 100% at 50% 40%, transparent 52%, rgba(0,0,0,.60) 100%); }
.mark { position: absolute; left: 86px; top: 84px; width: 84px; mix-blend-mode: screen; }
.idx { position: absolute; right: 96px; top: 104px; font-weight: 400; font-size: 14px; letter-spacing: .34em; opacity: .7; }
.label { position: absolute; left: 96px; font-weight: 500; font-size: 15px; letter-spacing: .42em; opacity: .74; }
.rule { position: absolute; left: 96px; width: 44px; height: 1px; background: rgba(var(--off), .6); }
h1 { position: absolute; left: 96px; bottom: 96px; margin: 0; font-weight: 300; font-size: 46px; line-height: 1.24; letter-spacing: .13em; text-transform: uppercase; }
.grain { opacity: .13; mix-blend-mode: overlay; }
/* capa */
.beam { position: absolute; left: 50%; top: 50%; }
.beam.wide { width: 560px; height: 2600px; margin: -1300px 0 0 -230px; transform: rotate(-39deg);
  background: linear-gradient(90deg, transparent 0%, rgba(var(--off), .07) 30%, rgba(var(--off), .17) 50%, rgba(var(--off), .07) 70%, transparent 100%); filter: blur(40px);
  -webkit-mask-image: linear-gradient(180deg, #000 0%, #000 44%, rgba(0,0,0,.3) 60%, transparent 74%); mask-image: linear-gradient(180deg, #000 0%, #000 44%, rgba(0,0,0,.3) 60%, transparent 74%); }
.beam.core { width: 150px; height: 2600px; margin: -1300px 0 0 -40px; transform: rotate(-39deg);
  background: linear-gradient(90deg, transparent, rgba(var(--off), .16) 50%, transparent); filter: blur(22px);
  -webkit-mask-image: linear-gradient(180deg, #000 0%, #000 42%, transparent 62%); mask-image: linear-gradient(180deg, #000 0%, #000 42%, transparent 62%); }
.beam.edge { width: 3px; height: 2600px; margin: -1300px 0 0 180px; transform: rotate(-39deg); background: rgba(var(--off), .26); filter: blur(1.2px);
  -webkit-mask-image: linear-gradient(180deg, transparent 4%, #000 16%, #000 40%, transparent 58%); mask-image: linear-gradient(180deg, transparent 4%, #000 16%, #000 40%, transparent 58%); }
.ambient { background: radial-gradient(900px 700px at 24% -6%, rgba(var(--off), .14), transparent 62%); }
.vignette { background: radial-gradient(120% 95% at 50% 40%, transparent 42%, rgba(0,0,0,.62) 78%, rgba(0,0,0,.93) 100%), linear-gradient(0deg, rgba(0,0,0,.85) 0%, transparent 42%); }
canvas { position: absolute; inset: 0; }
/* pontos interativos do tour */
.hot { position: absolute; width: 18px; height: 18px; margin: -9px 0 0 -9px; border-radius: 50%; background: rgb(var(--off)); box-shadow: 0 0 18px rgba(var(--off), .55); }
.hot::before { content: ''; position: absolute; inset: -15px; border-radius: 50%; border: 1px solid rgba(var(--off), .75); }
.hot::after { content: ''; position: absolute; inset: -30px; border-radius: 50%; border: 1px solid rgba(var(--off), .22); }
.tag { position: absolute; font-weight: 500; font-size: 12px; letter-spacing: .3em; padding: 9px 14px 9px 16px; border: 1px solid rgba(var(--off), .45); background: rgba(8,8,8,.55); backdrop-filter: blur(6px); white-space: nowrap; }
.lead { position: absolute; height: 1px; background: rgba(var(--off), .5); transform-origin: left center; }
.compass { position: absolute; right: 96px; top: 170px; width: 92px; height: 92px; }
/* fecho */
.logo-full { position: absolute; left: 50%; width: 560px; margin-left: -280px; mix-blend-mode: screen; }
.closing { position: absolute; left: 0; right: 0; text-align: center; font-weight: 300; font-size: 25px; letter-spacing: .36em; text-indent: .36em; text-transform: uppercase; }
</style></head><body><div class="art" id="art">`;

const grain = `<svg class="layer grain" width="1080" height="1350"><filter id="n"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="7"/><feColorMatrix type="saturate" values="0"/></filter><rect width="100%" height="100%" filter="url(#n)"/></svg>`;
const foot = `</div></body></html>`;
const mark = `<img class="mark" src="img/simbolo-a.png" alt="">`;
const idx = n => `<div class="idx">0${n} / 05</div>`;
const text = (label, lines, labelBottom) => `<div class="label" style="bottom:${labelBottom}px">${label}</div><div class="rule" style="bottom:${labelBottom - 26}px"></div><h1>${lines.join('<br>')}</h1>`;
const scene = (file, pos = 'center top', extra = '') => `<div class="layer scene" style="background-image:url(img/${file});background-position:${pos};${extra}"></div><div class="layer shade"></div>`;

const dust = `<canvas id="dust" width="1080" height="1350"></canvas><script>
let s = 77; const rnd = () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296;
const c = document.getElementById('dust').getContext('2d'); const ang = -39 * Math.PI / 180, cx = 590, cy = 675;
for (let i = 0; i < 560; i++) { const along = (rnd() - .66) * 1500, g = (rnd() + rnd() + rnd() - 1.5) / 1.5, across = g * 320;
  const x = cx + across * Math.cos(ang) - along * Math.sin(ang), y = cy + across * Math.sin(ang) + along * Math.cos(ang); if (y > 760) continue;
  const r = .4 + rnd() * rnd() * 2.2, a = (.05 + rnd() * .32) * (1 - Math.abs(g));
  c.beginPath(); c.fillStyle = 'rgba(243,237,226,' + a.toFixed(3) + ')'; c.shadowColor = 'rgba(243,237,226,.5)'; c.shadowBlur = r * 3; c.arc(x, y, r, 0, 6.283); c.fill(); }
</script>`;

const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'carrossel.json'), 'utf8'));
const hotspots = (cfg.hotspots || []).map(h => {
  const len = h.len || 46;
  let out = `<div class="hot" style="left:${h.x}px;top:${h.y}px"></div>`;
  if (h.tag && h.side === 'left') out += `<div class="lead" style="left:${h.x - 24 - len}px;top:${h.y}px;width:${len}px"></div><div class="tag" style="right:${1080 - (h.x - 24 - len)}px;top:${h.y - 17}px">${h.tag}</div>`;
  else if (h.tag) out += `<div class="lead" style="left:${h.x + 24}px;top:${h.y}px;width:${len}px"></div><div class="tag" style="left:${h.x + 24 + len}px;top:${h.y - 17}px">${h.tag}</div>`;
  return out;
}).join('') + (cfg.floor || []).map(f => `<svg style="position:absolute;left:${f.x - 90}px;top:${f.y - 30}px" width="180" height="60" viewBox="0 0 180 60" fill="none" stroke="rgb(243,237,226)"><ellipse cx="90" cy="30" rx="86" ry="26" stroke-opacity=".28"/><ellipse cx="90" cy="30" rx="56" ry="17" stroke-opacity=".7" stroke-width="1.4"/><ellipse cx="90" cy="30" rx="10" ry="3.2" fill="rgb(243,237,226)" fill-opacity=".85" stroke="none"/></svg>`).join('');
const compass = `<svg class="compass" viewBox="0 0 92 92" fill="none" stroke="rgb(243,237,226)"><circle cx="46" cy="46" r="44" stroke-opacity=".35"/><ellipse cx="46" cy="46" rx="44" ry="15" stroke-opacity=".6"/><path d="M46 2 A44 44 0 0 1 46 90" stroke-opacity=".25"/><text x="46" y="51" text-anchor="middle" font-family="Montserrat" font-size="13" letter-spacing="2" fill="rgb(243,237,226)" stroke="none">360°</text></svg>`;

const slides = {
  1: head + `<div class="layer ambient"></div><div class="beam wide"></div><div class="beam core"></div><div class="beam edge"></div>${dust}<div class="layer vignette"></div>` + mark + idx(1) + text('O QUE FAZEMOS', ['Mais que imagens.', 'Criamos', 'experiências.'], 330).replace('font-size: 46px', '') + grain + foot,
  2: head + scene(cfg.s2.file, cfg.s2.pos) + mark + idx(2) + text('AUDIOVISUAL E FOTOGRAFIA', ['Imagens que', 'contam histórias.'], 258) + grain + foot,
  3: head + scene(cfg.s3.file, cfg.s3.pos) + mark + idx(3) + text('INTELIGÊNCIA ARTIFICIAL', ['Criatividade', 'sem limites.'], 258) + grain + foot,
  4: head + scene(cfg.s4.file, cfg.s4.pos) + hotspots + compass + mark + idx(4) + text('EXPERIÊNCIAS 360° E DIGITAIS', ['O digital ganha', 'uma nova dimensão.'], 258) + grain + foot,
  5: head + scene(cfg.s5.file, cfg.s5.pos) + `<div class="layer" style="background:linear-gradient(0deg, rgba(0,0,0,.96) 0%, rgba(0,0,0,.9) 34%, rgba(0,0,0,.35) 52%, transparent 64%)"></div>` + idx(5) +
     `<img class="logo-full" src="../logo-atrio-oficial.png" style="top:${cfg.s5.logoTop}px" alt="ATRIO"><div class="closing" style="bottom:118px">Uma nova forma de criar.</div>` + grain + foot,
};

(async () => {
  const only = process.argv.slice(2).map(Number);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1080, height: 1350 }, deviceScaleFactor: 1 });
  for (const n of Object.keys(slides)) {
    if (only.length && !only.includes(+n)) continue;
    const f = path.join(__dirname, `carrossel-${n}.html`);
    fs.writeFileSync(f, slides[n]);
    await p.goto('file://' + f); await p.waitForTimeout(500);
    await (await p.$('#art')).screenshot({ path: path.join(__dirname, `../previas/post2-${n}.png`) });
    console.log('ok', n);
  }
  await b.close();
})();
