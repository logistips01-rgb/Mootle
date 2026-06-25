'use strict';

/**
 * Definición del portal Milanuncios.
 *
 * - `searchUrl`  : punto de partida que se pasa a Firecrawl /map para
 *                  descubrir URLs de anuncios.
 * - `urlPattern` : filtro para quedarnos solo con URLs de FICHA de anuncio
 *                  (descartando categorías, filtros, etc.).
 * - `rateLimit`  : ms de espera entre peticiones para no saturar el portal.
 * - `mapSearch`  : término que ayuda a Firecrawl a priorizar URLs relevantes.
 */
module.exports = {
  id: 'milanuncios',
  name: 'Milanuncios',
  searchUrl: 'https://www.milanuncios.com/motos-de-segunda-mano/',
  urlPattern: /milanuncios\.com\/moto.*\/\d+\.htm/i,
  rateLimit: 2000,
  mapSearch: 'moto',
};
