'use strict';

/**
 * Registro de portales activos + schema de extracción compartido.
 *
 * Para añadir un portal nuevo: crea su archivo en esta carpeta y añádelo aquí.
 */
const milanuncios = require('./milanuncios');
const wallapop = require('./wallapop');
const cochesnet = require('./cochesnet');

const PORTALS = [milanuncios, wallapop, cochesnet];

/**
 * Schema que se pasa a Firecrawl en `jsonOptions.schema` para que extraiga
 * campos estructurados directamente de cada ficha de anuncio.
 */
const EXTRACTION_SCHEMA = {
  type: 'object',
  properties: {
    titulo: { type: 'string' },
    marca: { type: 'string' },
    modelo: { type: 'string' },
    año: { type: 'number' },
    km: { type: 'number' },
    precio: { type: 'number' },
    ubicacion: { type: 'string' },
    cilindrada: { type: 'number' },
    descripcion: { type: 'string' },
    fotos: { type: 'array', items: { type: 'string' } },
  },
};

module.exports = { PORTALS, EXTRACTION_SCHEMA };
