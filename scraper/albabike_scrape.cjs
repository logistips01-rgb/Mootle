// Lee el catálogo de equipación de Albabike (web Vue, hay que renderizar) y escribe
// data/albabike_raw.json con {categoria: [{href, title, newp, oldp, img}]}.
// Recorre cada categoría y sus páginas de fabricante (cada listado trae ~30 productos
// con precio). Pausas educadas y tope de renders. Uso: node scraper/albabike_scrape.cjs
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, '..', 'data', 'albabike_raw.json');
const CATS = [
  ['casco',    'https://albabike.com/motos/cascos-732-c.html'],
  ['chaqueta', 'https://albabike.com/motos/chaquetas-733-c.html'],
  ['guantes',  'https://albabike.com/motos/guantes-734-c.html'],
  ['pantalon', 'https://albabike.com/motos/pantalones-736-c.html'],
  ['botas',    'https://albabike.com/motos/botas-731-c.html'],
];
const MAX_RENDERS = 400;
const grab = page => page.evaluate(() => {
  const res = [], seen = new Set();
  for (const h3 of document.querySelectorAll('a[href*="-p.html"] h3')) {
    const link = h3.closest('a[href*="-p.html"]'); const href = link.getAttribute('href');
    if (seen.has(href)) continue; seen.add(href);
    let card = link;
    for (let i=0;i<5 && card && !card.querySelector('.new_price, .old_price');i++) card = card.parentElement;
    card = card || link.parentElement;
    const q = s => { const e = card.querySelector(s); return e ? e.textContent.trim() : ''; };
    const imgEl = card.querySelector('img');
    const img = imgEl ? (imgEl.getAttribute('data-src') || imgEl.getAttribute('src') || '') : '';
    res.push({ href, title: h3.textContent.trim(), newp: q('.new_price'), oldp: q('.old_price'), img });
  }
  return res;
});
(async () => {
  const b = await chromium.launch(); const out = {}; let renders = 0;
  for (const [cat, url] of CATS) {
    const p = await b.newPage(); const byHref = new Map();
    try {
      await p.goto(url, { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(1500); renders++;
      for (const it of await grab(p)) byHref.set(it.href, it);
      const brands = await p.evaluate(() => [...document.querySelectorAll('a[href*="/fabricante/"]')].map(a=>a.getAttribute('href')).filter((v,i,s)=>s.indexOf(v)===i));
      for (const bu of brands) {
        if (renders >= MAX_RENDERS) break;
        const full = bu.startsWith('http') ? bu : 'https://albabike.com'+bu;
        try {
          await new Promise(r=>setTimeout(r,2000));
          await p.goto(full, { waitUntil:'networkidle', timeout:60000 }); await p.waitForTimeout(1000); renders++;
          for (const it of await grab(p)) if(!byHref.has(it.href)) byHref.set(it.href, it);
        } catch(e){}
      }
    } catch(e){ console.error(cat,'ERR',e.message); }
    out[cat] = [...byHref.values()];
    console.error(`${cat}: ${out[cat].length} productos (renders ${renders})`);
    await p.close(); await new Promise(r=>setTimeout(r,1500));
  }
  await b.close();
  fs.writeFileSync(OUT, JSON.stringify(out));
  console.error('OK · total', Object.values(out).reduce((a,v)=>a+v.length,0), '· renders', renders);
})().catch(e=>{console.error('FATAL',e.message);process.exit(1);});
