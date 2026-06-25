'use strict';

/**
 * Diagnóstico motos.net (motos.coches.net): descarga el HTML de la página de
 * resultados desde TU ordenador (IP doméstica) y busca los anuncios que el
 * sitio incrusta dentro del propio HTML (típico de apps Next.js: __NEXT_DATA__
 * o window.__INITIAL_STATE__). NO usa Firecrawl: es gratis.
 *
 * Uso:  node crawler/debug-motosnet-html.js [url]
 *   (por defecto: https://motos.coches.net/segunda-mano/)
 *
 * Requiere Node 18+ (fetch nativo).
 */

const URL_OBJETIVO =
  process.argv[2] || 'https://motos.coches.net/segunda-mano/';

const HEADERS = {
  'User-Agent':
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
  Accept:
    'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
  'Accept-Language': 'es-ES,es;q=0.9',
  'Upgrade-Insecure-Requests': '1',
  'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"Windows"',
};

/** Busca recursivamente el primer array de objetos que parezcan anuncios. */
function encontrarAnuncios(obj, prof = 0) {
  if (!obj || prof > 8) return null;
  if (Array.isArray(obj)) {
    const pinta = obj.filter(
      (x) =>
        x &&
        typeof x === 'object' &&
        ('price' in x || 'title' in x || 'make' in x || 'km' in x)
    );
    if (pinta.length >= 3) return pinta;
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

(async () => {
  console.log(`\nDescargando HTML de: ${URL_OBJETIVO}\n`);

  let resp;
  try {
    resp = await fetch(URL_OBJETIVO, { headers: HEADERS, redirect: 'follow' });
  } catch (e) {
    console.error('ERROR de red:', e.message);
    process.exit(1);
  }

  console.log('HTTP', resp.status, resp.headers.get('content-type'));
  const html = await resp.text();
  console.log('Tamaño del HTML:', html.length, 'caracteres');

  if (resp.status !== 200) {
    console.log('Recorte:', html.slice(0, 200));
    console.log('\n(Si es 403, el sitio bloquea peticiones sin navegador.)');
    return;
  }

  // Pistas de que los datos están dentro del HTML.
  for (const marca of ['__NEXT_DATA__', '__INITIAL_STATE__', 'application/ld+json', 'window.__']) {
    console.log(`  contiene "${marca}":`, html.includes(marca));
  }

  // Intento 1: bloque __NEXT_DATA__ (Next.js).
  const m = html.match(
    /<script id="__NEXT_DATA__"[^>]*>([\s\S]*?)<\/script>/
  );
  if (m) {
    try {
      const data = JSON.parse(m[1]);
      const anuncios = encontrarAnuncios(data) || [];
      console.log(`\n✅ __NEXT_DATA__ parseado · anuncios detectados: ${anuncios.length}`);
      anuncios.slice(0, 8).forEach((a, i) =>
        console.log(`  ${i + 1}.`, JSON.stringify(a).slice(0, 140))
      );
      if (anuncios.length) {
        console.log('\nClaves del primer anuncio:', Object.keys(anuncios[0]).join(', '));
      }
      return;
    } catch (e) {
      console.log('No se pudo parsear __NEXT_DATA__:', e.message);
    }
  }

  // Intento 2: bloques JSON-LD (schema.org) — a veces traen los productos.
  const ld = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)];
  console.log(`\nBloques JSON-LD encontrados: ${ld.length}`);

  // Pista bruta: ¿cuántos precios "€" hay en el HTML?
  const precios = (html.match(/\d[\d.]*\s?€/g) || []).length;
  console.log(`Apariciones de precios (…€) en el HTML: ${precios}`);

  // (A) ¿Qué variables window.__XXXX__ hay? (donde suele ir el estado)
  const vars = [...new Set((html.match(/window\.__[A-Za-z0-9_]+/g) || []))];
  console.log('\nVariables window.* encontradas:', vars.join(', ') || '(ninguna)');

  // (B) ¿Hay pistas de datos estructurados de anuncios en algún <script>?
  const pistas = ['"price"', '"make"', '"model"', 'precio', 'kilometers', '"ads"', '"items"', '"results"'];
  console.log('\nPistas de datos en el HTML:');
  pistas.forEach((p) => console.log(`  ${p}:`, html.includes(p)));

  // (C) Contexto alrededor de los 3 primeros precios, para ver la estructura
  //     (¿están en tarjetas HTML o dentro de un JSON?).
  console.log('\n── Contexto de los primeros precios (300 chars antes/después) ──');
  const re = /\d[\d.]*\s?€/g;
  let mm, n = 0;
  while ((mm = re.exec(html)) && n < 3) {
    const ini = Math.max(0, mm.index - 300);
    const frag = html.slice(ini, mm.index + 40).replace(/\s+/g, ' ');
    console.log(`\n[precio ${n + 1}] …${frag}…`);
    n++;
  }
})();
