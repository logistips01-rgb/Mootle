'use strict';

/**
 * Foodle — extracción automática.
 *
 * Flujo:
 *   1. YouTube Data API → últimos vídeos de uno o varios canales foodie.
 *   2. Por cada vídeo, Claude (Haiku) lee título + descripción y devuelve una
 *      ficha de restaurante estructurada — o marca que NO es un restaurante.
 *   3. Guarda las fichas válidas en un JSON (y, opcionalmente, en Firestore).
 *
 * Uso:
 *   node foodle/extract.js @cenandoconpablo @cocituber 40
 *   node foodle/extract.js @cenandoconpablo 80 --firestore
 *
 * Requiere en .env:
 *   YOUTUBE_API_KEY=AIza...
 *   ANTHROPIC_API_KEY=sk-ant-...
 *   (para --firestore: serviceAccount.json o las vars FIREBASE_*)
 *
 * Node 18+ (fetch nativo).
 */
require('dotenv').config();

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const AnthropicMod = require('@anthropic-ai/sdk');
const Anthropic = AnthropicMod.default || AnthropicMod;

const YT_API = 'https://www.googleapis.com/youtube/v3';

const DATA_DIR = path.join(__dirname, 'data');
const SEEN_FILE = path.join(DATA_DIR, 'seen.json');
const OUT_FILE = path.join(DATA_DIR, 'restaurantes.json');

/** id estable de una ficha: mismo restaurante + ciudad + foodie = misma ficha. */
function hashFicha(r) {
  return crypto
    .createHash('sha1')
    .update(`${(r.nombre || '').toLowerCase()}|${(r.ciudad || '').toLowerCase()}|${(r.creador || '').toLowerCase()}`)
    .digest('hex');
}

function leerJSON(file, porDefecto) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (_) {
    return porDefecto;
  }
}

/* ───────────────────────── argumentos ───────────────────────── */
const args = process.argv.slice(2);
const usarFirestore = args.includes('--firestore');
const reanalizar = args.includes('--reanalyze'); // ignora "ya vistos" y reprocesa todo
let N = 40;
const handles = [];
for (const a of args) {
  if (a === '--firestore' || a === '--reanalyze') continue;
  if (/^\d+$/.test(a)) N = parseInt(a, 10);
  else handles.push(a.replace(/^@/, ''));
}
if (handles.length === 0) handles.push('cenandoconpablo', 'cocituber');

/* ───────────────────────── YouTube ───────────────────────── */
async function yt(pathname, params) {
  const url = new URL(YT_API + pathname);
  url.search = new URLSearchParams({ ...params, key: process.env.YOUTUBE_API_KEY });
  const r = await fetch(url);
  const data = await r.json();
  if (!r.ok) throw new Error(`YouTube ${pathname}: ${(data.error && data.error.message) || r.status}`);
  return data;
}

async function traerVideos(ref, n) {
  // Acepta un id de canal (UC...) o un @handle.
  const esId = /^UC[\w-]{20,}$/.test(ref);
  const ch = await yt('/channels', esId
    ? { part: 'contentDetails,snippet', id: ref }
    : { part: 'contentDetails,snippet', forHandle: ref });
  if (!ch.items || !ch.items.length) {
    console.log(`⚠️  Canal ${esId ? ref : '@' + ref} no encontrado — lo salto.`);
    return [];
  }
  const canal = ch.items[0];
  const uploads = canal.contentDetails.relatedPlaylists.uploads;

  const items = [];
  let pageToken;
  while (items.length < n) {
    const pl = await yt('/playlistItems', {
      part: 'snippet',
      playlistId: uploads,
      maxResults: 50,
      ...(pageToken ? { pageToken } : {}),
    });
    items.push(...pl.items);
    if (!pl.nextPageToken) break;
    pageToken = pl.nextPageToken;
  }

  return items.slice(0, n).map((it) => ({
    creador: canal.snippet.title,
    titulo: it.snippet.title,
    descripcion: (it.snippet.description || '').replace(/\s+/g, ' ').slice(0, 700),
    vid: it.snippet.resourceId.videoId,
    fecha: it.snippet.publishedAt.slice(0, 10),
  }));
}

/* ───────────────────────── Claude (extracción) ───────────────────────── */
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

const SYSTEM = `Eres un extractor de datos para Foodle, un buscador de restaurantes recomendados por foodies.
Te doy el TÍTULO y la DESCRIPCIÓN de un vídeo de un foodie de YouTube. Tu trabajo es decidir si el vídeo
reseña UN restaurante/bar concreto y, si es así, extraer sus datos.

Responde ÚNICAMENTE con un objeto JSON válido (sin texto alrededor, sin markdown) con estos campos:
{
  "es_restaurante": boolean,   // true solo si reseña un local concreto donde comer/beber. false para reflexiones, entrevistas, recetas, vídeos de viaje a otro país, fábricas, o si no se puede identificar el local.
  "nombre": string|null,       // nombre del restaurante/bar
  "ciudad": string|null,       // ciudad o pueblo en España (no barrio). Si solo hay barrio, deja la ciudad.
  "zona": string|null,         // barrio, dirección o referencia ("Castellana 115", "casco antiguo")
  "cocina": string|null,       // una etiqueta corta: Arroces, Marisco, Carnes, Tapas, Asador, Tradicional, Asturiana, Gallega, Extremeña, Alta cocina, Italiana, Hamburguesas, Dulce, Bocadillos, Sin gluten, Internacional...
  "precio": string|null,       // "€", "€€", "€€€" o "€€€€" según lo que sugiera el texto, o null
  "nivel": string|null,        // "top" (entusiasta, brutal, lo mejor), "rec" (positivo), "mix" (regular o con peros), "ver" (no concluye / cliffhanger)
  "veredicto": string|null,    // 1 frase corta resumiendo la opinión, en español, sin comillas
  "tags": string[],            // etiquetas especiales: "📣 Publicidad" SOLO si la reseña del RESTAURANTE está patrocinada (ver regla abajo), "⚠️ ojo a la cuenta", "pet-friendly", "Michelin", "menú X€", etc. Array vacío si no hay.
  "publi": boolean             // true SOLO si el propio RESTAURANTE patrocina/invita la reseña (ver regla)
}

Reglas:
- Si es_restaurante es false, pon el resto de campos a null/[] / false.
- Vídeos de comida en Japón, Corea u otros países: es_restaurante=false (Foodle es de España).
- No inventes datos: si la ciudad no aparece, déjala en null (no la deduzcas a lo loco).
- PUBLICIDAD (¡importante, no te confundas!): publi=true y tag "📣 Publicidad" SOLO cuando el
  RESTAURANTE RESEÑADO es quien paga o invita. Señales válidas: la descripción empieza por "publi"
  refiriéndose al local, etiqueta al restaurante con promoción (@nombredelrestaurante), dice "gracias
  por la invitación", o da un código de descuento DEL PROPIO RESTAURANTE.
  NO es publicidad del restaurante (publi=false, sin tag) cuando el patrocinio es del CANAL y no tiene
  nada que ver con el local: códigos o menciones de proteínas/suplementos (IOGENIX), ropa (pampling),
  bancos (N26, "20€ gratis"), o apps ajenas al restaurante. Esos patrocinios del creador aparecen en
  casi todos sus vídeos y NO deben marcar el restaurante como patrocinado.`;

const SCHEMA = {
  type: 'object',
  additionalProperties: false,
  properties: {
    es_restaurante: { type: 'boolean' },
    nombre: { type: ['string', 'null'] },
    ciudad: { type: ['string', 'null'] },
    zona: { type: ['string', 'null'] },
    cocina: { type: ['string', 'null'] },
    precio: { type: ['string', 'null'] },
    nivel: { type: ['string', 'null'] },
    veredicto: { type: ['string', 'null'] },
    tags: { type: 'array', items: { type: 'string' } },
    publi: { type: 'boolean' },
  },
  required: [
    'es_restaurante', 'nombre', 'ciudad', 'zona', 'cocina',
    'precio', 'nivel', 'veredicto', 'tags', 'publi',
  ],
};

function parseJSON(texto) {
  // Quita posibles vallas de código y recorta al primer objeto JSON.
  const limpio = texto.replace(/```json\s*|\s*```/g, '').trim();
  const ini = limpio.indexOf('{');
  const fin = limpio.lastIndexOf('}');
  if (ini === -1 || fin === -1) throw new Error('sin JSON');
  return JSON.parse(limpio.slice(ini, fin + 1));
}

async function extraer(video) {
  const userMsg = `TÍTULO: ${video.titulo}\nDESCRIPCIÓN: ${video.descripcion || '(vacía)'}`;
  const params = {
    model: 'claude-haiku-4-5',
    max_tokens: 500,
    system: SYSTEM,
    messages: [{ role: 'user', content: userMsg }],
  };

  let datos;
  try {
    // Intento con salida estructurada (si el SDK/modelo lo soporta).
    const resp = await anthropic.messages.create({
      ...params,
      output_config: { format: { type: 'json_schema', schema: SCHEMA } },
    });
    const txt = resp.content.map((b) => (b.type === 'text' ? b.text : '')).join('');
    datos = parseJSON(txt);
  } catch (e) {
    // Fallback: pedir JSON a pelo y parsear.
    const resp = await anthropic.messages.create(params);
    const txt = resp.content.map((b) => (b.type === 'text' ? b.text : '')).join('');
    datos = parseJSON(txt);
  }

  if (!datos.es_restaurante || !datos.nombre) return null;

  return {
    nombre: datos.nombre,
    ciudad: datos.ciudad,
    zona: datos.zona,
    cocina: datos.cocina,
    precio: datos.precio,
    nivel: datos.nivel || 'rec',
    veredicto: datos.veredicto,
    tags: Array.isArray(datos.tags) ? datos.tags : [],
    publi: !!datos.publi,
    creador: video.creador,
    url: `https://youtu.be/${video.vid}`,
    vid: video.vid,
    // Miniatura del vídeo (gratis): la foto que puso el propio foodie.
    imagen: `https://i.ytimg.com/vi/${video.vid}/hqdefault.jpg`,
    fecha: video.fecha,
  };
}

/* Ejecuta tareas con concurrencia limitada. */
async function pool(items, limite, fn) {
  const resultados = [];
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const idx = i++;
      try {
        resultados[idx] = await fn(items[idx], idx);
      } catch (e) {
        resultados[idx] = { __error: e.message };
      }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limite, items.length) }, worker));
  return resultados;
}

/* ───────────────────────── Firestore (opcional) ───────────────────────── */
async function guardarEnFirestore(fichas) {
  const { db } = require('../crawler/firebase-client');
  let escritos = 0;
  for (let i = 0; i < fichas.length; i += 400) {
    const lote = fichas.slice(i, i + 400);
    const batch = db.batch();
    for (const f of lote) {
      const ref = db.collection('restaurants').doc(hashFicha(f));
      batch.set(
        ref,
        { ...f, fecha_extraccion: new Date().toISOString(), activo: true },
        { merge: true }
      );
    }
    await batch.commit();
    escritos += lote.length;
  }
  return escritos;
}

/* ───────────────────────── main ───────────────────────── */
(async () => {
  if (!process.env.YOUTUBE_API_KEY) throw new Error('Falta YOUTUBE_API_KEY en el .env');
  if (!process.env.ANTHROPIC_API_KEY) throw new Error('Falta ANTHROPIC_API_KEY en el .env');

  fs.mkdirSync(DATA_DIR, { recursive: true });
  console.log(`\n🍽️  Foodle extract — canales: ${handles.map((h) => '@' + h).join(', ')} · ${N} vídeos c/u${reanalizar ? ' · (reanalizando todo)' : ''}\n`);

  // 1. Traer vídeos
  let videos = [];
  for (const h of handles) {
    const v = await traerVideos(h, N);
    console.log(`[${h}] ${v.length} vídeos`);
    videos = videos.concat(v);
  }

  // 1b. Filtrar los ya vistos (salvo --reanalyze)
  const seen = new Set(reanalizar ? [] : leerJSON(SEEN_FILE, []));
  const nuevos = videos.filter((v) => !seen.has(v.vid));
  console.log(
    `\nVídeos totales: ${videos.length} · ya vistos: ${videos.length - nuevos.length} · a analizar: ${nuevos.length}\n`
  );

  if (nuevos.length === 0) {
    console.log('No hay vídeos nuevos que analizar. 🎉 (usa --reanalyze para reprocesar todo)');
    process.exit(0);
  }

  // 2. Extraer con Claude (concurrencia 5)
  let procesados = 0;
  const fichas = (await pool(nuevos, 5, async (v) => {
    const ficha = await extraer(v);
    procesados++;
    if (procesados % 10 === 0) process.stdout.write(`  …${procesados}/${nuevos.length}\n`);
    return ficha;
  })).filter((f) => f && !f.__error);

  console.log(`\n✅ ${fichas.length} restaurantes nuevos extraídos de ${nuevos.length} vídeos`);
  console.log(`   (${nuevos.length - fichas.length} descartados: no eran restaurantes o sin nombre)\n`);

  fichas.slice(0, 8).forEach((f, i) =>
    console.log(`  ${i + 1}. ${f.nombre} · ${f.ciudad || '?'} · ${f.cocina || '?'} · ${f.nivel}${f.publi ? ' · 📣' : ''} (${f.creador})`)
  );

  // 3. Marcar como vistos TODOS los analizados (incluidos los descartados, para no repagarlos)
  nuevos.forEach((v) => seen.add(v.vid));
  fs.writeFileSync(SEEN_FILE, JSON.stringify([...seen], null, 2));

  // 4. Acumular en restaurantes.json (dedup por hash; las nuevas pisan a las viejas)
  const previas = leerJSON(OUT_FILE, []);
  const porId = new Map(previas.map((f) => [hashFicha(f), f]));
  for (const f of fichas) porId.set(hashFicha(f), f);
  const todas = [...porId.values()];
  fs.writeFileSync(OUT_FILE, JSON.stringify(todas, null, 2));
  console.log(`\n💾 ${OUT_FILE}`);
  console.log(`   ${fichas.length} nuevas · ${todas.length} en total acumuladas`);

  // 5. Firestore (opcional) — solo las nuevas de esta tanda
  if (usarFirestore) {
    console.log('\nEscribiendo en Firestore (colección "restaurants")…');
    const n = await guardarEnFirestore(fichas);
    console.log(`✅ ${n} fichas escritas/actualizadas en Firestore`);
  } else {
    console.log('\n(Para escribir en Firestore añade --firestore al comando)');
  }
  process.exit(0);
})().catch((e) => {
  console.error('\n💥 Error:', e.message);
  process.exit(1);
});
