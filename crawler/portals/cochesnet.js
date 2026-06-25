'use strict';

/**
 * Definición del portal Coches.net (sección motos).
 */
module.exports = {
  id: 'cochesnet',
  name: 'Coches.net Motos',
  searchUrl: 'https://www.coches.net/motos-segunda-mano/',
  urlPattern: /coches\.net\/motos\/.+\/\d+/i,
  rateLimit: 1500,
  mapSearch: 'moto',
};
