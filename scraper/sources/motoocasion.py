"""moto-ocasion.com: concesionario de Mora (Toledo), ~900 motos.

Es una tienda WooCommerce con la Store API pública (`/wp-json/wc/store/v1/products`):
100 motos por petición en JSON, con modelo, año, km, cilindrada, CV y carnet como
atributos. Se lee entero en cada ejecución (~9 peticiones), así que lo que no aparece
se ha vendido.
"""
from ..common import brand, clean_title, is_a2, model, moto_type, to_int, year
from ..fetch import is_challenge

ID = "motoocasion"
NAME = "Moto Ocasión"
HOME = "https://www.moto-ocasion.com/"
API = "https://www.moto-ocasion.com/wp-json/wc/store/v1/products"
PER_PAGE = 100
MAX_PAGES = 50
PROVINCE, CITY = "Toledo", "Mora"


def _attrs(raw):
    out = {}
    for a in raw.get("attributes") or []:
        terms = [t.get("name") for t in a.get("terms") or [] if t.get("name")]
        if terms:
            out[a.get("name")] = terms[0]
    return out


def to_listing(raw, current_year):
    attrs = _attrs(raw)
    km_raw = attrs.get("Kilómetros")
    if km_raw is None or not attrs.get("Año"):
        return None  # no es una moto (accesorio, ropa...)
    prices = raw.get("prices") or {}
    unit = 10 ** int(prices.get("currency_minor_unit") or 0)
    price = to_int(prices.get("price"))
    regular = to_int(prices.get("regular_price"))
    brands = [b.get("name") for b in raw.get("brands") or [] if b.get("name")]
    mk = brand(brands[0] if brands else (raw.get("name") or "").split(" ")[0])
    md = model(attrs.get("Modelo"))
    title = clean_title(raw.get("name"), mk)
    hp = to_int(attrs.get("Potencia Máxima"))
    cats = [c.get("slug") for c in raw.get("categories") or []]
    images = raw.get("images") or []
    img = images[0].get("thumbnail") or images[0].get("src") if images else None
    return {
        "id": f"{ID}:{raw['id']}",
        "src": ID,
        "url": raw.get("permalink"),
        "t": title,
        "mk": mk,
        "md": md,
        "y": year(attrs.get("Año"), current_year),
        "km": to_int(km_raw) if to_int(km_raw) is not None else 0,
        "p": price // unit if price else None,
        "p0": regular // unit if regular and price and regular > price else None,
        "prov": PROVINCE,
        "city": CITY,
        "img": img,
        "cv": hp,
        "cc": to_int(attrs.get("Cilindrada")),
        "tp": moto_type(cats[0] if cats else None, f"{title} {md or ''}"),
        "a2": is_a2(raw.get("name"), hp, attrs.get("Carnet")),
        "pro": True,
        "res": attrs.get("Disponibilidad", "").lower().startswith("reserv") or None,
    }


def scrape(fetcher, known, state, deadline, current_year, log):
    ok, robots_info = fetcher.allowed(API)
    if not ok:
        return [], {"status": "robots_disallowed", "detail": robots_info}
    found, pages = {}, 0
    for page in range(1, MAX_PAGES + 1):
        resp = fetcher.get(f"{API}?per_page={PER_PAGE}&page={page}")
        if resp.status_code == 400 and page > 1:
            break  # página fuera de rango
        if resp.status_code != 200 or is_challenge(resp):
            status = "challenge" if is_challenge(resp) else f"http_{resp.status_code}"
            log(f"⚠ {status} en la página {page}")
            return list(found.values()), {"status": status, "detail": f"página {page}", "pages": pages,
                                          "complete": False}
        items = resp.json()
        pages += 1
        for raw in items:
            if raw.get("is_in_stock") is False:
                continue
            listing = to_listing(raw, current_year)
            if listing and listing["p"]:
                found[listing["id"]] = listing
        total_pages = to_int(resp.headers.get("X-WP-TotalPages")) or 0
        if len(items) < PER_PAGE or (total_pages and page >= total_pages):
            break
    return list(found.values()), {"status": "ok", "pages": pages, "complete": True}
