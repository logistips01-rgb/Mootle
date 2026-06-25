# 🛵 Mootle

**El buscador de motos de segunda mano de España.** Agrega anuncios de
Milanuncios, Wallapop y Coches.net en un único sitio, normalizados, sin
duplicados y con filtros potentes — el "Skyscanner de las motos".

Esto es **Mootle v0.1**. Todo lo demás es iteración.

---

## Arquitectura

```
Firecrawl API
     │  /map  → descubre URLs de anuncios
     │  /batch/scrape → extrae campos estructurados
     ▼
crawler/                       (Node.js)
  ├── portals/                 schema + URL patterns por portal
  ├── normalize.js             normaliza al schema común
  ├── dedup.js                 hash (marca|modelo|precio|km)
  └── index.js                 orquestador
     │
     ▼
Firebase Firestore
  ├── listings/    anuncios normalizados (doc id = hash)
  ├── portals/     estado de cada portal (último crawl, errores)
  └── stats/       métricas globales
     ▲
     │ lectura directa vía SDK web
index.html                     frontend (un único archivo)

Firebase Cloud Functions
  └── scheduledCrawl           cada 6 h lanza el crawler
```

---

## Puesta en marcha

### 1. Dependencias

```bash
npm install
```

### 2. Variables de entorno

```bash
cp .env.example .env
```

Rellena en `.env`:

- `FIRECRAWL_API_KEY` — clave de [Firecrawl](https://www.firecrawl.dev).
- `FIREBASE_PROJECT_ID`, `FIREBASE_CLIENT_EMAIL`, `FIREBASE_PRIVATE_KEY` —
  del service account (Firebase Console → Configuración → Cuentas de servicio
  → Generar nueva clave privada). Solo necesarios para ejecutar el crawler en
  local; en Cloud Functions las credenciales se inyectan solas.

### 3. Ejecutar el crawler

```bash
npm run crawl                 # todos los portales
node crawler/index.js wallapop   # solo un portal
```

Salida esperada por portal:

```
[Milanuncios] 47 nuevos anuncios | 12 duplicados descartados | 3 errores
```

### 4. Frontend

Edita el objeto `firebaseConfig` al final de `index.html` con la config de tu
app web de Firebase (Console → Configuración → Tus apps → Web), y sirve:

```bash
firebase serve --only hosting
# o cualquier servidor estático: npx serve .
```

### 5. Desplegar

```bash
# Reglas e índices de Firestore
firebase deploy --only firestore

# Hosting (frontend)
firebase deploy --only hosting

# Cloud Function programada (copia el crawler a functions/ automáticamente)
firebase functions:secrets:set FIRECRAWL_API_KEY
firebase deploy --only functions
```

---

## Schema de un anuncio (`listings/`)

| Campo               | Tipo            | Notas                                  |
| ------------------- | --------------- | -------------------------------------- |
| `id`                | string          | hash sha1 de marca\|modelo\|precio\|km |
| `titulo`            | string          |                                        |
| `marca` / `modelo`  | string          |                                        |
| `año`               | number          |                                        |
| `km` / `precio`     | number          |                                        |
| `ubicacion`         | string          |                                        |
| `provincia`         | string          | inferida de la ubicación               |
| `combustible`       | string          | "gasolina" por defecto                 |
| `cilindrada`        | number          |                                        |
| `tipo`              | string          | naked / trail / deportiva / custom / scooter |
| `color`             | string \| null  |                                        |
| `descripcion`       | string          |                                        |
| `fotos`             | string[]        |                                        |
| `url_original`      | string          |                                        |
| `portal`            | string          | milanuncios / wallapop / cochesnet     |
| `fecha_publicacion` | string \| null  |                                        |
| `fecha_crawl`       | string ISO 8601 |                                        |
| `activo`            | boolean         |                                        |

Los campos que no se puedan extraer quedan como `null` (nunca se omiten).

---

## Foodle (experimento) — buscador de restaurantes por foodies

Pivote del proyecto: en vez de scrapear portales bloqueados, agrega
**recomendaciones de foodies de YouTube** (datos accesibles vía API oficial).

```bash
npm install
# en .env: YOUTUBE_API_KEY=... y ANTHROPIC_API_KEY=...
node foodle/extract.js @cenandoconpablo @cocituber 40            # → foodle/data/restaurantes.json
node foodle/extract.js @cenandoconpablo @cocituber 40 --firestore # además escribe en Firestore
```

Flujo: YouTube Data API (títulos + descripciones de los últimos vídeos) →
Claude Haiku extrae la ficha de restaurante (o descarta el vídeo si no lo es) →
JSON / colección `restaurants` de Firestore. Coste de IA: ~0,2 céntimos por
vídeo.

## Notas y limitaciones de v0.1

- **Wallapop** es una SPA con anti-bot agresivo: `/map` puede devolver pocas
  URLs de ficha. Milanuncios y Coches.net suelen mapear mejor. Un fallo en un
  portal se registra y **no detiene** el resto.
- El **frontend filtra en cliente** sobre los últimos `FETCH_LIMIT` (500)
  anuncios traídos de Firestore. Suficiente para v0.1; al crecer el volumen,
  los filtros se moverán a consultas server-side con índices compuestos.
- Firestore necesita el índice `activo + fecha_crawl` (incluido en
  `firestore.indexes.json`). Si una consulta pide un índice que falta, Firebase
  te da en consola el enlace exacto para crearlo.
- El crawler respeta el `rateLimit` de cada portal y el `robots.txt` (lo
  gestiona Firecrawl por defecto).
```
