// Renderiza marketing/_fuentes/anuncio.html a PNG.
// Uso: node scraper/render_anuncio.cjs <salida.png> [ancho] [alto] [tall]
//   tall = añade la clase .tall (layout para story vertical)
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const [, , out, w = '1080', h = '1080', variant = ''] = process.argv;
  const width = parseInt(w, 10), height = parseInt(h, 10);
  const tpl = 'file://' + path.resolve(__dirname, '../marketing/_fuentes/anuncio.html');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 2 });
  await page.goto(tpl, { waitUntil: 'load', timeout: 60000 });
  if (variant === 'tall') await page.evaluate(() => document.body.classList.add('tall'));
  try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch (e) {}
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(700);
  await page.screenshot({ path: out });
  await browser.close();
  console.log('OK ' + out);
})().catch((e) => { console.error(e); process.exit(1); });
