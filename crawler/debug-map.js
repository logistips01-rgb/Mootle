'use strict';

/**
 * Diagnóstico: imprime las URLs que Firecrawl /map devuelve para un portal,
 * y si cada una coincide con el patrón de ficha definido en el portal.
 *
 * Uso:  node crawler/debug-map.js [portalId]
 *       (por defecto: milanuncios)
 */
require('dotenv').config();

const FirecrawlApp = require('@mendable/firecrawl-js').default;

const portalId = process.argv[2] || 'milanuncios';
const portal = require('./portals/' + portalId);

(async () => {
  const apiKey = process.env.FIRECRAWL_API_KEY;
  if (!apiKey) {
    console.error('Falta FIRECRAWL_API_KEY en el .env');
    process.exit(1);
  }

  const app = new FirecrawlApp({ apiKey });

  console.log(`\nMapeando: ${portal.searchUrl}`);
  console.log(`Patrón de ficha: ${portal.urlPattern}\n`);

  // Probamos primero CON el término de búsqueda, y si sale vacío, SIN él.
  let res = await app.mapUrl(portal.searchUrl, {
    search: portal.mapSearch,
    limit: 30,
  });
  let links = (res && (res.links || res.data)) || [];
  let urls = links.map((l) => (typeof l === 'string' ? l : l && l.url)).filter(Boolean);

  if (urls.length === 0) {
    console.log('(0 con search; reintento SIN search…)\n');
    res = await app.mapUrl(portal.searchUrl, { limit: 30 });
    links = (res && (res.links || res.data)) || [];
    urls = links.map((l) => (typeof l === 'string' ? l : l && l.url)).filter(Boolean);
  }

  console.log(`Total de URLs devueltas: ${urls.length}\n`);
  console.log('Primeras 25:');
  urls.slice(0, 25).forEach((u) => {
    console.log(`  ${portal.urlPattern.test(u) ? '✅' : '  '} ${u}`);
  });

  const matches = urls.filter((u) => portal.urlPattern.test(u));
  console.log(`\nCoinciden con el patrón de ficha: ${matches.length} de ${urls.length}`);
})().catch((e) => {
  console.error('\nERROR:', e.message);
  process.exit(1);
});
