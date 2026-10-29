"""Moto Fuchs (Aldaia, Valencia): ocasión, ~47 motos.

Listado estático en la portada: cada tarjeta (`card moto-card`) trae el título en la
cabecera, el enlace a la ficha (detalles.php?id=N), y unos badges con cc, año, precio
y km.
"""
import html
import re

from ..common import BRANDS, brand, clean_title, is_a2, key, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

ID = "motofuchs"
NAME = "Moto Fuchs"
HOME = "https://motofuchs.com/"
LISTING = HOME
CITY, PROV = "Aldaia", "Valencia"

_CARD = re.compile(r'<div class="card moto-card[^"]*">(.*?)(?=<div class="card moto-card|</main>|$)', re.S)
_HEADER = re.compile(r'card-header[^>]*>\s*([^<]+?)\s*</div>', re.I)
_ID = re.compile(r"detalles\.php\?id=(\d+)")
_IMG = re.compile(r'<img src="(fotos/[^"]+)"')
_CC = re.compile(r"([\d.]+)\s*cc", re.I)
_YEAR = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
_PRICE = re.compile(r"([\d.]+)\s*€")
_KM = re.compile(r"([\d.]+)\s*km", re.I)


def _brand_model(title):
    words = title.split()
    if len(words) >= 2 and key(words[0] + words[1]) in BRANDS:
        return brand(words[0] + " " + words[1]), " ".join(words[2:])
    return brand(words[0]), " ".join(words[1:])


def _to_listing(block, current_year):
    hdr = _HEADER.search(block)
    rid = _ID.search(block)
    img = _IMG.search(block)
    text = re.sub(r"<img[^>]*>", " ", block)  # sin el src, que puede traer números sueltos
    price = _PRICE.search(text)
    if not hdr or not rid or not price:
        return None
    raw_title = html.unescape(hdr.group(1)).strip()
    mk, md = _brand_model(raw_title)
    cc = _CC.search(text)
    ym = _YEAR.search(text)
    km = _KM.search(text)
    title = clean_title(raw_title, mk)
    return {
        "id": f"{ID}:{rid.group(1)}",
        "src": ID,
        "url": f"{HOME}detalles.php?id={rid.group(1)}",
        "t": title,
        "mk": mk,
        "md": model(md) if md else None,
        "y": year(ym.group(1), current_year) if ym else None,
        "km": to_int(km.group(1)) if km else None,
        "p": to_int(price.group(1)),
        "prov": province(PROV),
        "city": CITY,
        "img": HOME + img.group(1) if img else None,
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
    found = {}
    for block in _CARD.findall(resp.text):
        listing = _to_listing(block, current_year)
        if listing:
            found[listing["id"]] = listing
    log(f"{len(found)} motos leídas")
    return list(found.values()), {"status": "ok", "pages": 1, "complete": True}
