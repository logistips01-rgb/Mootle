'use strict';

/**
 * Inicializa Firebase Admin SDK y expone el cliente de Firestore.
 *
 * Dos modos de autenticación:
 *   1. LOCAL  → usa el service account de las variables de entorno
 *               (FIREBASE_PROJECT_ID / CLIENT_EMAIL / PRIVATE_KEY).
 *   2. CLOUD  → dentro de Cloud Functions las credenciales se inyectan
 *               automáticamente, así que usamos applicationDefault().
 */
const admin = require('firebase-admin');

let app;

function init() {
  if (app) return app;
  if (admin.apps.length) {
    app = admin.app();
    return app;
  }

  const { FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY } =
    process.env;

  if (FIREBASE_PROJECT_ID && FIREBASE_CLIENT_EMAIL && FIREBASE_PRIVATE_KEY) {
    app = admin.initializeApp({
      credential: admin.credential.cert({
        projectId: FIREBASE_PROJECT_ID,
        clientEmail: FIREBASE_CLIENT_EMAIL,
        // En .env la clave lleva \n literales; los convertimos a saltos reales.
        privateKey: FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n'),
      }),
    });
  } else {
    // Entorno gestionado (Cloud Functions) o gcloud ADC configurado.
    app = admin.initializeApp();
  }
  return app;
}

init();

const db = admin.firestore();
db.settings({ ignoreUndefinedProperties: true });

module.exports = { admin, db };
