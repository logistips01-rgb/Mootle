'use strict';

/**
 * Cloud Function programada: lanza el crawler de Mootle cada 6 horas.
 *
 * El código del crawler vive en /crawler. Antes del deploy se copia a
 * functions/crawler/ mediante el script `copy:crawler` (ver firebase.json),
 * porque Cloud Functions solo empaqueta el contenido de la carpeta functions/.
 *
 * La clave de Firecrawl se inyecta como secreto:
 *   firebase functions:secrets:set FIRECRAWL_API_KEY
 *
 * Las credenciales de Firebase Admin se proporcionan automáticamente en el
 * entorno gestionado, así que no hace falta service account aquí.
 */
const { onSchedule } = require('firebase-functions/v2/scheduler');
const { logger } = require('firebase-functions');

const { runCrawler } = require('./crawler');

exports.scheduledCrawl = onSchedule(
  {
    schedule: 'every 6 hours',
    timeZone: 'Europe/Madrid',
    timeoutSeconds: 540,
    memory: '512MiB',
    secrets: ['FIRECRAWL_API_KEY'],
    retryCount: 0,
  },
  async (event) => {
    logger.info('scheduledCrawl: iniciando crawl programado');
    try {
      const total = await runCrawler();
      logger.info('scheduledCrawl: completado', total);
    } catch (e) {
      logger.error('scheduledCrawl: error', { message: e.message });
      throw e; // permite reintentos/alertas de Cloud Functions
    }
  }
);
