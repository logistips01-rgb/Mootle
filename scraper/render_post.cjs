// Renderiza marketing/_fuentes/post.html a un PNG 1080x1080 con los datos dados.
// Uso: node scraper/render_post.cjs <data.json> <salida.png>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const [, , dataPath, out] = process.argv;
  const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
  const tpl = 'file://' + path.resolve(__dirname, '../marketing/_fuentes/post.html');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto(tpl, { waitUntil: 'load', timeout: 60000 });
  await page.evaluate((d) => window.renderPost(d), data);
  // esperar a que fuentes e imágenes carguen
  try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch (e) {}
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(700);
  await page.screenshot({ path: out });
  await browser.close();
  console.log('OK ' + out);
})().catch((e) => { console.error(e); process.exit(1); });
