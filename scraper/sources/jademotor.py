"""Jade Motor (Cartagena, Murcia): ocasión, ~36 motos.

Listado estático en una página (/ocasion): cada tarjeta (`<a class="moto">`) trae el
enlace, el título, una línea de datos "AÑO · KM km · CC cc" y el precio.
"""
import html
import re

from ..common import BRANDS, brand, clean_title, is_a2, key, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

ID = "jademotor"
NAME = "Jade Motor"
HOME = "https://jademotor.com/"
LISTING = HOME + "ocasion"
CITY, PROV = "Cartagena", "Murcia"

_CARD = re.compile(r'<a class="moto" href="(/producto/[^"]+)">(.*?)</a>', re.S)
_NOM = re.compile(r'class="nom">([^<]+)<', re.I)
_DATOS = re.compile(r'class="datos-moto">([^<]+)<', re.I)
_PRECIO = re.compile(r'class="precio">\s*([\d.]+)', re.I)
_IMG = re.compile(r'<img src="([^"]+)"')
_YEAR = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")
_KM = re.compile(r"([\d.]+)\s*km", re.I)
_CC = re.compile(r"([\d.]+)\s*cc", re.I)


def _brand_model(title):
    words = title.split()
    if len(words) >= 2 and key(words[0] + words[1]) in BRANDS:
        return brand(words[0] + " " + words[1]), " ".join(words[2:])
    return brand(words[0]), " ".join(words[1:])


def _to_listing(url, block, current_year):
    nom = _NOM.search(block)
    precio = _PRECIO.search(block)
    if not nom or not precio:
        return None
    raw_title = html.unescape(nom.group(1)).strip()
    mk, md = _brand_model(raw_title)
    datos = _DATOS.search(block)
    dtext = datos.group(1) if datos else ""
    ym = _YEAR.search(dtext)
    km = _KM.search(dtext)
    cc = _CC.search(dtext)
    img = _IMG.search(block)
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    title = clean_title(raw_title, mk)
    return {
        "id": f"{ID}:{slug}",
        "src": ID,
        "url": HOME.rstrip("/") + url,
        "t": title,
        "mk": mk,
        "md": model(md) if md else None,
        "y": year(ym.group(1), current_year) if ym else None,
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
    found = {}
    for url, block in _CARD.findall(resp.text):
        listing = _to_listing(url, block, current_year)
        if listing:
            found[listing["id"]] = listing
    log(f"{len(found)} motos leídas")
    return list(found.values()), {"status": "ok", "pages": 1, "complete": True}
