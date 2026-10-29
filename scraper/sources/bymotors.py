"""ByMotors (Rivas-Vaciamadrid, Madrid): compraventa de ocasión.

Listado estático y paginado (?page=N): cada tarjeta trae marca y modelo en elementos
aparte, el precio, y los specs (Año, Km, CV, CC) en una lista de definición.
"""
import html
import re
import time

from ..common import brand, clean_title, is_a2, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

ID = "bymotors"
NAME = "ByMotors"
HOME = "https://bymotors.es/"
LISTING = HOME + "stock?filtro_clase_vehiculo=moto"
CITY, PROV = "Rivas-Vaciamadrid", "Madrid"
MAX_PAGES = 20

_CARD = re.compile(r'<article class="bymotors-pro-stock-card">(.*?)</article>', re.S)
_URL = re.compile(r'href="(https://bymotors\.es/stock/([A-Za-z0-9\-]+))"')
_MK = re.compile(r'__title">\s*<span>([^<]+)</span>', re.I)
_MD = re.compile(r"<h5>([^<]+)</h5>", re.I)
_PRICE = re.compile(r'__prices">.*?<strong>([\d.]+)\s*€', re.I | re.S)  # puede haber un precio tachado antes
_P0 = re.compile(r'__prices">\s*<span>([\d.]+)\s*€', re.I)  # precio tachado (anterior), si lo hay
_IMG = re.compile(r'<img src="([^"]+)"')


def _spec(block, label):
    m = re.search(r"<dt>\s*" + label + r"\s*</dt>\s*<dd>([^<]+)</dd>", block, re.I)
    return m.group(1).strip() if m else None


def _to_listing(block, current_year):
    url_m = _URL.search(block)
    price_m = _PRICE.search(block)
    md_m = _MD.search(block)
    if not url_m or not price_m or not md_m:
        return None
    url, rid = url_m.group(1), url_m.group(2)
    mk_m = _MK.search(block)
    mk = brand(html.unescape(mk_m.group(1)).strip()) if mk_m else None
    md = html.unescape(md_m.group(1)).strip()
    img_m = _IMG.search(block)
    p0_m = _P0.search(block)
    p0 = to_int(p0_m.group(1)) if p0_m else None
    price = to_int(price_m.group(1))
    anio = _spec(block, "A[ñn]o")
    km = _spec(block, "Km")
    cv = _spec(block, "CV")
    cc = _spec(block, "CC")
    title = clean_title(f"{mk or ''} {md}".strip(), mk)
    return {
        "id": f"{ID}:{rid}",
        "src": ID,
        "url": url,
        "t": title,
        "mk": mk,
        "md": model(md) if md else None,
        "y": year(anio, current_year) if anio else None,
        "km": to_int(km) if km else None,
        "p": price,
        "p0": p0 if p0 and price and p0 > price else None,
        "prov": province(PROV),
        "city": CITY,
        "img": img_m.group(1) if img_m else None,
        "cv": to_int(cv) if cv else None,
        "cc": to_int(cc) if cc else None,
        "tp": moto_type(None, f"{title} {md}"),
        "a2": is_a2(title, to_int(cv) if cv else None),
        "col": color(title),
        "pro": True,
    }


def scrape(fetcher, known, state, deadline, current_year, log):
    ok, robots_info = fetcher.allowed(LISTING)
    if not ok:
        return [], {"status": "robots_disallowed", "detail": robots_info}
    found = {}
    pages = 0
    for n in range(1, MAX_PAGES + 1):
        if time.monotonic() > deadline:
            return list(found.values()), {"status": "ok", "pages": pages, "complete": False}
        resp = fetcher.get(f"{LISTING}&page={n}")
        if resp.status_code != 200 or is_challenge(resp):
            status = "challenge" if is_challenge(resp) else f"http_{resp.status_code}"
            if n == 1:
                return [], {"status": status, "detail": LISTING, "complete": False}
            break
        before = len(found)
        for block in _CARD.findall(resp.text):
            listing = _to_listing(block, current_year)
            if listing:
                found[listing["id"]] = listing
        pages += 1
        if len(found) == before:  # página sin tarjetas nuevas: se acabó
            break
    log(f"{len(found)} motos leídas ({pages} páginas)")
    return list(found.values()), {"status": "ok", "pages": pages, "complete": True}
