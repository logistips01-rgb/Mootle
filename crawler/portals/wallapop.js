'use strict';

/**
 * Definición del portal Wallapop.
 *
 * Nota: Wallapop es una SPA con anti-bot agresivo. Es el portal donde /map
 * puede devolver menos URLs de ficha. Firecrawl renderiza JS, lo que ayuda,
 * pero si un día deja de mapear bien habrá que mirar su API interna.
 */
module.exports = {
  id: 'wallapop',
  name: 'Wallapop',
  searchUrl:
    'https://es.wallapop.com/app/search?category_ids=14000&filters_source=quick_filters',
  urlPattern: /wallapop\.com\/item\//i,
  rateLimit: 3000,
  mapSearch: 'moto',
};
