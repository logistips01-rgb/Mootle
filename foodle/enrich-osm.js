'use strict';

/**
 * Foodle — enriquecido con OpenStreetMap (Nominatim).
 *
 * Para cada restaurante en Firestore que aún no tenga coordenadas, busca su
 * dirección y posición en OpenStreetMap (gratis, sin API key) y se las añade:
 *   - lat, lng   → para mapas y "cómo llegar"
 *   - direccion  → calle + localidad (versión corta y legible)
 *
 * Respeta la norma de Nominatim: 1 consulta/segundo y User-Agent identificativo.
 *
 * Uso:
 *   node foodle/enrich-osm.js              # solo los que faltan
 *   node foodle/enrich-osm.js --refresh    # re-geolocaliza todos
 *
 * Requiere serviceAccount.json (o vars FIREBASE_*). Node 18+.
 */
require('dotenv').config();

const { db } = require('../crawler/firebase-client');

const refresh = process.argv.includes('--refresh');
const NOMINATIM = 'https://nominatim.openstreetmap.org/search';
const HEADERS = {
  // Nominatim exige identificar la aplicación.
  'User-Agent': 'Foodle/1.0 (agregador de restaurantes; foodle.es)',
  'Accept-Language': 'es',
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function geocodificar(nombre, ciudad) {
  const intentos = [
    `${nombre}, ${ciudad}, España`,
    `${nombre} ${ciudad}`,
  ];
  for (const q of intentos) {
    const url = new URL(NOMINATIM);
    url.search = new URLSearchParams({
      q, format: 'json', limit: '1', addressdetails: '1', countrycodes: 'es',
    });
    let data;
    try {
      const r = await fetch(url, { headers: HEADERS });
      data = await r.json();
    } catch (_) { data = null; }
    await sleep(1100); // 1 req/seg (con margen)
    if (Array.isArray(data) && data.length) {
      const hit = data[0];
      const a = hit.address || {};
      const calle = [a.road, a.house_number].filter(Boolean).join(' ');
      const loc = a.city || a.town || a.village || a.municipality || ciudad;
      const direccion = [calle, loc].filter(Boolean).join(', ') || (hit.display_name || '').split(',').slice(0, 2).join(',');
      return { lat: Number(hit.lat), lng: Number(hit.lon), direccion };
    }
  }
  return null;
}

(async () => {
  const snap = await db.collection('restaurants').get();
  const docs = snap.docs.filter((d) => refresh || d.get('lat') == null);
  console.log(`\n🗺️  ${snap.size} restaurantes · a geolocalizar: ${docs.length}${refresh ? ' (refresh)' : ''}\n`);

  let ok = 0, sin = 0, i = 0;
  for (const doc of docs) {
    const r = doc.data();
    i++;
    const geo = await geocodificar(r.nombre, r.ciudad || '');
    if (geo && geo.lat && geo.lng) {
      await doc.ref.set({ ...geo }, { merge: true });
      ok++;
      if (ok <= 8) console.log(`  ✓ ${r.nombre} (${r.ciudad}) → ${geo.direccion}`);
    } else {
      sin++;
    }
    if (i % 20 === 0) console.log(`  …${i}/${docs.length}`);
  }

  console.log(`\n✅ Geolocalizados: ${ok} · sin resultado: ${sin}`);
  console.log('   (Los que no encuentre seguirán sin mapa; es normal que falle un % por nombres ambiguos.)');
  process.exit(0);
})().catch((e) => { console.error('💥 Error:', e.message); process.exit(1); });
