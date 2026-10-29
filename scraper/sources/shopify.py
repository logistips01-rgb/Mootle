"""Lector genérico para tiendas Shopify, que publican su catálogo en `/products.json`
(JSON uniforme: título, vendor, product_type, variants[].price, body_html). Como con
WooCommerce, cada tienda se declara en STORES.

`types`: valores de product_type (en minúsculas) que son motos de ocasión (vacío = todos).
`ykm`: None si la tienda no da año/km; cualquier otro valor los busca en el título y la
descripción. Solo se guardan las motos que traen año o km (así se descarta la moto nueva).
"""
import html
import re

from ..common import brand, clean_title, fold, is_a2, model, moto_type, province, to_int, year

PER_PAGE = 250
MAX_PAGES = 20

STORES = [
    {"id": "mottium", "name": "Mottium", "home": "https://mottium.com/", "city": "Tarragona", "prov": "Tarragona",
     "types": ["moto"], "ykm": "auto"},
]

_YEAR = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
_YEAR_LABEL = re.compile(r"(?:año|anio|a[nñ]o)\s*[:;.\-]?\s*((?:19|20)\d{2})", re.I)
_KM = re.compile(r"([\d.]{2,})\s*(?:km|kms|kilómetros|kilometros)\b", re.I)
_KM_LABEL = re.compile(r"(?:kms?|kilómetros|kilometros)\s*[:=]\s*([\d.]+)", re.I)


def _year_km(text):
    ym = _YEAR_LABEL.search(text) or _YEAR.search(text)
    # Primero "60.000KM" (número antes); si no, "Km: 10.300" (etiqueta antes). Evita tomar el
    # precio que a veces sigue a los km ("60.000KM - 14.990€").
    km = _KM_LABEL.search(text) or _KM.search(text)
    return (ym.group(1) if ym and ym.lastindex else (ym.group() if ym else None),
            km.group(1) if km else None)


def _to_listing(p, store, current_year):
    ptype = (p.get("product_type") or "").lower()
    if store["types"] and not any(t in ptype for t in store["types"]):
        return None
    variants = p.get("variants") or []
    # Shopify da el precio en euros con decimales ("14990.00"), no en céntimos.
    try:
        price = int(round(float(variants[0].get("price")))) if variants and variants[0].get("price") else None
    except (TypeError, ValueError):
        price = None
    if not price:
        return None
    name = html.unescape(p.get("title") or "")
    body = re.sub(r"<[^>]+>", " ", p.get("body_html") or "")
    y_raw, km_raw = _year_km(name + " · " + body) if store.get("ykm") else (None, None)
    if store.get("ykm") and not (y_raw or km_raw):
        return None  # sin año ni km: probablemente moto nueva, se descarta
    vendor = p.get("vendor") or ""
    mk = brand(vendor) if brand(vendor) and fold(vendor) != fold(store["name"]) else brand(name.split(" ")[0])
    md = name[len(mk):] if mk and fold(name).startswith(fold(mk)) else name
    imgs = p.get("images") or []
    img = imgs[0].get("src") if imgs else None
    handle = p.get("handle")
    return {
        "id": f"{store['id']}:{p.get('id')}",
        "src": store["id"],
        "url": store["home"].rstrip("/") + "/products/" + handle if handle else store["home"],
        "t": clean_title(name, mk),
        "mk": mk,
        "md": model(md.strip()) if md and md.strip() else None,
        "y": year(y_raw, current_year),
        "km": to_int(km_raw) if km_raw else None,
        "p": price,
        "prov": province(store["prov"]),
        "city": store["city"],
        "img": img,
        "tp": moto_type(None, f"{name} {body[:80]}"),
        "a2": is_a2(name + " " + body),
        "pro": True,
    }


def _make_scrape(store):
    base = store["home"].rstrip("/") + "/products.json"

    def scrape(fetcher, known, state, deadline, current_year, log):
        ok, robots_info = fetcher.allowed(base)
        if not ok:
            return [], {"status": "robots_disallowed", "detail": robots_info}
        found, pages = {}, 0
        for page in range(1, MAX_PAGES + 1):
            resp = fetcher.get(f"{base}?limit={PER_PAGE}&page={page}")
            if resp.status_code != 200:
                status = f"http_{resp.status_code}"
                log(f"⚠ {status} en la página {page}")
                return list(found.values()), {"status": status, "detail": f"página {page}", "pages": pages, "complete": False}
            try:
                items = (resp.json() or {}).get("products") or []
            except ValueError:
                return list(found.values()), {"status": "sin_json", "detail": f"página {page}", "pages": pages, "complete": False}
            pages += 1
            for p in items:
                listing = _to_listing(p, store, current_year)
                if listing:
                    found[listing["id"]] = listing
            if len(items) < PER_PAGE:
                break
        return list(found.values()), {"status": "ok", "pages": pages, "complete": True}

    return scrape


class _ShopifyStore:
    def __init__(self, store):
        self.ID = store["id"]
        self.NAME = store["name"]
        self.HOME = store["home"]
        self.scrape = _make_scrape(store)


SOURCES = [_ShopifyStore(s) for s in STORES]
