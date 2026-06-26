'use strict';

/**
 * Foodle — enriquecido por transcripción del vídeo.
 *
 * Para cada restaurante con `vid`, baja la transcripción del vídeo de YouTube
 * (gratis, sin API key) y la pasa por Claude (Haiku) para extraer detalle que
 * el título/descripción no tienen:
 *   - platos        → platos concretos que prueba/destaca
 *   - precio_aprox  → cuánto costó / ticket, si lo dice
 *   - resumen       → opinión más rica (1-2 frases)
 *   - destacado     → el plato estrella
 *
 * Idempotente: solo procesa los que aún no tienen transcripción analizada
 * (campo `tr`); usa --refresh para reprocesar todos.
 *
 * Uso:
 *   node foodle/enrich-transcript.js
 *   node foodle/enrich-transcript.js --refresh
 *
 * Requiere ANTHROPIC_API_KEY en .env y serviceAccount.json. Node 18+.
 */
require('dotenv').config();

const AnthropicMod = require('@anthropic-ai/sdk');
const Anthropic = AnthropicMod.default || AnthropicMod;
const { YoutubeTranscript } = require('youtube-transcript');
const { db } = require('../crawler/firebase-client');

const refresh = process.argv.includes('--refresh');
const anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });

function sysPrompt(nombre, ciudad) {
  return `Eres un extractor para Foodle. Te doy la TRANSCRIPCIÓN automática (puede tener erratas) de un vídeo en el que un foodie reseña el restaurante "${nombre}"${ciudad ? ' en ' + ciudad : ''}. Extrae SOLO lo que se diga de ese restaurante y su comida.

Responde ÚNICAMENTE con un objeto JSON válido (sin markdown):
{
  "platos": string[],          // platos concretos que prueba o destaca (máx 6, nombres cortos en español)
  "precio_aprox": string|null, // si menciona lo que costó o el ticket (ej. "unos 30€", "menú 15€"); si no, null
  "resumen": string|null,      // 1-2 frases naturales con su opinión y por qué; si no hay material, null
  "destacado": string|null     // el plato estrella o lo más memorable; si no, null
}
Reglas: NO inventes platos ni precios que no se mencionen. Si la transcripción no habla claramente de comida/restaurante, devuelve {"platos":[],"precio_aprox":null,"resumen":null,"destacado":null}.`;
}

function parseJSON(texto) {
  const limpio = texto.replace(/```json\s*|\s*```/g, '').trim();
  const i = limpio.indexOf('{'), j = limpio.lastIndexOf('}');
  if (i === -1 || j === -1) throw new Error('sin JSON');
  return JSON.parse(limpio.slice(i, j + 1));
}

async function transcripcion(vid) {
  for (const opts of [{ lang: 'es' }, undefined]) {
    try {
      const items = await YoutubeTranscript.fetchTranscript(vid, opts);
      if (items && items.length) return items.map((x) => x.text).join(' ');
    } catch (_) { /* sin subtítulos en ese idioma; probamos el siguiente */ }
  }
  return null;
}

async function analizar(r) {
  const texto = await transcripcion(r.vid);
  if (!texto) return { sinTranscripcion: true };
  const recorte = texto.replace(/\s+/g, ' ').slice(0, 6000);

  const resp = await anthropic.messages.create({
    model: 'claude-haiku-4-5',
    max_tokens: 500,
    system: sysPrompt(r.nombre, r.ciudad),
    messages: [{ role: 'user', content: recorte }],
  });
  const txt = resp.content.map((b) => (b.type === 'text' ? b.text : '')).join('');
  const d = parseJSON(txt);
  return {
    platos: Array.isArray(d.platos) ? d.platos.slice(0, 6) : [],
    precio_aprox: d.precio_aprox || null,
    resumen: d.resumen || null,
    destacado: d.destacado || null,
  };
}

async function pool(items, limite, fn) {
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const idx = i++;
      try { await fn(items[idx], idx); } catch (e) { /* sigue */ }
    }
  }
  await Promise.all(Array.from({ length: Math.min(limite, items.length) }, worker));
}

(async () => {
  if (!process.env.ANTHROPIC_API_KEY) throw new Error('Falta ANTHROPIC_API_KEY en el .env');

  const snap = await db.collection('restaurants').get();
  const docs = snap.docs.filter((d) => d.get('vid') && (refresh || d.get('tr') !== true));
  console.log(`\n🎙️  ${snap.size} restaurantes · con transcripción por analizar: ${docs.length}${refresh ? ' (refresh)' : ''}\n`);

  let con = 0, sin = 0, hechos = 0, muestras = 0;
  await pool(docs, 3, async (doc) => {
    const r = doc.data();
    const res = await analizar(r);
    hechos++;
    if (res.sinTranscripcion) {
      sin++;
      await doc.ref.set({ tr: true }, { merge: true }); // marcado para no reintentar
    } else {
      con++;
      await doc.ref.set({ ...res, tr: true }, { merge: true });
      if (muestras < 8) {
        console.log(`  ✓ ${r.nombre}: ${(res.platos || []).slice(0, 3).join(', ') || '—'}${res.precio_aprox ? ' · ' + res.precio_aprox : ''}`);
        muestras++;
      }
    }
    if (hechos % 20 === 0) console.log(`  …${hechos}/${docs.length}`);
  });

  console.log(`\n✅ Con transcripción: ${con} · sin subtítulos: ${sin}`);
  console.log('   (YouTube no siempre tiene subtítulos; esos se quedan con la info básica.)');
  process.exit(0);
})().catch((e) => { console.error('💥 Error:', e.message); process.exit(1); });
