'use strict';

/**
 * Experimento Foodle — paso 1: traer los últimos vídeos de un canal foodie
 * usando la YouTube Data API v3 (oficial, gratis, sin bloqueos de IP).
 *
 * Saca título + descripción de cada vídeo, que en canales como
 * "Cenando con Pablo" ya contienen el restaurante, la ciudad y a menudo
 * dirección/precio. Luego esa salida se la pasamos a la IA para extraer la
 * ficha estructurada (nombre, zona, cocina, precio, veredicto).
 *
 * Uso:  node experiments/youtube-foodie.js [@handle] [nVideos]
 *   node experiments/youtube-foodie.js @cenandoconpablo 15
 *
 * Requiere en .env:  YOUTUBE_API_KEY=AIza...
 * Requiere Node 18+ (fetch nativo).
 */
require('dotenv').config();

const API = 'https://www.googleapis.com/youtube/v3';
const handle = (process.argv[2] || '@cenandoconpablo').replace(/^@/, '');
const N = parseInt(process.argv[3] || '15', 10);

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

(async () => {
  if (!process.env.YOUTUBE_API_KEY) {
    console.error('Falta YOUTUBE_API_KEY en el .env');
    process.exit(1);
  }

  // 1) Resolver el canal por su @handle → playlist de subidas.
  console.log(`\nBuscando canal @${handle}…`);
  const ch = await api('/channels', {
    part: 'contentDetails,snippet,statistics',
    forHandle: handle,
  });
  if (!ch.items || !ch.items.length) {
    throw new Error(`No se encontró el canal @${handle}`);
  }
  const canal = ch.items[0];
  const uploads = canal.contentDetails.relatedPlaylists.uploads;
  console.log(
    `Canal: ${canal.snippet.title} · ${Number(
      canal.statistics.subscriberCount || 0
    ).toLocaleString('es-ES')} subs · ${canal.statistics.videoCount} vídeos\n`
  );

  // 2) Traer los últimos N vídeos (título + descripción).
  const pl = await api('/playlistItems', {
    part: 'snippet',
    playlistId: uploads,
    maxResults: Math.min(N, 50),
  });

  console.log(`──────── Últimos ${pl.items.length} vídeos ────────\n`);
  pl.items.forEach((it, i) => {
    const s = it.snippet;
    const vid = s.resourceId.videoId;
    const desc = (s.description || '').replace(/\s+/g, ' ').slice(0, 600);
    console.log(`### ${i + 1}. ${s.title}`);
    console.log(`URL: https://youtu.be/${vid}`);
    console.log(`FECHA: ${s.publishedAt.slice(0, 10)}`);
    console.log(`DESCRIPCIÓN: ${desc}`);
    console.log('');
  });

  console.log(
    '─────────────────────────────────────────\n' +
      'Copia TODO lo de arriba y pégamelo en el chat: yo lo convierto en\n' +
      'las fichas Foodle (restaurante · zona · cocina · precio · veredicto)\n' +
      'y vemos si la extracción es fiable.\n'
  );
})().catch((e) => {
  console.error('\nERROR:', e.message);
  process.exit(1);
});
