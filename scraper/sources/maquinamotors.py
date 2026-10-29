"""Máquina Motors (maquinamotors.com): concesionario con tiendas en varias ciudades, ~400 motos de ocasión.

Tienda Magento: el listado `/motos-de-ocasion.html?p=N` trae unas 20 motos por página con marca,
modelo, km, año, cilindrada, carnet, tienda y precio. robots.txt lo permite todo con
`Crawl-delay: 3` (el Fetcher espera 3-6 s). Se lee entero en cada ejecución (~20 páginas),
así que lo que no aparece se ha vendido.
"""
import re

from bs4 import BeautifulSoup

from ..common import brand, clean_title, fold, is_a2, model, moto_type, province, to_int, year
from ..fetch import is_challenge
from ..models import color

ID = "maquinamotors"
NAME = "Máquina Motors"
HOME = "https://maquinamotors.com/"
LIST = "https://maquinamotors.com/motos-de-ocasion.html"
MAX_PAGES = 60
# Tiendas (lo que pone tras "Maquina Motors") → (ciudad, provincia). Las de calles son de Barcelona ciudad.
STORES = {
    "valencia": ("Valencia", "Valencia"), "honda valencia": ("Valencia", "Valencia"),
    "consell de cent": ("Barcelona", "Barcelona"), "provenca": ("Barcelona", "Barcelona"),
    "numancia": ("Barcelona", "Barcelona"), "brusi": ("Barcelona", "Barcelona"), "bruc": ("Barcelona", "Barcelona"),
    "mollet": ("Mollet del Vallès", "Barcelona"), "terrassa": ("Terrassa", "Barcelona"), "manresa": ("Manresa", "Barcelona"),
}


def page_url(n):
    return LIST if n <= 1 else f"{LIST}?p={n}"


def _text(el):
    return re.sub(r"\s+", " ", el.get_text(" ", strip=True)) if el else ""


def to_listing(item, current_year):
    link = item.select_one("a.product-item-link")
    price = item.select_one("[data-price-amount]")
    box = item.select_one("[data-product-id]")
    if not link or not price or not box:
        return None
    mk_raw = _text(link.find("strong"))
    full = _text(link)
    md_raw = full[len(mk_raw):].strip() if full.startswith(mk_raw) else full
    mk = brand(mk_raw)
    # Características: km, año, cilindrada, carnet y tienda, cada una con su icono (alt del <img>).
    feats = {}
    for li in item.select("ul.caracteristicas-moto li"):
        img = li.find("img")
        alt = (img.get("alt") or "").lower() if img else ""
        feats[alt.split()[0] if alt else len(feats)] = _text(li)
    shop = re.sub(r"^m[aá]quina motors\s*", "", feats.get("tienda", ""), flags=re.I).strip()
    city, prov = STORES.get(fold(shop), (shop.title() or None, None))
    title = clean_title(f"{mk_raw} {md_raw}", mk)
    licence = feats.get("licencia")
    img = item.select_one(".foto-moto img")
    return {
        "id": f"{ID}:{box.get('data-product-id')}",
        "src": ID,
        "url": link.get("href"),
        "t": title,
        "mk": mk,
        "md": model(md_raw),
        "y": year(feats.get("año"), current_year),
        "km": to_int(feats.get("km")) if feats.get("km") else 0,
        "p": to_int(float(price.get("data-price-amount") or 0)),
        "prov": prov or province(city),
        "city": city,
        "img": img.get("src") if img else None,
        "cc": to_int(feats.get("cilindrada")),
        "tp": moto_type(None, title),
        "a2": is_a2(title, None, licence),
        "col": color(title),
        "pro": True,
        "res": bool(re.search(r"\breservada\b", _text(item), re.I)) or None,
    }


def scrape(fetcher, known, state, deadline, current_year, log):
    ok, robots_info = fetcher.allowed(LIST)
    if not ok:
        return [], {"status": "robots_disallowed", "detail": robots_info}
    found, pages = {}, 0
    for n in range(1, MAX_PAGES + 1):
        resp = fetcher.get(page_url(n))
        if resp.status_code != 200 or is_challenge(resp):
            status = "challenge" if is_challenge(resp) else f"http_{resp.status_code}"
            log(f"⚠ {status} en la página {n}")
            return list(found.values()), {"status": status, "detail": f"página {n}", "pages": pages, "complete": False}
        pages += 1
        soup = BeautifulSoup(resp.text, "html.parser")
        new = 0
        for item in soup.select(".product-item-info"):
            listing = to_listing(item, current_year)
            if listing and listing["p"] and listing["id"] not in found:
                found[listing["id"]] = listing
                new += 1
        # Pasada la última página, Magento repite la última: sin motos nuevas, hemos terminado.
        if new == 0:
            break
    return list(found.values()), {"status": "ok", "pages": pages, "complete": bool(found)}
