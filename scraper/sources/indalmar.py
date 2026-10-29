"""Indalmar Motor (Almería): compraventa de ocasión, ~130 motos.

El listado es una tabla: cada fila (`<tr data-url="/vehiculo/…">`) trae en columnas
la marca, el modelo (con el color en un span), el precio, el tipo, los km, el año y
el combustible. Con `?limit=0,500` devuelve todas las motos en una sola petición.
"""
import html
import re

from ..common import brand, clean_title, is_a2, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

ID = "indalmar"
NAME = "Indalmar Motor"
HOME = "https://www.indalmarmotor.com/"
LISTING = HOME + "motos-segunda-mano?limit=0,500&curPage=1"
CITY, PROV = "Almería", "Almería"

_ROW = re.compile(r'<tr data-url="(/vehiculo/[^"]+)">(.*?)</tr>', re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_SPAN = re.compile(r"<span[^>]*>(.*?)</span>", re.S)


def _text(s):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _to_listing(url, cells, current_year):
    if len(cells) < 7:
        return None
    mk_raw = re.sub(r"\s+motos?$", "", _text(cells[1]), flags=re.I)  # "Bmw Motos"/"SWM Moto" → "Bmw"/"SWM"
    mk = brand(mk_raw)
    col = None
    span = _SPAN.search(cells[2])
    if span:
        col = _text(span.group(1)).lstrip("-– ").strip() or None
    md = _text(_SPAN.sub(" ", cells[2]))
    price = to_int(_text(cells[3]))
    if not price:
        return None
    km = to_int(_text(cells[5]))
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    title = clean_title(f"{mk} {md}".strip(), mk)
    return {
        "id": f"{ID}:{slug}",
        "src": ID,
        "url": HOME.rstrip("/") + url,
        "t": title,
        "mk": mk,
        "md": model(md) if md else None,
        "y": year(_text(cells[6]), current_year),
        "km": km,
        "p": price,
        "prov": province(PROV),
        "city": CITY,
        "img": None,
        "tp": moto_type(_text(cells[4]), f"{title} {md}"),
        "a2": is_a2(title, None),
        "col": color(col, title) if col else color(title),
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
    for url, body in _ROW.findall(resp.text):
        listing = _to_listing(url, _TD.findall(body), current_year)
        if listing:
            found[listing["id"]] = listing
    log(f"{len(found)} motos leídas")
    return list(found.values()), {"status": "ok", "pages": 1, "complete": True}
