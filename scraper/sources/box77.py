"""Box 77 Motos (Córdoba): compraventa de ocasión, ~110 motos.

Es una rejilla WPBakery: una sola página (/ocasion/) trae todas las motos, cada
tarjeta con su enlace a la ficha, foto y campos etiquetados (Año, Kilómetros,
Cilindrada, Precio). No pagina, así que se lee entera de una vez.
"""
import html
import re

from ..common import BRANDS, brand, clean_title, is_a2, key, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color


def _brand_model(title):
    """Separa marca y modelo de un título libre, respetando marcas de dos palabras
    (Royal Enfield, Moto Guzzi, Harley-Davidson…)."""
    words = title.split()
    if len(words) >= 2 and key(words[0] + words[1]) in BRANDS:
        return brand(words[0] + " " + words[1]), " ".join(words[2:])
    return brand(words[0]), " ".join(words[1:])

ID = "box77"
NAME = "Box 77 Motos"
HOME = "https://www.box77motos.com/"
LISTING = HOME + "ocasion/"
CITY, PROV = "Córdoba", "Córdoba"

_CARD = re.compile(r"vc_gitem-animated-block")
_LINK = re.compile(r'href="(https://www\.box77motos\.com/moto/[^"]+?)"\s+title="([^"]*)"')
_IMG = re.compile(r'vc_gitem-zone-img"\s+src="([^"]+)"')
_ANIO = re.compile(r"A[ñn]o:</span>\s*([0-9]{4})", re.I)
_KM = re.compile(r"Kil[óo]metros:</span>\s*([0-9.]+)", re.I)
_CC = re.compile(r"Cilindrada:</span>\s*([0-9.]+)", re.I)
_PRECIO = re.compile(r"Precio:</span>\s*([0-9.]+)\s*€", re.I)


def _to_listing(chunk, current_year):
    link = _LINK.search(chunk)
    precio = _PRECIO.search(chunk)
    if not link or not precio:
        return None
    url, raw_title = link.group(1), html.unescape(link.group(2)).strip()
    if not raw_title:
        return None
    mk, md = _brand_model(raw_title)
    title = clean_title(raw_title, mk)
    img = _IMG.search(chunk)
    anio = _ANIO.search(chunk)
    km = _KM.search(chunk)
    cc = _CC.search(chunk)
    # el id del anuncio es el slug de la ficha
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    return {
        "id": f"{ID}:{slug}",
        "src": ID,
        "url": url,
        "t": title,
        "mk": mk,
        "md": model(md) if md else None,
        "y": year(anio.group(1), current_year) if anio else None,
        "km": to_int(km.group(1)) if km else None,
        "p": to_int(precio.group(1)),
        "prov": province(PROV),
        "city": CITY,
        "img": img.group(1) if img else None,
        "cc": to_int(cc.group(1)) if cc else None,
        "tp": moto_type(None, f"{title} {md or ''}"),
        "a2": is_a2(title, None),
        "col": color(title),
        "pro": True,
    }


def scrape(fetcher, known, state, deadline, current_year, log):
    ok, robots_info = fetcher.allowed(LISTING)
    if not ok:
        return [], {"status": "robots_disallowed", "detail": robots_info}
    resp = fetcher.get(LISTING)
    if resp.status_code != 200 or is_challenge(resp):
        status = "challenge" if is_challenge(resp) else f"http_{resp.status_code}"
        return [], {"status": status, "detail": LISTING, "complete": False}

    # Cada tarjeta empieza en un vc_gitem-animated-block: partimos por ahí.
    parts = _CARD.split(resp.text)[1:]
    found = {}
    for chunk in parts:
        listing = _to_listing(chunk, current_year)
        if listing:
            found[listing["id"]] = listing
    log(f"{len(found)} motos leídas")
    return list(found.values()), {"status": "ok", "pages": 1, "complete": True}
