'use strict';

/**
 * Orquestador del crawler de Mootle.
 *
 * Flujo por portal:
 *   1. Firecrawl /map sobre la URL de búsqueda → URLs candidatas.
 *   2. Filtra por patrón de ficha y descarta las URLs ya presentes en BD.
 *   3. Firecrawl /batch/scrape con el schema → datos estructurados.
 *   4. normalize.js → schema común.
 *   5. dedup.js → hash; descarta si ya existe ese hash.
 *   6. Escribe en Firestore (listings/) por lotes.
 *   7. Actualiza portals/{id} con timestamp y métricas.
 *
 * Un error en una URL o en un portal se registra y NO detiene el resto.
 *
 * Uso:  node crawler/index.js [portalId ...]
 *       (sin argumentos = todos los portales)
 */
require('dotenv').config();

const FirecrawlApp = require('@mendable/firecrawl-js').default;
const { admin, db } = require('./firebase-client');
const { PORTALS, EXTRACTION_SCHEMA } = require('./portals');
const { normalizar, esValido } = require('./normalize');
const { generarHash } = require('./dedup');

const MAP_LIMIT = parseInt(process.env.CRAWL_MAP_LIMIT || '100', 10);
const FIRESTORE_BATCH_SIZE = 400; // < 500 por límite de Firestore

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function logPortal(portal, msg) {
  console.log(`[${portal.name}] ${msg}`);
}

/* ───────────────────────── Firestore helpers ───────────────────────── */

/**
 * Devuelve dos Sets con las url_original y los hashes ya guardados de un
 * portal, para no reprocesar ni duplicar.
 */
async function cargarExistentes(portalId) {
  const urls = new Set();
  const hashes = new Set();
  const snap = await db
    .collection('listings')
    .where('portal', '==', portalId)
    .select('url_original')
    .get();
  snap.forEach((doc) => {
    hashes.add(doc.id);
    const u = doc.get('url_original');
    if (u) urls.add(u);
  });
  return { urls, hashes };
}

/**
 * Escribe anuncios en listings/ por lotes. El id del documento es el hash,
 * de modo que un re-crawl actualiza (merge) en vez de duplicar.
 */
async function escribirListings(anuncios) {
  let escritos = 0;
  for (let i = 0; i < anuncios.length; i += FIRESTORE_BATCH_SIZE) {
    const lote = anuncios.slice(i, i + FIRESTORE_BATCH_SIZE);
    const batch = db.batch();
    for (const a of lote) {
      const ref = db.collection('listings').doc(a.id);
      batch.set(ref, a, { merge: true });
    }
    await batch.commit();
    escritos += lote.length;
  }
  return escritos;
}

async function actualizarEstadoPortal(portal, datos) {
  await db
    .collection('portals')
    .doc(portal.id)
    .set(
      {
        name: portal.name,
        ultimo_crawl: admin.firestore.FieldValue.serverTimestamp(),
        ...datos,
      },
      { merge: true }
    );
}

/* ───────────────────────────── Firecrawl ───────────────────────────── */

/**
 * Descubre URLs de ficha de un portal usando /map.
 */
async function descubrirUrls(app, portal) {
  const res = await app.mapUrl(portal.searchUrl, {
    search: portal.mapSearch,
    limit: MAP_LIMIT,
    includeSubdomains: false,
  });
  const links = (res && (res.links || res.data)) || [];
  const urls = links
    .map((l) => (typeof l === 'string' ? l : l && l.url))
    .filter(Boolean);
  // Quedarnos solo con fichas de anuncio según el patrón del portal.
  const fichas = urls.filter((u) => portal.urlPattern.test(u));
  // Únicas.
  return [...new Set(fichas)];
}

/**
 * Extrae datos estructurados de un conjunto de URLs vía /batch/scrape.
 * Devuelve un array de { url, json, metadata } (solo los OK).
 */
async function extraerDatos(app, urls) {
  const res = await app.batchScrapeUrls(urls, {
    formats: ['json'],
    onlyMainContent: true,
    jsonOptions: { schema: EXTRACTION_SCHEMA },
  });

  if (!res || res.success === false) {
    throw new Error(
      `batch/scrape falló: ${(res && res.error) || 'respuesta vacía'}`
    );
  }

  const items = res.data || [];
  return items
    .map((item) => {
      const meta = item.metadata || {};
      const url = meta.sourceURL || meta.url || null;
      const json = item.json || item.extract || null;
      return { url, json, metadata: meta };
    })
    .filter((x) => x.url && x.json);
}

/* ────────────────────────────── por portal ─────────────────────────── */

async function procesarPortal(app, portal) {
  let nuevos = 0;
  let duplicados = 0;
  let errores = 0;

  try {
    const { urls: urlsExistentes, hashes: hashesExistentes } =
      await cargarExistentes(portal.id);

    logPortal(portal, 'descubriendo URLs (/map)…');
    const todas = await descubrirUrls(app, portal);
    const pendientes = todas.filter((u) => !urlsExistentes.has(u));
    logPortal(
      portal,
      `${todas.length} fichas encontradas · ${pendientes.length} nuevas a procesar`
    );

    if (pendientes.length === 0) {
      await actualizarEstadoPortal(portal, {
        nuevos: 0,
        duplicados: 0,
        errores: 0,
        urls_descubiertas: todas.length,
        estado: 'ok',
      });
      logPortal(portal, '0 nuevos anuncios | nada que extraer');
      return { nuevos, duplicados, errores };
    }

    // Respetar el rate limit del portal antes de la extracción masiva.
    await sleep(portal.rateLimit);

    logPortal(portal, `extrayendo datos (/batch/scrape) de ${pendientes.length} URLs…`);
    const extraidos = await extraerDatos(app, pendientes);

    const hashesEsteRun = new Set();
    const paraEscribir = [];

    for (const { url, json, metadata } of extraidos) {
      try {
        const anuncio = normalizar(json, portal, url, metadata);
        if (!esValido(anuncio)) {
          errores += 1;
          continue;
        }
        const hash = generarHash(anuncio);
        if (hashesExistentes.has(hash) || hashesEsteRun.has(hash)) {
          duplicados += 1;
          continue;
        }
        hashesEsteRun.add(hash);
        anuncio.id = hash;
        anuncio.fecha_crawl = new Date().toISOString();
        paraEscribir.push(anuncio);
      } catch (e) {
        errores += 1;
        logPortal(portal, `error normalizando ${url}: ${e.message}`);
      }
    }

    // URLs que se pidieron pero Firecrawl no devolvió con datos = errores.
    errores += pendientes.length - extraidos.length;

    nuevos = await escribirListings(paraEscribir);

    await actualizarEstadoPortal(portal, {
      nuevos,
      duplicados,
      errores,
      urls_descubiertas: todas.length,
      estado: 'ok',
    });
  } catch (e) {
    errores += 1;
    logPortal(portal, `ERROR de portal: ${e.message}`);
    await actualizarEstadoPortal(portal, {
      estado: 'error',
      ultimo_error: e.message,
    }).catch(() => {});
  }

  logPortal(
    portal,
    `${nuevos} nuevos anuncios | ${duplicados} duplicados descartados | ${errores} errores`
  );
  return { nuevos, duplicados, errores };
}

/* ──────────────────────────────── main ─────────────────────────────── */

async function runCrawler(portalIds) {
  const apiKey = process.env.FIRECRAWL_API_KEY;
  if (!apiKey) {
    throw new Error('Falta FIRECRAWL_API_KEY en el entorno (.env).');
  }

  const app = new FirecrawlApp({ apiKey });

  const seleccionados =
    portalIds && portalIds.length
      ? PORTALS.filter((p) => portalIds.includes(p.id))
      : PORTALS;

  if (seleccionados.length === 0) {
    throw new Error(
      `Ningún portal coincide con: ${(portalIds || []).join(', ')}`
    );
  }

  console.log(
    `\n🛵 Mootle crawler — portales: ${seleccionados
      .map((p) => p.id)
      .join(', ')}\n`
  );

  const total = { nuevos: 0, duplicados: 0, errores: 0 };
  for (const portal of seleccionados) {
    const r = await procesarPortal(app, portal);
    total.nuevos += r.nuevos;
    total.duplicados += r.duplicados;
    total.errores += r.errores;
    // Pequeña pausa entre portales.
    await sleep(1000);
  }

  // Métricas globales.
  await db
    .collection('stats')
    .doc('crawler')
    .set(
      {
        ultima_ejecucion: admin.firestore.FieldValue.serverTimestamp(),
        ...total,
      },
      { merge: true }
    )
    .catch((e) => console.error('No se pudieron guardar stats:', e.message));

  console.log(
    `\n✅ Total: ${total.nuevos} nuevos | ${total.duplicados} duplicados | ${total.errores} errores\n`
  );
  return total;
}

module.exports = { runCrawler };

// Ejecución directa por CLI: node crawler/index.js [portalId ...]
if (require.main === module) {
  const args = process.argv.slice(2);
  runCrawler(args)
    .then(() => process.exit(0))
    .catch((e) => {
      console.error('💥 Crawler abortado:', e.message);
      process.exit(1);
    });
}
