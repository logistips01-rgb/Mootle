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

  // (A0) Conteo de elementos clave de las tarjetas en el HTML.
  const cuenta = (re) => (html.match(re) || []).length;
  console.log('\n── Conteo de tarjetas en el HTML ──');
  console.log('  contenedores mt-ListAds-item:   ', cuenta(/mt-ListAds-item/g));
  console.log('  contenedores mt-CardAd:         ', cuenta(/mt-CardAd[ "]/g));
  console.log('  títulos (infoHeaderTitleLink):  ', cuenta(/mt-CardAd-infoHeaderTitleLink/g));
  console.log('  precios (cashAmount):           ', cuenta(/mt-CardAdPrice-cashAmount/g));
  console.log('  enlaces de ficha (…\\d+.htm):    ',
    cuenta(/href="\/(?:ocasion|segunda-mano)\/[^"]*\d{5,}\.htm"/g));

  // (A) ¿Qué variables window.__XXXX__ hay? (donde suele ir el estado)
  const vars = [...new Set((html.match(/window\.__[A-Za-z0-9_]+/g) || []))];
  console.log('\nVariables window.* encontradas:', vars.join(', ') || '(ninguna)');

  // (B) ¿Hay pistas de datos estructurados de anuncios en algún <script>?
  const pistas = ['"price"', '"make"', '"model"', 'precio', 'kilometers', '"ads"', '"items"', '"results"'];
  console.log('\nPistas de datos en el HTML:');
  pistas.forEach((p) => console.log(`  ${p}:`, html.includes(p)));

  // (C) Intentar extraer el JSON de window.__INITIAL_PROPS__ / __INITIAL_CONTEXT_VALUE__
  for (const v of ['window.__INITIAL_PROPS__', 'window.__INITIAL_CONTEXT_VALUE__']) {
    const data = extraerAsignacion(html, v);
    if (!data) {
      console.log(`\n${v}: no se pudo extraer/parsear.`);
      continue;
    }
    console.log(`\n${v}: parseado ✅  claves raíz: ${Object.keys(data).join(', ').slice(0, 200)}`);
    const arr = arrayMasGrande(data);
    if (arr) {
      console.log(`  → array más grande: ${arr.length} elementos`);
      if (arr[0] && typeof arr[0] === 'object') {
        console.log('  → claves del 1er elemento:', Object.keys(arr[0]).join(', ').slice(0, 300));
        console.log('  → muestra:', JSON.stringify(arr[0]).slice(0, 300));
      }
    }
  }

  // (D) Volcar UNA tarjeta HTML completa (fallback fiable).
  const ci = html.indexOf('mt-CardAd');
  if (ci >= 0) {
    const ini = html.lastIndexOf('<', ci);
    const frag = html.slice(ini, ini + 1600).replace(/\s+/g, ' ');
    console.log('\n── Una tarjeta HTML (mt-CardAd), recorte de 1600 chars ──');
    console.log(frag);
  }
})();

/** Extrae el objeto JSON asignado a una variable (maneja `= {…}` y `= JSON.parse("…")`). */
function extraerAsignacion(html, varName) {
  const i = html.indexOf(varName);
  if (i < 0) return null;
  const eq = html.indexOf('=', i);
  if (eq < 0) return null;
  let j = eq + 1;
  while (j < html.length && /\s/.test(html[j])) j++;

  if (html.startsWith('JSON.parse(', j)) {
    j += 'JSON.parse('.length;
    const q = html[j];
    let k = j + 1, out = '';
    while (k < html.length) {
      if (html[k] === '\\') { out += html[k] + (html[k + 1] || ''); k += 2; continue; }
      if (html[k] === q) break;
      out += html[k]; k++;
    }
    try { return JSON.parse(JSON.parse(q + out + q)); } catch (e) { return null; }
  }

  if (html[j] === '{') {
    let depth = 0, k = j, inStr = false, q = '';
    for (; k < html.length; k++) {
      const c = html[k];
      if (inStr) { if (c === '\\') { k++; continue; } if (c === q) inStr = false; continue; }
      if (c === '"' || c === "'") { inStr = true; q = c; continue; }
      if (c === '{') depth++;
      else if (c === '}') { depth--; if (depth === 0) { k++; break; } }
    }
    try { return JSON.parse(html.slice(j, k)); } catch (e) { return null; }
  }
  return null;
}

/** Devuelve el array de objetos más grande dentro de una estructura. */
function arrayMasGrande(obj, mejor = { len: 0, arr: null }, prof = 0) {
  if (!obj || prof > 8) return mejor.arr;
  if (Array.isArray(obj)) {
    if (obj.length > mejor.len && obj.some((x) => x && typeof x === 'object')) {
      mejor.len = obj.length; mejor.arr = obj;
    }
    obj.forEach((el) => arrayMasGrande(el, mejor, prof + 1));
  } else if (typeof obj === 'object') {
    Object.values(obj).forEach((v) => arrayMasGrande(v, mejor, prof + 1));
  }
  return mejor.arr;
}
