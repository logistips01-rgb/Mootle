// Monta un reel vertical 1080x1920 (mp4 H.264) desde marketing/_fuentes/reel_multi.html.
// Renderiza fotogramas con Playwright (setTime) y los une con ffmpeg (con audio en silencio,
// que Instagram exige para los Reels por API).
// Uso: node scraper/render_reel.cjs <data.json> <salida.mp4>
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

(async () => {
  const [, , dataPath, out] = process.argv;
  const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));
  const fps = 25;
  const tmp = fs.mkdtempSync('/tmp/reel_');
  const tpl = 'file://' + path.resolve(__dirname, '../marketing/_fuentes/reel_multi.html');
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  await page.goto(tpl, { waitUntil: 'load', timeout: 60000 });
  await page.evaluate((d) => window.renderReel(d), data);
  try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch (e) {}
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(800);
  const total = await page.evaluate(() => window.__total);
  const N = Math.round(total * fps);
  for (let i = 0; i < N; i++) {
    await page.evaluate((t) => window.setTime(t), i / fps);
    await page.screenshot({ path: path.join(tmp, 'f_' + String(i).padStart(4, '0') + '.png') });
  }
  await browser.close();
  execFileSync('ffmpeg', ['-y',
    '-framerate', String(fps), '-i', path.join(tmp, 'f_%04d.png'),
    '-f', 'lavfi', '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-r', String(fps), '-shortest',
    '-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out], { stdio: 'inherit' });
  fs.rmSync(tmp, { recursive: true, force: true });
  console.log('OK ' + out);
})().catch((e) => { console.error(e); process.exit(1); });
