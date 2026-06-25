'use strict';

/**
 * Diagnóstico Plan B: en lugar de /map, renderiza la página de resultados con
 * Firecrawl /scrape (ejecutando su JS) y extrae TODOS los enlaces, filtrando
 * los que parecen fichas de anuncio (con un id numérico largo antes de .htm).
 *
 * Uso:  node crawler/debug-links.js [portalId]
 */
require('dotenv').config();

const FirecrawlApp = require('@mendable/firecrawl-js').default;

const portalId = process.argv[2] || 'milanuncios';
const portal = require('./portals/' + portalId);

// Heurística genérica de "ficha de anuncio": id numérico de 6+ dígitos.
const ID_NUMERICO = /\d{6,}/;

(async () => {
  const apiKey = process.env.FIRECRAWL_API_KEY;
  if (!apiKey) {
    console.error('Falta FIRECRAWL_API_KEY en el .env');
    process.exit(1);
  }

  const app = new FirecrawlApp({ apiKey });

  console.log(`\nRenderizando (con JS) la página de resultados:`);
  console.log(`  ${portal.searchUrl}\n`);

  const res = await app.scrapeUrl(portal.searchUrl, {
    formats: ['links'],
    onlyMainContent: false,
    waitFor: 4000,
  });

  // El SDK puede devolver los enlaces en .links o en .data.links.
  const links =
    (res && (res.links || (res.data && res.data.links))) || [];

  console.log(`Enlaces totales en la página: ${links.length}`);

  const delPortal = links.filter((u) =>
    new RegExp(portalId === 'cochesnet' ? 'coches\\.net' : portalId, 'i').test(u)
  );
  const fichas = links.filter(
    (u) => /\.htm/i.test(u) && ID_NUMERICO.test(u)
  );

  console.log(`Enlaces del propio portal: ${delPortal.length}`);
  console.log(`Posibles fichas (con id numérico): ${fichas.length}\n`);

  console.log('Muestra de posibles fichas:');
  fichas.slice(0, 25).forEach((u) => console.log(`  ${u}`));

  if (fichas.length === 0) {
    console.log('\n(Ninguna ficha detectada — muestra de los primeros enlaces:)');
    links.slice(0, 25).forEach((u) => console.log(`  ${u}`));
  }
})().catch((e) => {
  console.error('\nERROR:', e.message);
  process.exit(1);
});
