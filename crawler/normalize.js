'use strict';

/**
 * Normaliza los datos crudos extraídos por Firecrawl al schema común de
 * Mootle. Cualquier campo que no se pueda determinar queda como `null`
 * (nunca se omite).
 */

const MARCAS_CONOCIDAS = [
  'Honda', 'Yamaha', 'Suzuki', 'Kawasaki', 'BMW', 'Ducati', 'KTM',
  'Triumph', 'Harley-Davidson', 'Harley Davidson', 'Aprilia', 'Vespa',
  'Piaggio', 'Kymco', 'SYM', 'Royal Enfield', 'Husqvarna', 'Benelli',
  'MV Agusta', 'Moto Guzzi', 'Indian', 'Gas Gas', 'GasGas', 'Derbi',
  'Rieju', 'Beta', 'Sherco', 'Montesa', 'Bultaco', 'Peugeot', 'Daelim',
  'CFMoto', 'CF Moto', 'Zontes', 'Voge', 'Keeway', 'Macbor', 'Hanway',
  'Mitt', 'Brixton', 'Fantic', 'Lambretta', 'Scomadi', 'Mash', 'UM',
];

const TIPOS = ['naked', 'trail', 'deportiva', 'custom', 'scooter'];

// Pistas de texto → tipo de moto (orden importa: la primera que casa gana).
// Borde de palabra solo al INICIO de cada token: los códigos de modelo mezclan
// letras y dígitos (CB650F, CBR600RR) y un \b final cortaría la coincidencia.
const PISTAS_TIPO = [
  { tipo: 'scooter', re: /\b(?:scooter|scoot|maxiscooter|tmax|t-max|xmax|x-max|burgman|forza|pcx|sh\d{3}|nmax|vespa|primavera|liberty)/i },
  { tipo: 'trail', re: /\b(?:trail|adventure|gs\b|enduro|africa\s?twin|tenere|ténéré|transalp|v-?strom|tiger|multistrada|crosstourer|versys|tracer)/i },
  { tipo: 'deportiva', re: /\b(?:deportiva|fireblade|cbr|gsx-?r|zx-?\d|panigale|rsv4|ninja|supersport|superbike|r1\b|r6\b|rr\b)/i },
  { tipo: 'custom', re: /\b(?:custom|cruiser|chopper|bobber|harley|sportster|softail|rebel|vulcan|diavel|guzzi|caf[eé]\s?racer|scrambler|bonneville)/i },
  { tipo: 'naked', re: /\b(?:naked|streetfighter|hornet|mt-?\d+|z\d{3,}|cb\d+|gsx-?s|street\s?triple|duke|monster|svartpilen|vitpilen|brutale)/i },
];

// Provincias de España para resolver `provincia` desde la ubicación.
const PROVINCIAS = [
  'Álava', 'Albacete', 'Alicante', 'Almería', 'Asturias', 'Ávila', 'Badajoz',
  'Barcelona', 'Burgos', 'Cáceres', 'Cádiz', 'Cantabria', 'Castellón',
  'Ciudad Real', 'Córdoba', 'La Coruña', 'A Coruña', 'Cuenca', 'Girona',
  'Gerona', 'Granada', 'Guadalajara', 'Guipúzcoa', 'Gipuzkoa', 'Huelva',
  'Huesca', 'Islas Baleares', 'Baleares', 'Jaén', 'León', 'Lérida', 'Lleida',
  'Lugo', 'Madrid', 'Málaga', 'Murcia', 'Navarra', 'Ourense', 'Orense',
  'Palencia', 'Las Palmas', 'Pontevedra', 'La Rioja', 'Salamanca',
  'Santa Cruz de Tenerife', 'Tenerife', 'Segovia', 'Sevilla', 'Soria',
  'Tarragona', 'Teruel', 'Toledo', 'Valencia', 'Valladolid', 'Vizcaya',
  'Bizkaia', 'Zamora', 'Zaragoza', 'Ceuta', 'Melilla',
];

const AÑO_ACTUAL = 2026;

/* ───────────────────────── helpers de parseo ───────────────────────── */

function aTextoLimpio(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim();
  return s.length ? s : null;
}

function aNumero(v) {
  if (v === null || v === undefined || v === '') return null;
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  // Quita símbolos de moneda, puntos de millar, "km", "€", etc.
  const limpio = String(v).replace(/[^\d,.-]/g, '').replace(/\.(?=\d{3}\b)/g, '');
  const num = parseFloat(limpio.replace(',', '.'));
  return Number.isFinite(num) ? num : null;
}

function aEntero(v) {
  const n = aNumero(v);
  return n === null ? null : Math.round(n);
}

function capitalizar(s) {
  if (!s) return s;
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/* ─────────────────────── inferencia de campos ──────────────────────── */

function detectarMarca(raw, texto) {
  const directa = aTextoLimpio(raw);
  if (directa) {
    const lower = directa.toLowerCase();
    const conocida = MARCAS_CONOCIDAS.find((m) => m.toLowerCase() === lower);
    if (conocida) return conocida;
    return capitalizar(directa);
  }
  // Buscar una marca conocida dentro del texto disponible.
  const enTexto = MARCAS_CONOCIDAS.find((m) =>
    new RegExp(`\\b${m.replace(/[-\s]/g, '[-\\s]?')}\\b`, 'i').test(texto)
  );
  return enTexto || null;
}

function detectarTipo(texto) {
  for (const { tipo, re } of PISTAS_TIPO) {
    if (re.test(texto)) return tipo;
  }
  return null;
}

function detectarProvincia(ubicacion) {
  if (!ubicacion) return null;
  const hit = PROVINCIAS.find((p) =>
    new RegExp(`\\b${p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(
      ubicacion
    )
  );
  return hit || null;
}

function validarAño(v) {
  const n = aEntero(v);
  if (n === null) return null;
  if (n < 1950 || n > AÑO_ACTUAL + 1) return null;
  return n;
}

function inferirCilindrada(raw, texto) {
  const directa = aEntero(raw);
  if (directa && directa >= 49 && directa <= 2500) return directa;
  // Patrón típico "650cc", "1000 cc", "125 cc".
  const m = texto.match(/\b(\d{2,4})\s?cc\b/i);
  if (m) {
    const n = parseInt(m[1], 10);
    if (n >= 49 && n <= 2500) return n;
  }
  return null;
}

/* ───────────────────────────── principal ───────────────────────────── */

/**
 * @param {object} raw    - JSON extraído por Firecrawl para una ficha.
 * @param {object} portal - definición del portal (id, name...).
 * @param {string} url    - URL original del anuncio.
 * @param {object} meta   - metadatos de Firecrawl (title, ogImage...).
 * @returns {object|null} anuncio normalizado, o null si no es válido.
 */
function normalizar(raw, portal, url, meta = {}) {
  raw = raw || {};

  const titulo = aTextoLimpio(raw.titulo) || aTextoLimpio(meta.title) || null;
  const descripcion = aTextoLimpio(raw.descripcion);
  // Texto agregado para inferencias por palabras clave.
  const texto = [titulo, raw.modelo, raw.marca, descripcion]
    .filter(Boolean)
    .join(' ');

  const marca = detectarMarca(raw.marca, texto);
  const modelo = aTextoLimpio(raw.modelo);
  const precio = aEntero(raw.precio);
  const km = aEntero(raw.km);
  const ubicacion = aTextoLimpio(raw.ubicacion);

  let fotos = Array.isArray(raw.fotos)
    ? raw.fotos.filter((f) => typeof f === 'string' && /^https?:\/\//.test(f))
    : [];
  if (fotos.length === 0 && meta.ogImage) fotos = [meta.ogImage];

  const anuncio = {
    // `id` y `fecha_crawl` los completa el orquestador antes de escribir.
    titulo,
    marca,
    modelo,
    año: validarAño(raw.año),
    km,
    precio,
    ubicacion,
    provincia: detectarProvincia(ubicacion),
    combustible: 'gasolina', // las motos de combustión son gasolina por defecto
    cilindrada: inferirCilindrada(raw.cilindrada, texto),
    tipo: detectarTipo(texto),
    color: null, // Firecrawl no lo extrae de forma fiable; queda null
    descripcion,
    fotos: fotos.length ? fotos : null,
    url_original: url,
    portal: portal.id,
    fecha_publicacion: aTextoLimpio(raw.fecha_publicacion) || null,
    activo: true,
  };

  return anuncio;
}

/**
 * Un anuncio es "útil" si al menos tiene precio y (marca o título). Si no,
 * la extracción ha fallado y no merece la pena guardarlo.
 */
function esValido(anuncio) {
  return (
    anuncio &&
    anuncio.precio !== null &&
    (anuncio.marca !== null || anuncio.titulo !== null)
  );
}

module.exports = { normalizar, esValido, TIPOS };
