'use strict';

/**
 * Diagnóstico Plan C+ : habla DIRECTAMENTE con la API interna de Wallapop
 * (la misma que usa su web) y nos enseña qué devuelve. NO usa Firecrawl, así
 * que es gratis. Conviene ejecutarlo desde tu propio ordenador (IP doméstica),
 * que es lo que mejor acepta la API.
 *
 * Uso:  node crawler/debug-wallapop-api.js
 *
 * Requiere Node 18+ (usa fetch nativo).
 */

// Coordenadas aproximadas de Madrid (la API suele pedir ubicación).
const LAT = 40.4168;
const LON = -3.7038;

// Cabeceras tipo navegador. Wallapop a veces exige X-DeviceOS.
const HEADERS = {
  Accept: 'application/json, text/plain, */*',
  'Accept-Language': 'es-ES,es;q=0.9',
  'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
  'X-DeviceOS': '0',
  Origin: 'https://es.wallapop.com',
  Referer: 'https://es.wallapop.com/',
};

// Varias combinaciones de endpoint/parámetros, por si alguna está obsoleta.
const VARIANTES = [
  `https://api.wallapop.com/api/v3/general/search?keywords=moto&latitude=${LAT}&longitude=${LON}&category_ids=14000&distance_in_km=400&order_by=newest`,
  `https://api.wallapop.com/api/v3/search?keywords=moto&latitude=${LAT}&longitude=${LON}&category_ids=14000`,
  `https://api.wallapop.com/api/v3/general/search?keywords=moto&latitude=${LAT}&longitude=${LON}`,
];

/**
 * Busca recursivamente el primer array de objetos que parezcan anuncios
 * (tienen título y/o precio), para no depender de la forma exacta del JSON.
 */
function encontrarAnuncios(obj, prof = 0) {
  if (!obj || prof > 6) return null;
  if (Array.isArray(obj)) {
    const pinta = obj.filter(
      (x) => x && typeof x === 'object' && ('title' in x || 'price' in x)
    );
    if (pinta.length) return pinta;
    for (const el of obj) {
      const r = encontrarAnuncios(el, prof + 1);
      if (r) return r;
    }
    return null;
  }
  if (typeof obj === 'object') {
    for (const k of Object.keys(obj)) {
      const r = encontrarAnuncios(obj[k], prof + 1);
      if (r) return r;
    }
  }
  return null;
}

function precioDe(a) {
  if (typeof a.price === 'number') return a.price;
  if (a.price && typeof a.price === 'object') return a.price.amount ?? a.price.cash;
  if (a.sale_price) return a.sale_price;
  return '?';
}

(async () => {
  for (const url of VARIANTES) {
    console.log('\n──────────────────────────────────────────');
    console.log('GET', url.split('?')[0], '\n   params:', url.split('?')[1]);
    try {
      const resp = await fetch(url, { headers: HEADERS });
      console.log('   HTTP', resp.status, resp.headers.get('content-type'));
      if (!resp.ok) {
        const txt = await resp.text();
        console.log('   cuerpo (recorte):', txt.slice(0, 160));
        continue;
      }
      const data = await resp.json();
      console.log('   claves nivel raíz:', Object.keys(data).join(', '));
      const anuncios = encontrarAnuncios(data) || [];
      console.log(`   ✅ anuncios detectados: ${anuncios.length}`);
      anuncios.slice(0, 8).forEach((a, i) => {
        console.log(
          `     ${i + 1}. ${(a.title || '?').slice(0, 50)} | ${precioDe(a)} € | ${
            a.web_slug || a.id || ''
          }`
        );
      });
      if (anuncios.length) {
        console.log('\n   (Estructura del primer anuncio — claves disponibles:)');
        console.log('   ', Object.keys(anuncios[0]).join(', '));
      }
    } catch (e) {
      console.log('   ERROR:', e.message);
    }
  }
  console.log('\nFin del diagnóstico.\n');
})();
