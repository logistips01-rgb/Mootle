'use strict';

/**
 * Diagnóstico Plan B: renderiza la página de resultados con Firecrawl /scrape
 * (ejecutando su JS) y extrae TODOS los enlaces, analizando cuáles parecen
 * fichas de anuncio.
 *
 * Uso:  node crawler/debug-links.js [portalId] [stealth]
 *   - portalId : milanuncios | wallapop | cochesnet  (def. milanuncios)
 *   - stealth  : añade la palabra "stealth" para activar proxy anti-detección
 *
 * Ejemplos:
 *   node crawler/debug-links.js cochesnet
 *   node crawler/debug-links.js milanuncios stealth
 */
require('dotenv').config();

const FirecrawlApp = require('@mendable/firecrawl-js').default;

const portalId = process.argv[2] || 'milanuncios';
const usarStealth = (process.argv[3] || '').toLowerCase() === 'stealth';
const portal = require('./portals/' + portalId);

const dominioRe = new RegExp(
  portalId === 'cochesnet' ? 'coches\\.net' : portalId.replace(/[^a-z]/gi, ''),
  'i'
);
const ID_NUMERICO = /\d{6,}/;

(async () => {
  const apiKey = process.env.FIRECRAWL_API_KEY;
  if (!apiKey) {
    console.error('Falta FIRECRAWL_API_KEY en el .env');
    process.exit(1);
  }

  const app = new FirecrawlApp({ apiKey });

  const opts = { formats: ['links'], onlyMainContent: false, waitFor: 4000 };
  if (usarStealth) opts.proxy = 'stealth';

  console.log(`\nPortal: ${portalId}${usarStealth ? '  (modo STEALTH)' : ''}`);
  console.log(`Renderizando: ${portal.searchUrl}\n`);

  const res = await app.scrapeUrl(portal.searchUrl, opts);
  const links = (res && (res.links || (res.data && res.data.links))) || [];

  const delPortal = links.filter((u) => dominioRe.test(u));
  const porPatron = links.filter((u) => portal.urlPattern.test(u));
  const porId = delPortal.filter((u) => ID_NUMERICO.test(u));

  console.log(`Enlaces totales:                 ${links.length}`);
  console.log(`  · del propio portal:           ${delPortal.length}`);
  console.log(`  · que casan el patrón actual:  ${porPatron.length}`);
  console.log(`  · con id numérico (6+):        ${porId.length}\n`);

  console.log('Muestra de enlaces del portal (para ver el formato real):');
  (delPortal.length ? delPortal : links).slice(0, 30).forEach((u) =>
    console.log(`  ${portal.urlPattern.test(u) ? '✅' : '  '} ${u}`)
  );
})().catch((e) => {
  console.error('\nERROR:', e.message);
  process.exit(1);
});
