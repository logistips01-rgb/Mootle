'use strict';

/**
 * Experimento Foodle — trae los últimos vídeos de UNO O VARIOS canales foodie
 * usando la YouTube Data API v3 (oficial, gratis, sin bloqueos de IP).
 *
 * Saca título + descripción de cada vídeo (que en estos canales ya traen el
 * restaurante, la ciudad y a menudo dirección/precio). Esa salida se la
 * pasamos a la IA para extraer las fichas estructuradas de restaurante.
 *
 * Uso:  node experiments/youtube-foodie.js @canal1 @canal2 ... [nPorCanal]
 *   node experiments/youtube-foodie.js @cenandoconpablo @cocituber 10
 *
 * Requiere en .env:  YOUTUBE_API_KEY=AIza...
 * Requiere Node 18+ (fetch nativo).
 */
require('dotenv').config();

const API = 'https://www.googleapis.com/youtube/v3';

// Separar argumentos: los @handles por un lado, el número (nPorCanal) por otro.
const args = process.argv.slice(2);
let N = 10;
const handles = [];
for (const a of args) {
  if (/^\d+$/.test(a)) N = parseInt(a, 10);
  else handles.push(a.replace(/^@/, ''));
}
if (handles.length === 0) handles.push('cenandoconpablo', 'cocituber');

async function api(path, params) {
  const url = new URL(API + path);
  url.search = new URLSearchParams({ ...params, key: process.env.YOUTUBE_API_KEY });
  const r = await fetch(url);
  const data = await r.json();
  if (!r.ok) {
    const msg = (data.error && data.error.message) || r.status;
    throw new Error(`YouTube API ${path}: ${msg}`);
  }
  return data;
}

async function traerCanal(handle) {
  const ch = await api('/channels', {
    part: 'contentDetails,snippet,statistics',
    forHandle: handle,
  });
  if (!ch.items || !ch.items.length) {
    console.log(`\n⚠️  No se encontró el canal @${handle} — lo salto.\n`);
    return;
  }
  const canal = ch.items[0];
  const uploads = canal.contentDetails.relatedPlaylists.uploads;

  console.log(`\n══════════════════════════════════════════`);
  console.log(
    `CANAL: ${canal.snippet.title}  (@${handle}) · ${Number(
      canal.statistics.subscriberCount || 0
    ).toLocaleString('es-ES')} subs`
  );
  console.log(`══════════════════════════════════════════`);

  const pl = await api('/playlistItems', {
    part: 'snippet',
    playlistId: uploads,
    maxResults: Math.min(N, 50),
  });

  pl.items.forEach((it, i) => {
    const s = it.snippet;
    const vid = s.resourceId.videoId;
    const desc = (s.description || '').replace(/\s+/g, ' ').slice(0, 550);
    console.log(`\n### [${canal.snippet.title}] ${i + 1}. ${s.title}`);
    console.log(`URL: https://youtu.be/${vid}`);
    console.log(`FECHA: ${s.publishedAt.slice(0, 10)}`);
    console.log(`DESCRIPCIÓN: ${desc || '(vacía)'}`);
  });
}

(async () => {
  if (!process.env.YOUTUBE_API_KEY) {
    console.error('Falta YOUTUBE_API_KEY en el .env');
    process.exit(1);
  }
  console.log(`\nFoodle — canales: ${handles.map((h) => '@' + h).join(', ')} · ${N} vídeos c/u`);
  for (const h of handles) {
    try {
      await traerCanal(h);
    } catch (e) {
      console.log(`\nERROR con @${h}: ${e.message}`);
    }
  }
  console.log(
    '\n─────────────────────────────────────────\n' +
      'Copia TODO lo de arriba y pégamelo: lo convierto en fichas Foodle\n' +
      '(restaurante · ciudad · cocina · precio · veredicto · creador) y las\n' +
      'añado al buscador.\n'
  );
})().catch((e) => {
  console.error('\nERROR:', e.message);
  process.exit(1);
});
