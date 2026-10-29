"""Lector genérico para tiendas WooCommerce con la Store API pública abierta
(`/wp-json/wc/store/v1/products`), como Moto Ocasión. Una sola clase sirve para muchos
concesionarios: cada uno se declara en STORES con de dónde saca el año y los km, porque
ahí es donde difieren (en atributos propios, en el nombre o en la descripción).

Para añadir una tienda: comprueba que su API responde y mira una ficha; añade una entrada a
STORES. `cats`: slugs de categoría que son motos de ocasión (vacío = todas). `ykm`: de dónde
leer año y km — "attrs" (atributos Año/Kilómetros, como Moto Ocasión), "name" (en el título,
"... -AÑO 2005- 61.937 KM"), "desc" (en la descripción, "Año:1990 Km:10.300") o None.
"""
import re

from ..common import brand, clean_title, is_a2, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

PER_PAGE = 100
MAX_PAGES = 60

STORES = [
    # Moto Ocasión y Máquina Motors tienen su propio módulo (más fino); aquí van las demás.
    {"id": "germotos", "name": "Germotos", "home": "https://germotos.com/", "city": "Baena", "prov": "Córdoba",
     "cats": ["motos-de-ocasion", "ciclomotores"], "ykm": "desc"},
    {"id": "paradisemotos", "name": "Paradise Motos", "home": "https://paradisemotos.es/", "city": "Jaén", "prov": "Jaén",
     "cats": ["motos-segunda-mano"], "ykm": "name"},
    {"id": "motostapia", "name": "Motos Tapia", "home": "https://motostapia.com/", "city": "Vitoria-Gasteiz", "prov": "Álava",
     "cats": ["motos"], "ykm": None},
    {"id": "motoslemans", "name": "Motos LeMans", "home": "https://motoslemans.es/", "city": "Mollet del Vallès", "prov": "Barcelona",
     "cats": [], "ykm": "name"},
    # BCN Motorbikes (Yamaha oficial): su API es casi toda moto nueva con precio 0, no sirve para ocasión.
]

_YEAR = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
_KM = re.compile(r"([\d.]{2,})\s*(?:km|kms|kilómetros|kilometros)\b", re.I)
_KM_LABEL = re.compile(r"(?:kms?|kilómetros|kilometros)\s*[:;.\-]?\s*([\d.]+)", re.I)
_YEAR_LABEL = re.compile(r"(?:año|anio|a[nñ]o)\s*[:;.\-]?\s*((?:19|20)\d{2})", re.I)


def _attrs(raw):
    out = {}
    for a in raw.get("attributes") or []:
        terms = [t.get("name") for t in a.get("terms") or [] if t.get("name")]
        if terms:
            out[a.get("name").strip().lower()] = terms[0]
    return out


def _clean(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html or "")).strip()


def _year_km(raw, how, attrs):
    """Devuelve (año, km) según la estrategia de la tienda."""
    if how == "attrs":
        return (attrs.get("año") or attrs.get("ano") or attrs.get("anio"),
                attrs.get("kilómetros") or attrs.get("kilometros") or attrs.get("km"))
    text = raw.get("name", "") if how == "name" else _clean(raw.get("short_description") or raw.get("description"))
    if not how or not text:
        return None, None
    ym = _YEAR_LABEL.search(text) or _YEAR.search(text)
    km = _KM_LABEL.search(text) or _KM.search(text)
    return (ym.group(1) if ym and ym.lastindex else (ym.group() if ym else None),
            km.group(1) if km else None)


def _to_listing(raw, store, current_year):
    cats = [c.get("slug") for c in raw.get("categories") or []]
    if store["cats"] and not any(c in store["cats"] for c in cats):
        return None
    prices = raw.get("prices") or {}
    unit = 10 ** int(prices.get("currency_minor_unit") or 2)
    price = to_int(prices.get("price"))
    regular = to_int(prices.get("regular_price"))
    if not price:
        return None
    attrs = _attrs(raw)
    name = raw.get("name") or ""
    brands = [b.get("name") for b in raw.get("brands") or [] if b.get("name")]
    mk = brand(brands[0] if brands else name.split(" ")[0])
    y_raw, km_raw = _year_km(raw, store.get("ykm"), attrs)
    # El nombre sin los adornos de año/km ("BMW GS 650 -AÑO 2005- 61.937 KM" → "BMW GS 650").
    clean_name = re.sub(r"[*\-·|]*\s*a[nñ]o\b.*$", "", name, flags=re.I).strip() if store.get("ykm") == "name" else name
    clean_name = re.sub(r"[\d.]{2,}\s*km\b.*$", "", clean_name, flags=re.I).strip()
    md = attrs.get("modelo")
    if not md:
        md = clean_name[len(mk):] if mk and clean_name.lower().startswith(mk.lower()) else clean_name
    images = raw.get("images") or []
    img = (images[0].get("thumbnail") or images[0].get("src")) if images else None
    title = clean_title(clean_name, mk)
    return {
        "id": f"{store['id']}:{raw['id']}",
        "src": store["id"],
        "url": raw.get("permalink"),
        "t": title,
        "mk": mk,
        "md": model(md.strip()) if md and md.strip() else None,
        "y": year(y_raw, current_year),
        "km": to_int(km_raw) if km_raw else None,
        "p": price // unit,
        "p0": regular // unit if regular and regular > price else None,
        "prov": province(store["prov"]),
        "city": store["city"],
        "img": img,
        "cc": to_int(attrs.get("cilindrada")),
        "tp": moto_type(cats[0] if cats else None, f"{title} {md or ''}"),
        "a2": is_a2(name, None, attrs.get("carnet")),
        "col": color(attrs.get("color"), name),
        "pro": True,
    }


def _make_scrape(store):
    api = store["home"].rstrip("/") + "/wp-json/wc/store/v1/products"

    def scrape(fetcher, known, state, deadline, current_year, log):
        ok, robots_info = fetcher.allowed(api)
        if not ok:
            return [], {"status": "robots_disallowed", "detail": robots_info}
        found, pages = {}, 0
        for page in range(1, MAX_PAGES + 1):
            resp = fetcher.get(f"{api}?per_page={PER_PAGE}&page={page}")
            if resp.status_code == 400 and page > 1:
                break
            if resp.status_code != 200 or is_challenge(resp):
                status = "challenge" if is_challenge(resp) else f"http_{resp.status_code}"
                log(f"⚠ {status} en la página {page}")
                return list(found.values()), {"status": status, "detail": f"página {page}", "pages": pages, "complete": False}
            try:
                items = resp.json()
            except ValueError:
                return list(found.values()), {"status": "sin_json", "detail": f"página {page}", "pages": pages, "complete": False}
            if not isinstance(items, list):
                return list(found.values()), {"status": "api_rara", "detail": str(items)[:120], "pages": pages, "complete": False}
            pages += 1
            for raw in items:
                if raw.get("is_in_stock") is False:
                    continue
                listing = _to_listing(raw, store, current_year)
                if listing:
                    found[listing["id"]] = listing
            total_pages = to_int(resp.headers.get("X-WP-TotalPages")) or 0
            if len(items) < PER_PAGE or (total_pages and page >= total_pages):
                break
        return list(found.values()), {"status": "ok", "pages": pages, "complete": True}

    return scrape


class _WooStore:
    def __init__(self, store):
        self.ID = store["id"]
        self.NAME = store["name"]
        self.HOME = store["home"]
        self.scrape = _make_scrape(store)


SOURCES = [_WooStore(s) for s in STORES]
