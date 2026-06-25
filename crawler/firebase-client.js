'use strict';

/**
 * Inicializa Firebase Admin SDK y expone el cliente de Firestore.
 *
 * Orden de preferencia para autenticar (de más robusto a menos):
 *   1. ARCHIVO JSON del service account → la forma recomendada en local.
 *      Pon el .json que descargaste de Firebase como `serviceAccount.json`
 *      en la raíz del proyecto, o indica su ruta en FIREBASE_SERVICE_ACCOUNT.
 *      Evita por completo el lío de pegar la private_key en el .env.
 *   2. VARIABLES de entorno (FIREBASE_PROJECT_ID / CLIENT_EMAIL / PRIVATE_KEY).
 *   3. CREDENCIALES por defecto → en Cloud Functions se inyectan solas.
 */
const fs = require('fs');
const path = require('path');
const admin = require('firebase-admin');

let app;

/**
 * Busca el archivo de service account en rutas habituales.
 * @returns {string|null} ruta absoluta del JSON, o null si no se encuentra.
 */
function localizarServiceAccount() {
  const candidatos = [];
  if (process.env.FIREBASE_SERVICE_ACCOUNT) {
    candidatos.push(process.env.FIREBASE_SERVICE_ACCOUNT);
  }
  if (process.env.GOOGLE_APPLICATION_CREDENTIALS) {
    candidatos.push(process.env.GOOGLE_APPLICATION_CREDENTIALS);
  }
  // serviceAccount.json en el cwd, en la carpeta del crawler y un nivel arriba.
  candidatos.push(
    path.join(process.cwd(), 'serviceAccount.json'),
    path.join(__dirname, 'serviceAccount.json'),
    path.join(__dirname, '..', 'serviceAccount.json')
  );
  for (const c of candidatos) {
    try {
      if (c && fs.existsSync(c)) return path.resolve(c);
    } catch (_) {
      /* ignora rutas inválidas */
    }
  }
  return null;
}

function init() {
  if (app) return app;
  if (admin.apps.length) {
    app = admin.app();
    return app;
  }

  // 1) Archivo JSON del service account (recomendado en local).
  const saPath = localizarServiceAccount();
  if (saPath) {
    const serviceAccount = require(saPath);
    app = admin.initializeApp({
      credential: admin.credential.cert(serviceAccount),
      projectId: serviceAccount.project_id,
    });
    return app;
  }

  // 2) Variables de entorno sueltas.
  const { FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY } =
    process.env;
  if (FIREBASE_PROJECT_ID && FIREBASE_CLIENT_EMAIL && FIREBASE_PRIVATE_KEY) {
    // La clave puede venir con \n literales (entre comillas en .env): los
    // convertimos a saltos reales. Si ya trae saltos reales, no pasa nada.
    const privateKey = FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n');
    app = admin.initializeApp({
      credential: admin.credential.cert({
        projectId: FIREBASE_PROJECT_ID,
        clientEmail: FIREBASE_CLIENT_EMAIL,
        privateKey,
      }),
    });
    return app;
  }

  // 3) Credenciales por defecto (Cloud Functions / gcloud ADC).
  app = admin.initializeApp();
  return app;
}

init();

const db = admin.firestore();
db.settings({ ignoreUndefinedProperties: true });

module.exports = { admin, db };
