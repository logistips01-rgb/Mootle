'use strict';

/**
 * Diagnóstico Plan C (el bueno para portales JS): en vez de descubrir la URL
 * de cada anuncio, renderiza la PÁGINA DE RESULTADOS y pide a Firecrawl que
 * extraiga la LISTA de anuncios visibles (con su título, precio, km, año…).
 *
 * Uso:  node crawler/debug-extract.js [portalId] [stealth]
 *   node crawler/debug-extract.js cochesnet
 *   node crawler/debug-extract.js wallapop stealth
 */
require('dotenv').config();

const FirecrawlApp = require('@mendable/firecrawl-js').default;

const portalId = process.argv[2] || 'cochesnet';
const usarStealth = (process.argv[3] || '').toLowerCase() === 'stealth';
const portal = require('./portals/' + portalId);

// Schema de LISTA: un array de anuncios con los campos clave de cada tarjeta.
const SCHEMA_LISTA = {
  type: 'object',
  properties: {
    anuncios: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          titulo: { type: 'string' },
          marca: { type: 'string' },
          modelo: { type: 'string' },
          precio: { type: 'number' },
          km: { type: 'number' },
          anio: { type: 'number' },
          ubicacion: { type: 'string' },
          url: { type: 'string' },
        },
      },
    },
  },
};

const PROMPT =
  'Esta es una página de resultados de anuncios de motos de segunda mano. ' +
  'Extrae TODOS los anuncios de motos que aparecen listados, uno por cada ' +
  'tarjeta/resultado, con su título, marca, modelo, precio en euros, ' +
  'kilómetros, año, ubicación y la URL del anuncio si está disponible.';

(async () => {
  const apiKey = process.env.FIRECRAWL_API_KEY;
  if (!apiKey) {
    console.error('Falta FIRECRAWL_API_KEY en el .env');
    process.exit(1);
  }

  const app = new FirecrawlApp({ apiKey });

  const opts = {
    formats: ['json'],
    onlyMainContent: false,
    waitFor: 5000,
    jsonOptions: { schema: SCHEMA_LISTA, prompt: PROMPT },
  };
  if (usarStealth) opts.proxy = 'stealth';

  console.log(`\nPortal: ${portalId}${usarStealth ? '  (STEALTH)' : ''}`);
  console.log(`Extrayendo lista de: ${portal.searchUrl}\n`);

  const res = await app.scrapeUrl(portal.searchUrl, opts);
  const json = (res && (res.json || (res.data && res.data.json))) || {};
  const anuncios = json.anuncios || [];

  console.log(`✅ Anuncios extraídos: ${anuncios.length}\n`);
  anuncios.slice(0, 10).forEach((a, i) => {
    console.log(
      `${String(i + 1).padStart(2)}. ${a.titulo || a.marca + ' ' + a.modelo || '?'} ` +
        `| ${a.precio ?? '?'}€ | ${a.km ?? '?'} km | ${a.anio ?? '?'} | ${a.ubicacion ?? '?'}`
    );
  });

  if (anuncios.length === 0) {
    console.log('(0 anuncios — probaremos con stealth o más tiempo de espera.)');
  }
})().catch((e) => {
  console.error('\nERROR:', e.message);
  process.exit(1);
});
