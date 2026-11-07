// Renderiza marketing/_fuentes/camiseta.html a PNG. Uso:
//   node scraper/render_shirt.cjs "<query>" <salida.png>  (vista previa 1200x1400 @2x)
//   añade print=1 en la query para fondo transparente (listo para imprimir)
const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const [, , query, out] = process.argv;
  const transparent = /(?:^|&)print=1/.test(query || '');
  const tpl = 'file://' + path.resolve(__dirname, '../marketing/_fuentes/camiseta.html') + '?' + (query || '');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 1400 }, deviceScaleFactor: 2 });
  await page.goto(tpl, { waitUntil: 'load', timeout: 60000 });
  try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch (e) {}
  await page.waitForTimeout(500);
  await page.screenshot({ path: out, omitBackground: transparent });
  await browser.close();
  console.log('OK ' + out);
})().catch((e) => { console.error(e); process.exit(1); });
