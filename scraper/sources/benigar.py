"""Benigar (Elche/Alicante): concesionario BMW Motorrad, motos de ocasión.

Listado en una sola página (/motos-ocasion): cada tarjeta trae el enlace a la ficha
(`/motos-ocasion/<marca>/<modelo>/<id>`), el título, el precio y, con sus iconos, los
km y el año. La marca se saca del propio enlace, que es la vía más fiable.
"""
import html
import re

from ..common import brand, clean_title, is_a2, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

ID = "benigar"
NAME = "Benigar"
HOME = "https://benigar.com/"
LISTING = HOME + "motos-ocasion"
CITY, PROV = "Elche", "Alicante"

_CARD = re.compile(
    r'<a href="(/motos-ocasion/([a-z0-9\-]+)/[^"]+?/\d+)"[^>]*>(.*?)(?=<a href="/motos-ocasion/[a-z0-9\-]+/[^"]+?/\d+"|$)',
    re.S,
)
_TITLE = re.compile(r'class="titulo[^"]*"[^>]*>([^<]+)<', re.I)
_PRICE = re.compile(r'class="precio[^"]*">\s*<span>([\d.]+)\s*€', re.I)
_KM = re.compile(r"icono-km\.svg[^>]*>\s*<span>([\d.]+)\s*km", re.I)
_YEAR = re.compile(r"icono-calendario\.svg[^>]*>\s*<span>((?:19|20)\d{2})", re.I)


def _to_listing(url, mk_slug, block, current_year):
    title_m = _TITLE.search(block)
    price_m = _PRICE.search(block)
    if not title_m or not price_m:
        return None
    raw_title = html.unescape(title_m.group(1)).strip()
    mk = brand(mk_slug.replace("-", " "))
    md = raw_title[len(mk):].strip() if mk and raw_title.lower().startswith(mk.lower()) else raw_title
    km_m = _KM.search(block)
    year_m = _YEAR.search(block)
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    title = clean_title(raw_title, mk)
    return {
        "id": f"{ID}:{slug}",
        "src": ID,
        "url": HOME.rstrip("/") + url,
        "t": title,
        "mk": mk,
        "md": model(md) if md else None,
        "y": year(year_m.group(1), current_year) if year_m else None,
        "km": to_int(km_m.group(1)) if km_m else None,
        "p": to_int(price_m.group(1)),
        "prov": province(PROV),
        "city": CITY,
        "img": None,
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
    for url, mk_slug, block in _CARD.findall(resp.text):
        listing = _to_listing(url, mk_slug, block, current_year)
        if listing:
            found[listing["id"]] = listing
    log(f"{len(found)} motos leídas")
    return list(found.values()), {"status": "ok", "pages": 1, "complete": True}
