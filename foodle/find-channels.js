'use strict';

/**
 * Foodle — buscador de canales foodie por ciudad.
 *
 * Usa la API de búsqueda de YouTube para encontrar canales de reseñas de
 * restaurantes en cada ciudad y te devuelve sus DATOS REALES (nombre, handle
 * o id de canal, suscriptores, nº de vídeos). Tú revisas la lista y eliges
 * cuáles meter en el extractor. No inventa nada.
 *
 * Uso:
 *   node foodle/find-channels.js                       # ciudades por defecto, 3 por ciudad
 *   node foodle/find-channels.js Madrid Bilbao 5       # ciudades concretas, 5 por ciudad
 *
 * Requiere YOUTUBE_API_KEY en el .env. (Ojo: /search gasta 100 de cuota por
 * llamada; con ~12 ciudades sigues muy por debajo del límite diario de 10.000.)
 */
require('dotenv').config();

const fs = require('fs');
const path = require('path');

const YT = 'https://www.googleapis.com/youtube/v3';

const args = process.argv.slice(2);
let porCiudad = 3;
const ciudades = [];
for (const a of args) {
  if (/^\d+$/.test(a)) porCiudad = parseInt(a, 10);
  else ciudades.push(a);
}
if (ciudades.length === 0) {
  ciudades.push(
    'Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao', 'Málaga',
    'Zaragoza', 'Granada', 'Alicante', 'Murcia', 'A Coruña', 'Oviedo'
  );
}

async function yt(pathname, params) {
  const url = new URL(YT + pathname);
  url.search = new URLSearchParams({ ...params, key: process.env.YOUTUBE_API_KEY });
  const r = await fetch(url);
  const data = await r.json();
  if (!r.ok) throw new Error(`${pathname}: ${(data.error && data.error.message) || r.status}`);
  return data;
}

async function buscarCiudad(ciudad) {
  // Buscamos VÍDEOS de reseña (no canales): da mucha mejor señal de quién
  // hace de verdad reseñas de restaurantes en esa ciudad.
  const s = await yt('/search', {
    part: 'snippet',
    type: 'video',
    q: `reseña restaurante dónde comer ${ciudad}`,
    maxResults: 25,
    regionCode: 'ES',
    relevanceLanguage: 'es',
  });

  // Contamos cuántos vídeos de reseña aporta cada canal (frecuencia = señal).
  const freq = new Map();
  for (const it of s.items || []) {
    const id = it.snippet && it.snippet.channelId;
    if (id) freq.set(id, (freq.get(id) || 0) + 1);
  }
  const ids = [...freq.keys()];
  if (!ids.length) return [];

  const ch = await yt('/channels', { part: 'snippet,statistics', id: ids.join(',') });
  let canales = (ch.items || []).map((c) => ({
    title: c.snippet.title,
    handle: c.snippet.customUrl ? c.snippet.customUrl.replace(/^@/, '') : null,
    id: c.id,
    subs: Number(c.statistics.subscriberCount || 0),
    videos: Number(c.statistics.videoCount || 0),
    freq: freq.get(c.id) || 0,
  }));

  // Filtra el ruido: fuera mega-canales (generalistas), radios/TV con miles de
  // vídeos, y canales demasiado pequeños/de un solo vídeo.
  canales = canales.filter((c) => c.subs <= 1500000 && c.videos >= 15 && c.videos <= 4000);

  // Ordena por frecuencia de reseñas (lo relevante), y a igualdad por subs.
  canales.sort((a, b) => b.freq - a.freq || b.subs - a.subs);
  return canales.slice(0, porCiudad);
}

(async () => {
  if (!process.env.YOUTUBE_API_KEY) throw new Error('Falta YOUTUBE_API_KEY en el .env');

  console.log(`\n🔎 Buscando ~${porCiudad} canales por ciudad: ${ciudades.join(', ')}\n`);
  const todo = {};
  for (const c of ciudades) {
    try {
      const lista = await buscarCiudad(c);
      todo[c] = lista;
      console.log(`\n📍 ${c}`);
      if (!lista.length) { console.log('   (sin resultados)'); continue; }
      lista.forEach((x, i) => {
        const ref = x.handle ? '@' + x.handle : x.id;
        console.log(`   ${i + 1}. ${x.title}  →  ${ref}  ·  ${x.subs.toLocaleString('es-ES')} subs · ${x.videos} vídeos`);
      });
    } catch (e) {
      console.log(`\n📍 ${c} — ERROR: ${e.message}`);
    }
  }

  const dir = path.join(__dirname, 'data');
  fs.mkdirSync(dir, { recursive: true });
  const out = path.join(dir, 'candidatos.json');
  fs.writeFileSync(out, JSON.stringify(todo, null, 2));

  const refs = [...new Set(Object.values(todo).flat().map((x) => (x.handle ? '@' + x.handle : x.id)))];
  console.log(`\n💾 ${out}`);
  console.log('\n👉 Revisa la lista (quita los que no sean reseñas de restaurantes) y extrae los buenos así:\n');
  console.log(`   node foodle/extract.js ${refs.slice(0, 8).join(' ')} 40 --firestore`);
  console.log('\n(El extractor acepta tanto @handles como ids de canal UC...; los que no encuentre, los salta.)');
  process.exit(0);
})().catch((e) => { console.error('Error:', e.message); process.exit(1); });
