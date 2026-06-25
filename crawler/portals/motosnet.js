'use strict';

/**
 * Portal Motos.net (servido desde motos.coches.net).
 *
 * A diferencia de los otros portales (que pasarían por Firecrawl), motos.net
 * sirve los anuncios renderizados en el propio HTML como tarjetas `.mt-CardAd`.
 * Por eso este portal usa `engine: 'html'`: descargamos el HTML directamente
 * (gratis, sin Firecrawl) y lo parseamos con cheerio.
 *
 * La propia URL de cada anuncio ya trae marca, modelo, año, provincia e id:
 *   /ocasion/benelli/trk_502/x-2021-en-sevilla-10027699.htm
 */
const cheerio = require('cheerio');

const BASE = 'https://motos.coches.net';
const SEARCH = BASE + '/segunda-mano/';

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

function capitalizar(s) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

/**
 * Extrae datos de la URL/slug de un anuncio.
 *   /ocasion/benelli/trk_502/x-2021-en-sevilla-10027699.htm
 *   →  marca=benelli, modelo=trk 502, año=2021, ubicacion=sevilla, id=10027699
 */
function datosDesdeHref(href) {
  const out = { marca: null, modelo: null, año: null, ubicacion: null };
  const partes = href.split('/').filter(Boolean); // ['ocasion','benelli','trk_502','x-...htm']
  if (partes.length >= 3) {
    out.marca = capitalizar(decodeURIComponent(partes[1]).replace(/[-_]/g, ' '));
    out.modelo = decodeURIComponent(partes[2]).replace(/[-_]/g, ' ').toUpperCase();
  }
  const slug = partes[partes.length - 1] || '';
  const anioM = slug.match(/-((?:19|20)\d{2})-/);
  if (anioM) out.año = parseInt(anioM[1], 10);
  const locM = slug.match(/-en-([a-z0-9-]+?)-\d+\.htm$/i);
  if (locM) out.ubicacion = capitalizar(locM[1].replace(/-/g, ' '));
  return out;
}

/**
 * Parsea el HTML de una página de resultados y devuelve un array de anuncios
 * "en crudo" (listos para pasar por normalize.js).
 */
function parseListings(html) {
  const $ = cheerio.load(html);
  const anuncios = [];

  $('.mt-CardAd').each((_, el) => {
    const card = $(el);
    const link = card.find('.mt-CardAd-infoHeaderTitleLink').first();
    const href = link.attr('href');
    if (!href) return;

    const titulo = link.text().trim();
    const url = href.startsWith('http') ? href : BASE + href;
    const desdeUrl = datosDesdeHref(href);

    const precio = card.find('.mt-CardAdPrice-cashAmount').first().text().trim() || null;

    // km: aparece como "14.714 km" en el texto de la tarjeta.
    const texto = card.text().replace(/\s+/g, ' ');
    const kmM = texto.match(/([\d.]+)\s*km(?![a-z])/i);
    const km = kmM ? kmM[1] : null;

    // Foto: el src suele ir en <img>, a veces en data-src (lazy load).
    const img = card.find('img').first();
    let foto = img.attr('src') || img.attr('data-src') || null;
    if (foto && !/^https?:\/\//.test(foto)) foto = null;

    anuncios.push({
      titulo,
      marca: desdeUrl.marca,
      modelo: desdeUrl.modelo,
      año: desdeUrl.año,
      km,
      precio,
      ubicacion: desdeUrl.ubicacion,
      fotos: foto ? [foto] : null,
      url,
    });
  });

  return anuncios;
}

module.exports = {
  id: 'motosnet',
  name: 'Motos.net',
  engine: 'html',
  baseUrl: BASE,
  searchUrl: SEARCH,
  headers: HEADERS,
  rateLimit: 1500,
  maxPages: 1, // se puede subir con CRAWL_MAX_PAGES; ver nota de paginación
  // Paginación (tentativa): motos.coches.net usa ?page=N. Si no funciona, se
  // ajusta aquí sin tocar el resto del crawler.
  pageUrl(n) {
    return n <= 1 ? SEARCH : `${SEARCH}?page=${n}`;
  },
  parseListings,
};
