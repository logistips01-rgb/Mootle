# mootle — comparador de motos de ocasión

Una sola búsqueda y ves las motos de segunda mano más baratas de portales y concesionarios de
España, con el **precio de mercado** de cada modelo y la **misma moto en varias webs** agrupada
("también en… por X €"). Misma línea que [guitle](https://guitle.com): rastreador diario en Python,
datos en JSON dentro del repo y una web estática que los lee.

## Cómo funciona

```
scraper/
  fetch.py        HTTP educado: UA de navegador, robots.txt, 3-6 s entre peticiones, detecta anti-bot
  common.py       normalización: marca canónica, modelo, tipo de moto, A2, provincia
  sources/        un módulo por web (scrape → anuncios + estado)
    motosnet.py     motos.net: JSON incrustado en cada página de resultados (20 anuncios/página)
    motoocasion.py  Moto Ocasión (Mora, Toledo): API pública de WooCommerce (100 motos/petición)
  run.py          lee todas las webs en paralelo y actualiza data/listings.json
data/
  listings.json   lo que carga la web: fuentes + anuncios (claves cortas, ver abajo)
  state.json      por dónde va cada web que se lee por partes (cursor de motos.net)
index.html        la web: portada (chollos, bajadas, webs) y buscador con filtros
.github/workflows/scrape.yml   cron diario que ejecuta el rastreador y commitea data/
```

Cada ejecución, por web:

- **motos.net** (~35.000 motos, ~1.730 páginas): **como mucho 4 páginas al día**, para no cargar la
  web. Primero las novedades (páginas 1, 2… hasta una sin anuncios nuevos); si sobra cupo, sigue el
  barrido donde lo dejó el día anterior (`cursor` en `data/state.json`). Si responde con su página
  anti-bot, para ese día sin reintentar. Un anuncio que no se ve en 14 días se da por vendido.
- **Moto Ocasión**: se lee entera (~9 peticiones); lo que no aparece, o está agotado, se ha vendido.

Después, `run.py`:

- conserva la fecha en que se vio cada anuncio por primera vez y el **precio anterior** si cambia;
- calcula el **precio de mercado**: mediana de las motos de la misma marca, modelo y año (±1),
  si hay 5 o más;
- **agrupa la misma moto en varias webs** (misma marca, año y km, modelo compatible, precio parecido):
  la web muestra la más barata y el resto como "también en…".

## Uso local

```sh
pip install -r requirements.txt
python -m scraper.run --minutes 5 --dry-run     # informe sin tocar data/
python -m scraper.run --only motoocasion        # solo una web, guardando
python -m http.server                           # y abrir http://localhost:8000
```

## Añadir una web

1. Crea `scraper/sources/<id>.py` con `ID`, `NAME`, `HOME` y
   `scrape(fetcher, known, state, deadline, current_year, log)` que devuelva `(anuncios, info)`.
   - `info["status"]`: `ok`, `http_403`, `challenge`, `robots_disallowed`, `sin_json`, `error`…
   - `info["complete"] = True` si se ha leído la web entera (lo que falte se borra al momento).
2. Añádela en `scraper/sources/__init__.py`.
3. Pruébala: `python -m scraper.run --only <id> --minutes 3 --dry-run`.

Antes de añadir una web: mira su `robots.txt` y busca primero un JSON (API de tienda, JSON incrustado
en la página, feed) antes de leer HTML. Concesionarios con WordPress + WooCommerce suelen tener
`/wp-json/wc/store/v1/products` abierto, como Moto Ocasión.

## Formato de un anuncio (`data/listings.json` → `items`)

| Clave | Qué es | | Clave | Qué es |
|---|---|---|---|---|
| `id` | `<web>:<id en la web>` | | `prov`, `city` | provincia y ciudad |
| `src` | web de origen | | `img` | foto |
| `url` | anuncio original | | `cv`, `cc` | potencia y cilindrada |
| `t` | título | | `tp` | naked, trail, scooter, deportiva, custom, turismo, campo |
| `mk`, `md` | marca y modelo | | `a2` | apta o limitable para A2 |
| `y`, `km` | año y kilómetros | | `pro` | vendedor profesional |
| `p` | precio (€) | | `pub` | fecha de publicación en la web |
| `p0` | precio tachado en la web | | `fs`, `ls` | primera y última vez visto |
| `pa`, `pc` | precio anterior y día del cambio | | `mkt` | precio de mercado (mediana) |
| `res` | reservada | | `g` | grupo: la misma moto en varias webs |

## Publicar la web

Es estática: GitHub Pages (Settings → Pages → rama `main`, carpeta raíz), como guitle, o cualquier
hosting estático. El cron solo corre desde la rama por defecto.
