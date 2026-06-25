'use strict';

/**
 * Deduplicación de anuncios.
 *
 * El identificador de un anuncio es un hash estable de (marca, modelo,
 * precio, km). Dos anuncios con el mismo hash se consideran el mismo vehículo
 * aunque estén en portales distintos, de modo que el último crawl simplemente
 * actualiza el documento existente en lugar de crear un duplicado.
 */
const crypto = require('crypto');

/**
 * Normaliza un valor para que entre en el hash de forma estable.
 */
function clave(valor) {
  if (valor === null || valor === undefined || valor === '') return '∅';
  return String(valor).trim().toLowerCase();
}

/**
 * Genera el hash único de un anuncio normalizado.
 * @param {object} anuncio - anuncio ya pasado por normalize.js
 * @returns {string} hash sha1 (40 chars)
 */
function generarHash(anuncio) {
  const base = [
    clave(anuncio.marca),
    clave(anuncio.modelo),
    clave(anuncio.precio),
    clave(anuncio.km),
  ].join('|');
  return crypto.createHash('sha1').update(base).digest('hex');
}

module.exports = { generarHash };
