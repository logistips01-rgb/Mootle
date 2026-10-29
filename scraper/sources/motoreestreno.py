"""Moto Reestreno (Sant Joan d'Alacant, Alicante): ocasión, ~190 motos.

El listado se pinta por AJAX desde /inc/ajax-catalog/vehicles.php, que devuelve
JSON (id, nombre, precio, año, km, cv, tipo, foto). Hay que pasarle la lista de
IDs de vehículos que la propia página de listado lleva incrustada (vehicles: '…').
Se pide de 12 en 12 con ?page=N.
"""
import json
import re
import time

from ..common import BRANDS, brand, clean_title, is_a2, key, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

ID = "motoreestreno"
NAME = "Moto Reestreno"
HOME = "https://motoreestreno.com/"
LISTING = HOME + "moto-segunda-mano/"
API = HOME + "inc/ajax-catalog/vehicles.php"
FICHA = HOME + "moto-segunda-mano/"
CITY, PROV = "Sant Joan d'Alacant", "Alicante"
PER_PAGE = 12

_IDS = re.compile(r"vehicles:\s*'([0-9,]+)'")
_VERSION = re.compile(r"\s*Versi[oó]n.*$", re.I)


def _brand_model(name, url):
    """Marca del prefijo del enlace (bmw_…, moto-morini_…), modelo del nombre sin 'Versión'."""
    mk_slug = url.split("_", 1)[0]
    mk = brand(mk_slug.replace("-", " "))
    clean = _VERSION.sub("", name).strip()
    if mk and clean.lower().startswith(mk.lower()):
        return mk, clean[len(mk):].strip()
    # por si el nombre trae una marca de dos palabras que el prefijo no capta
    words = clean.split()
    if len(words) >= 2 and key(words[0] + words[1]) in BRANDS:
        return brand(words[0] + " " + words[1]), " ".join(words[2:])
    return mk, clean[len(mk):].strip() if mk and clean.lower().startswith(mk.lower()) else clean


def _to_listing(raw, current_year):
    rid = raw.get("id")
    name = raw.get("name") or ""
    url = raw.get("url") or ""
    if not rid or not name:
        return None
    price = to_int(re.sub(r"[^\d]", "", str(raw.get("price") or "")))
    if not price:
        return None
    mk, md = _brand_model(name, url)
    title = clean_title(_VERSION.sub("", name).strip(), mk)
    return {
        "id": f"{ID}:{rid}",
        "src": ID,
        "url": FICHA + url if not url.startswith("http") else url,
        "t": title,
        "mk": mk,
        "md": model(md) if md else None,
        "y": year(raw.get("years"), current_year),
        "km": to_int(raw.get("km")),
        "p": price,
        "prov": province(PROV),
        "city": CITY,
        "img": raw.get("image"),
        "cv": to_int(raw.get("power")),
        "tp": moto_type(raw.get("type"), f"{title} {md or ''}"),
        "a2": is_a2(title, to_int(raw.get("power"))),
        "col": color(title),
        "pro": True,
    }


def scrape(fetcher, known, state, deadline, current_year, log):
    ok, robots_info = fetcher.allowed(API)
    if not ok:
        return [], {"status": "robots_disallowed", "detail": robots_info}
    index = fetcher.get(LISTING)
    if index.status_code != 200 or is_challenge(index):
        status = "challenge" if is_challenge(index) else f"http_{index.status_code}"
        return [], {"status": status, "detail": LISTING, "complete": False}
    m = _IDS.search(index.text)
    if not m:
        return [], {"status": "sin_ids", "detail": "no está la lista vehicles:'…'", "complete": False}
    ids = m.group(1)
    total = ids.count(",") + 1
    pages = -(-total // PER_PAGE)  # techo

    found = {}
    read = 0
    for n in range(1, pages + 1):
        if time.monotonic() > deadline:
            return list(found.values()), {"status": "ok", "pages": read, "complete": False}
        resp = fetcher.get(f"{API}?page={n}&vehicles={ids}")
        if resp.status_code != 200 or is_challenge(resp):
            status = "challenge" if is_challenge(resp) else f"http_{resp.status_code}"
            return list(found.values()), {"status": status, "detail": f"página {n}", "pages": read, "complete": False}
        try:
            items = resp.json()
        except ValueError:
            return list(found.values()), {"status": "sin_json", "detail": f"página {n}", "pages": read, "complete": False}
        read += 1
        for raw in items or []:
            listing = _to_listing(raw, current_year)
            if listing:
                found[listing["id"]] = listing
    log(f"{len(found)} motos leídas ({read} páginas)")
    return list(found.values()), {"status": "ok", "pages": read, "complete": True}
