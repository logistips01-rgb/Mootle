"""Comparador de equipación de moto dentro de Mootle (cascos, guantes, chaquetas, botas…).

Mismo motor que el de motos: lee tiendas, agrupa por marca + modelo, guarda el histórico
de precios por producto y por grupo, y detecta bajadas de precio. El histórico empieza a
acumularse desde el primer día (no hay histórico retroactivo).

Fuente inicial: Máximo Moto (Shopify). Crece con Albabike (feed) y feeds de afiliados.

    python -m scraper.equip            # lee las tiendas y actualiza data/equipacion.json
"""
import argparse
import html as _html
import json
import os
import re
import statistics
import time
from collections import Counter
from datetime import date
from pathlib import Path

import requests

from .fetch import Fetcher, is_challenge
from .models import group_history, price_history
from .pages import slug

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "equipacion.json"
HISTORY = ROOT / "data" / "equip_history.json"
# Productos de Albabike añadidos a mano (datos reales) hasta que llegue su feed. Cada uno
# lleva el `mid` del grupo de Máximo Moto correspondiente, así se comparan en la misma ficha.
SEED_FILE = ROOT / "data" / "albabike_seed.json"
# Ofertas de eBay por producto (las refresca scraper.ebay_offers con enlace de afiliado).
EBAY_OFFERS = ROOT / "data" / "ebay_offers.json"

# product_type de Shopify → categoría de Mootle (ACCESORIOS se deja fuera: demasiado amplio)
CATS = {"CASCO": "casco", "GUANTES": "guantes", "CHAQUETA": "chaqueta",
        "BOTAS": "botas", "PANTALON": "pantalon", "MONO": "mono"}
CAT_NAMES = {"casco": "Cascos", "guantes": "Guantes", "chaqueta": "Chaquetas",
             "botas": "Botas", "pantalon": "Pantalones", "mono": "Monos"}

SHOPIFY_STORES = [
    {"id": "maximomoto", "name": "Máximo Moto", "home": "https://maximo-moto.com/"},
    # outletMOTARD: Shopify (outlet de Scorpion, Alpinestars, HJC, Nox, CGM, Five…). Sus
    # product_type no son los de Máximo ("Casco Integrales", "Alpinestars Gloves"…), así que
    # usa el mapeo por palabras clave (cats="kw") y limpia el sufijo de marca ("Scorpion
    # Helmets" → "Scorpion"). Fuente de comparación; sin afiliación todavía (feed pedido).
    {"id": "outletmotard", "name": "outletMOTARD", "home": "https://outletmotard.es/", "cats": "kw"},
]


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# accesorios que NO son la prenda/casco y ensucian el feed (se descartan)
_ACC = re.compile(r"\b(visor|pantalla|recambio|repuesto|spoiler|bolsa|funda|soporte|mentonera|"
                  r"tornill\w*|adhesiv\w*|pegatina|gafas|c[aá]mara|estuche|spray|limpiador|"
                  r"deflector|carrillera|almohad\w*|perfilador\w*|interiores?)\b", re.I)
# relleno de categoría en el título de la tienda ("CASCO INTEGRAL DE MOTO", "GUANTES DE MOTO"…)
_FILLER = re.compile(r"\b(cascos?|guantes?|chaquetas?|botas?|pantal[oó]n(?:es)?|monos?)\b"
                     r"(\s+(integral\w*|modular\w*|jet|abierto\w*|trail|cross|infantil\w*))*", re.I)


def _is_accessory(title):
    t = (title or "").lower()
    if "pinlock" in t and "incl" not in t:   # "pinlock included" sí es un casco; un pinlock suelto no
        return True
    return bool(_ACC.search(t))


def _pin_status(body_html):
    """A partir de la descripción de la tienda: '¿lleva pinlock (antivaho)?'
    -> 'incluido' (viene con el inserto), 'preparado' (compatible, se compra aparte) o None."""
    if not body_html:
        return None
    t = re.sub(r"<[^>]+>", " ", _html.unescape(body_html)).lower()
    t = re.sub(r"\s+", " ", t)
    if "pinlock" not in t:
        return None
    incl = re.search(r"(inserto|lente|l[aá]mina|lamina|visera)\s+(antivaho\s+)?.{0,12}pinlock"
                     r"|pinlock[^.]{0,25}(incluid|incorpora|de serie)"
                     r"|(incluye|incorpora|con)\s+(un\s+)?(inserto\s+)?pinlock", t)
    ready = re.search(r"(preparad\w*|compatible|lista?\w*|apta?|pre.?instal\w*)\s+(para\s+)?"
                      r"(el\s+)?(sistema\s+)?(antivaho\s+)?pinlock|pinlock\s*(ready|compatible)", t)
    if incl:
        return "incluido"
    if ready:
        return "preparado"
    return None


def _tok(w):
    return w if (any(c.isdigit() for c in w) or len(w) <= 3) else w.capitalize()


def _disp(s):
    return " ".join(_tok(w) for w in s.split())


def _clean_model(title, vendor):
    t = re.sub(r"\s+", " ", _html.unescape(title or "")).strip()
    for pref in filter(None, [vendor, (vendor or "").split(" ")[0]]):  # "MT HELMETS" y "MT"
        if t.upper().startswith(pref.upper() + " "):
            t = t[len(pref):].strip()
            break
    t = _FILLER.sub(" ", t)
    t = re.sub(r"\bde\s+moto\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -·,")
    return _disp(t)


# --- Tiendas con product_type irregular (cats="kw"): mapeo por palabras clave ---
# Excluir accesorios/recambios que no son prenda/casco (viseras, intercomunicadores, packs…).
_KW_SKIP = re.compile(r"visera|visor|intercomunicad|pinlock|\bpack\b|recambio|repuesto", re.I)
_KW_CAT = [("casco", r"casco|helmet"), ("guantes", r"guante|glove"),
           ("chaqueta", r"chaqueta|jacket"), ("mono", r"mono|suit"),
           ("pantalon", r"pantal[oó]n|\bpant"), ("botas", r"bota|boot")]
# "Scorpion Helmets" → "Scorpion", "Five Gloves" → "Five" (marca sin el sufijo de categoría)
_BRAND_SUFFIX = re.compile(r"\s+(helmets?|gloves?|boots?)$", re.I)


def _cat_keywords(ptype):
    t = (ptype or "").strip()
    if not t or _KW_SKIP.search(t):
        return None
    for cat, pat in _KW_CAT:
        if re.search(pat, t, re.I):
            return cat
    return None


def _brand_clean(vendor):
    return _disp(_BRAND_SUFFIX.sub("", (vendor or "").strip()))


def _clean_model_kw(title, vendor):
    """Como _clean_model pero para títulos que empiezan por la categoría ('Casco Scorpion
    EXO-R1…'): quita primero el relleno de categoría y luego la marca del principio."""
    t = re.sub(r"\s+", " ", _html.unescape(title or "")).strip()
    t = _FILLER.sub(" ", t)
    t = re.sub(r"\bde\s+moto\b", " ", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip(" -·,")
    for pref in filter(None, [_brand_clean(vendor), vendor, (vendor or "").split(" ")[0]]):
        if t.upper().startswith(pref.upper() + " "):
            t = t[len(pref):].strip(" -·,")
            break
    return _disp(t)


# --- TradeDoubler (feeds de afiliado: Motocard…) -----------------------------------------
# API de productos de TradeDoubler. El token "PRODUCTS" (40 car., uno por usuario) se guarda
# como secreto del repo (TRADEDOUBLER_PRODUCTS_TOKEN); nunca se escribe en código ni en logs.
TD_API = "https://api.tradedoubler.com/1.0"
# Sitio de mootle en TradeDoubler. ¡CRÍTICO! guitle es 3505824; solo cogemos ofertas cuyo
# productUrl lleve a(3505826), así la comisión es de mootle y nunca de guitle.
MOOTLE_TD_SITE = "3505826"
TD_HOMES = {"motocard": "https://www.motocard.com/"}
TD_NAMES = {"motocard": "Motocard"}   # nombre bonito (el src es slug(programName): "motocard-es")


def _td_name(src):
    return TD_NAMES.get(src.split("-")[0], src.replace("-", " ").title())
_TD_PREV_FIELDS = {"previousprice", "previous_price", "compare_at_price", "listprice", "rrp"}
_TD_PRICE_FIELDS = {"saleprice", "sale_price", "price"}
# Accesorios que caen en una categoría de prenda/casco: el producto ES una visera/recambio
# si el título EMPIEZA por eso (no excluye "Casco ... con visera solar").
# Accesorios/recambios que caen en una categoría de prenda/casco: el producto ES el accesorio
# cuando el título EMPIEZA por eso. Palabra inicial (no substring) para no excluir prendas que
# los mencionen de pasada ("Botas con puntera reforzada", "Casco con visera solar").
_ACC_LEAD = re.compile(r"^\s*(visera|pantalla|puntera|suela|plantilla|deslizador|slider|"
                       r"cord[oó]n(es)?|tacos?|kit|recambio|repuesto|pinlock|intercomunicad\w*|"
                       r"funda|bolsa|maleta|spoiler|protector(es)?|interior(es)?)\b", re.I)


def _looks_accessory(title):
    """Accesorio/recambio y no la prenda/casco: por palabra distintiva en cualquier parte
    (_is_accessory) o por nombre que empieza por el accesorio (_ACC_LEAD)."""
    return _is_accessory(title) or bool(_ACC_LEAD.match(title or ""))


def _to_eur(val):
    """'369.72' / '218.19 EUR' / '1.234,56' → entero de euros. None si no hay número."""
    if val is None:
        return None
    s = re.sub(r"[^\d.,]", "", str(val))
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")   # 1.234,56 → 1234.56
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def _td_token():
    return os.environ.get("TRADEDOUBLER_PRODUCTS_TOKEN", "").strip()


def _td_json(url, token):
    try:
        r = requests.get(url, params={"token": token}, timeout=120,
                         headers={"Accept": "application/json"})
    except requests.RequestException:
        return None, None
    if r.status_code != 200:
        return None, r.status_code
    try:
        return r.json(), 200
    except ValueError:
        return None, r.status_code


def _td_feeds(token):
    j, st = _td_json(f"{TD_API}/productFeeds", token)
    if not j:
        return [], st
    feeds = j.get("feeds", j) if isinstance(j, dict) else j
    return (feeds or []), st


# La API de BÚSQUEDA de TradeDoubler topa en 1000 productos por consulta (10 páginas de 100):
# barrer el feed entero es imposible (Motocard tiene 114k productos, el 99% recambios de motor
# que no comparamos; además a partir del producto 1000 la API corta). Así que en lugar de hojear
# el catálogo pedimos SOLO equipación con búsquedas filtradas por término (q) y, si una categoría
# pasa de 1000, la troceamos por franjas de precio. Motocard es tienda española, así que el título
# va en español y q=casco/guantes/... recupera la prenda; el filtro fino sigue siendo _td_parse.
_TD_Q_TERMS = ["casco", "guantes", "chaqueta", "cazadora", "pantalon",
               "botas", "mono", "traje", "buzo"]
_TD_PRICE_BANDS = [(0, 40), (40, 70), (70, 100), (100, 140),
                   (140, 200), (200, 300), (300, 500), (500, None)]


def _td_matrix(params):
    return "".join(f";{k}={v}" for k, v in params.items() if v is not None)


def _td_search(token, fid, params):
    """Una búsqueda filtrada del feed (q / precio). La API topa en 1000 productos (10×100),
    con reintentos por página. Devuelve (productos, totalHits)."""
    out, total = [], None
    for pg in range(1, 11):
        url = f"{TD_API}/products.json;fid={fid}{_td_matrix(params)};page={pg};pageSize=100"
        j = None
        for attempt in range(3):
            j, st = _td_json(url, token)
            if j is not None:
                break
            time.sleep(2 * (attempt + 1))
        if j is None:
            break
        prods = j.get("products") or []
        if total is None:
            try:
                total = int((j.get("productHeader") or {}).get("totalHits"))
            except (TypeError, ValueError):
                total = None
        out.extend(prods)
        if len(prods) < 100:
            break
    return out, total


def _td_term_products(token, fid, term):
    """Todos los productos del feed para un término, troceando por precio si supera el tope de
    1000 (así no nos quedamos con solo los 1000 más baratos de los cascos, p.ej.)."""
    prods, total = _td_search(token, fid, {"q": term})
    if not (total and total > 1000):
        return prods, total
    acc = list(prods)          # el primer lote (<=1000); las franjas recuperan el resto
    for lo, hi in _TD_PRICE_BANDS:
        p = {"q": term, "minPrice": lo}
        if hi is not None:
            p["maxPrice"] = hi
        bp, _ = _td_search(token, fid, p)
        acc.extend(bp)
    return acc, total


def _td_offer_for_site(p, site_id):
    """Oferta cuyo productUrl lleva a(site_id). Si ninguna es del sitio de mootle → None
    (así nunca cableamos un enlace que pague a guitle)."""
    tag = f"a({site_id})"
    for o in (p.get("offers") or []):
        if tag in (o.get("productUrl") or ""):
            return o
    return None


def _td_price(off, p):
    for pt in reversed(off.get("priceHistory") or []):
        n = _to_eur(((pt or {}).get("price") or {}).get("value"))
        if n:
            return n
    for f in (p.get("fields") or []):
        if (f.get("name") or "").lower() in _TD_PRICE_FIELDS:
            n = _to_eur(f.get("value"))
            if n:
                return n
    return None


def _td_prev(p):
    for f in (p.get("fields") or []):
        if (f.get("name") or "").lower() in _TD_PREV_FIELDS:
            return _to_eur(f.get("value"))
    return None


def _td_parse(p, site_id):
    off = _td_offer_for_site(p, site_id)
    if not off or not off.get("productUrl"):
        return None
    cat = _cat_keywords(" ".join((c.get("name") or "") for c in (p.get("categories") or [])))
    if not cat:
        return None
    raw_title = p.get("name") or ""
    if _looks_accessory(raw_title):
        return None
    price = _td_price(off, p)
    if not price:
        return None
    vendor = (p.get("brand") or "").strip()
    brand = _brand_clean(vendor)
    model = _clean_model_kw(raw_title, vendor)
    if not model:
        return None
    prog = (off.get("programName") or "").strip() or "TradeDoubler"
    src = slug(prog) or "tradedoubler"
    ident = p.get("identifiers") or {}
    pid = off.get("sourceProductId") or ident.get("sku") or ident.get("mpn") or slug(raw_title)
    prev = _td_prev(p)
    return {
        "id": f"{src}:{pid}", "src": src, "url": off["productUrl"],
        "t": f"{brand} {model}".strip(), "mk": brand, "md": model, "cat": cat,
        "p": price, "p0": prev if (prev and prev > price) else None,
        "img": (p.get("productImage") or {}).get("url"),
        "mid": f"{slug(brand)}-{slug(model)}-{cat}",
    }


def read_tradedoubler(site_id=MOOTLE_TD_SITE):
    """Lee los feeds de producto conectados al sitio de mootle (Motocard…). No-op (sin error)
    si falta el token. Devuelve (items, sources) como las tiendas Shopify."""
    token = _td_token()
    if not token:
        return [], {}
    feeds, st = _td_feeds(token)
    seen_prods = 0
    found = {}
    skipped_cats = {}   # diagnóstico: categorías descartadas (no están entre las 6 de mootle)
    for f in feeds:
        fid = f.get("feedId") or f.get("id")
        if not fid:
            continue
        kept0 = len(found)
        prods, per = [], []
        for term in _TD_Q_TERMS:
            tp, tot = _td_term_products(token, fid, term)
            prods.extend(tp)           # los duplicados entre términos colapsan luego por (src, mid)
            per.append(f'{term}={len(tp)}' + (f'/{tot}' if (tot and tot > len(tp)) else ''))
        for p in prods:
            seen_prods += 1
            it = _td_parse(p, site_id)
            if it:
                # dedup de variantes (colores/tallas del mismo modelo) por tienda+mid: la más
                # barata. Evita el mismo casco repetido 3 veces en la ficha.
                k = (it["src"], it["mid"])
                cur = found.get(k)
                if cur is None or it["p"] < cur["p"]:
                    found[k] = it
            else:
                rc = " / ".join(c.get("name") or "" for c in (p.get("categories") or [])) or "(sin categoría)"
                skipped_cats[rc] = skipped_cats.get(rc, 0) + 1
        print(f'[TradeDoubler] feed "{f.get("name") or fid}": por término -> ' + " · ".join(per))
        print(f'[TradeDoubler] feed "{f.get("name") or fid}": leídos={len(prods)}, '
              f'guardados={len(found) - kept0}')
    if skipped_cats:
        top = sorted(skipped_cats.items(), key=lambda x: -x[1])[:12]
        print("[TradeDoubler] categorías descartadas (no comparadas por mootle): "
              + " · ".join(f"{c} ×{n}" for c, n in top))
    if seen_prods and not found:
        print(f"[TradeDoubler] aviso: {seen_prods} productos leídos pero 0 del sitio "
              f"a({site_id}) — ¿feed conectado a otro sitio o sin categoría de equipación?")
    sources = {}
    for it in found.values():
        s = it["src"]
        info = sources.setdefault(s, {"name": _td_name(s),
                                      "home": TD_HOMES.get(s.split("-")[0], ""),
                                      "status": "td", "count": 0})
        info["count"] += 1
    return list(found.values()), sources


def read_shopify(fetcher, store):
    """Lee la equipación de una tienda Shopify por /products.json."""
    found = {}
    pages = 0
    for pg in range(1, 25):
        resp = fetcher.get(store["home"].rstrip("/") + f"/products.json?limit=250&page={pg}")
        if resp.status_code != 200 or is_challenge(resp):
            break
        try:
            prods = (resp.json() or {}).get("products", [])
        except ValueError:
            break
        if not prods:
            break
        pages += 1
        kw = store.get("cats") == "kw"
        for p in prods:
            cat = _cat_keywords(p.get("product_type")) if kw else CATS.get((p.get("product_type") or "").upper())
            if not cat:
                continue
            v = (p.get("variants") or [{}])[0]
            try:
                price = int(round(float(v.get("price"))))
            except (TypeError, ValueError):
                continue
            if not price:
                continue
            try:
                comp = float(v.get("compare_at_price") or 0)
            except (TypeError, ValueError):
                comp = 0
            raw_title = p.get("title") or ""
            if _looks_accessory(raw_title):   # fuera pinlocks, visores, punteras, recambios…
                continue
            vendor = (p.get("vendor") or "").strip()
            brand = _brand_clean(vendor) if kw else _disp(vendor)
            model = _clean_model_kw(raw_title, vendor) if kw else _clean_model(raw_title, vendor)
            if not model:
                continue
            img = (p.get("images") or [{}])[0].get("src")
            listing = {
                "id": f'{store["id"]}:{p["id"]}',
                "src": store["id"],
                "url": store["home"].rstrip("/") + "/products/" + (p.get("handle") or ""),
                "t": f"{brand} {model}".strip(),
                "mk": brand, "md": model, "cat": cat,
                "p": price, "p0": int(round(comp)) if comp > price else None,
                "img": img,
                "mid": f"{slug(brand)}-{slug(model)}-{cat}",
            }
            if cat == "casco":
                pin = _pin_status(p.get("body_html"))
                if pin:
                    listing["pin"] = pin
            found[listing["id"]] = listing
    return list(found.values()), {"name": store["name"], "home": store["home"], "status": "ok", "count": len(found), "complete": pages > 0}


def _drop_price_outliers(results, frac=0.35, min_group=3):
    """Quita items cuyo precio queda muy por debajo de la mediana de su grupo (mismo mid):
    casi siempre un accesorio/recambio mal emparejado que falsea el 'desde' (p. ej. un
    perfilador de 29 € entre botas de 280 €). Conservador: solo cae si queda por debajo del
    `frac` de la mediana del grupo."""
    groups = {}
    for it in results:
        groups.setdefault(it["mid"], []).append(it)
    drop = set()
    for items in groups.values():
        if len(items) < min_group:
            continue
        med = statistics.median([it["p"] for it in items])
        if med <= 0:
            continue
        for it in items:
            if it["p"] < frac * med:
                drop.add(id(it))
    if not drop:
        return results, 0
    kept = [it for it in results if id(it) not in drop]
    return kept, len(results) - len(kept)


def run(dry=False):
    today = date.today().isoformat()
    fetcher = Fetcher()
    old = load(DATA, {}).get("items", [])
    oldmap = {it["id"]: it for it in old}

    sources, results, seen = {}, [], set()
    for store in SHOPIFY_STORES:
        items, info = read_shopify(fetcher, store)
        sources[store["id"]] = info
        print(f'[{store["name"]}] {info["status"]} · {len(items)} productos')
        for it in items:
            prev = oldmap.get(it["id"])
            it["fs"] = prev.get("fs", today) if prev else today
            it["ls"] = today
            it["ph"] = price_history(it, prev, today)
            if prev and prev.get("p") and prev["p"] != it["p"]:
                it["pa"], it["pc"] = prev["p"], today
            elif prev and prev.get("pa"):
                it["pa"], it["pc"] = prev["pa"], prev.get("pc")
            results.append(it)
            seen.add(it["id"])

    # Albabike (seed manual con datos reales, hasta tener su feed): mismos campos y merge.
    seed = load(SEED_FILE, [])
    if seed:
        sources["albabike"] = {"name": "Albabike", "home": "https://albabike.com/", "status": "seed", "count": len(seed)}
        print(f"[Albabike] seed · {len(seed)} productos")
        for it in seed:
            prev = oldmap.get(it["id"])
            it["fs"] = prev.get("fs", today) if prev else today
            it["ls"] = today
            it["ph"] = price_history(it, prev, today)
            if prev and prev.get("p") and prev["p"] != it["p"]:
                it["pa"], it["pc"] = prev["p"], today
            elif prev and prev.get("pa"):
                it["pa"], it["pc"] = prev["pa"], prev.get("pc")
            results.append(it)
            seen.add(it["id"])

    # TradeDoubler (feeds de afiliado conectados al sitio de mootle: Motocard…). Enlace de
    # afiliado ya incluido en cada producto. No hace nada si falta el token (secreto).
    td_items, td_sources = read_tradedoubler()
    # Guardia anti-lectura-parcial: si un feed de TradeDoubler devuelve muchos menos productos
    # que la última vez (lectura incompleta), conservamos el catálogo anterior de esa tienda en
    # lugar de pisarlo con una lectura a medias (evita el baile 871→31).
    old_sources = load(DATA, {}).get("sources", {})
    td_src_ids = {s for s, inf in old_sources.items() if inf.get("status") == "td"} | set(td_sources)
    new_cnt = Counter(it["src"] for it in td_items)
    old_cnt = Counter(it.get("src") for it in old if it.get("src") in td_src_ids)
    for s in td_src_ids:
        oc, nc = old_cnt.get(s, 0), new_cnt.get(s, 0)
        if oc >= 20 and nc < 0.5 * oc:
            td_items = [it for it in td_items if it["src"] != s] + [it for it in old if it.get("src") == s]
            td_sources[s] = old_sources.get(s, {"name": _td_name(s),
                                                "home": TD_HOMES.get(s.split("-")[0], ""),
                                                "status": "td", "count": 0})
            td_sources[s]["count"] = oc
            print(f"[TradeDoubler] {s}: lectura parcial ({nc} < {oc}); conservado catálogo anterior")
    if td_sources:
        sources.update(td_sources)
    for it in td_items:
        prev = oldmap.get(it["id"])
        it["fs"] = prev.get("fs", today) if prev else today
        it["ls"] = today
        it["ph"] = price_history(it, prev, today)
        if prev and prev.get("p") and prev["p"] != it["p"]:
            it["pa"], it["pc"] = prev["p"], today
        elif prev and prev.get("pa"):
            it["pa"], it["pc"] = prev["pa"], prev.get("pc")
        results.append(it)
        seen.add(it["id"])
    for s, info in td_sources.items():
        print(f'[{info["name"]}] td · {info["count"]} productos')

    # eBay: una oferta más por producto (con enlace de afiliado). Solo para productos que ya
    # tenemos en el catálogo (empareja por `mid`); así es una oferta extra del mismo producto.
    ebay_offers = load(EBAY_OFFERS, {})
    if ebay_offers:
        info = {m["mid"]: (m["mk"], m["md"], m["cat"], m.get("img")) for m in results}
        n_ebay = 0
        for mid, o in ebay_offers.items():
            ref = info.get(mid)
            if not ref or not o.get("p") or not o.get("url"):
                continue
            mk, md, cat, img = ref
            it = {"id": f"ebay:{mid}", "src": "ebay", "url": o["url"],
                  "t": o.get("title") or f"{mk} {md}".strip(), "mk": mk, "md": md, "cat": cat,
                  "p": int(o["p"]), "p0": o.get("p0"), "img": o.get("img") or img, "mid": mid}
            prev = oldmap.get(it["id"])
            it["fs"] = prev.get("fs", today) if prev else today
            it["ls"] = today
            it["ph"] = price_history(it, prev, today)
            if prev and prev.get("p") and prev["p"] != it["p"]:
                it["pa"], it["pc"] = prev["p"], today
            elif prev and prev.get("pa"):
                it["pa"], it["pc"] = prev["pa"], prev.get("pc")
            results.append(it)
            seen.add(it["id"])
            n_ebay += 1
        if n_ebay:
            sources["ebay"] = {"name": "eBay", "home": "https://www.ebay.es/", "status": "api", "count": n_ebay}
            print(f"[eBay] {n_ebay} ofertas emparejadas")

    # saneo: fuera accesorios/recambios mal emparejados que quedan muy por debajo del grupo
    results, n_out = _drop_price_outliers(results)
    if n_out:
        print(f"Saneo de precios: {n_out} items descartados (muy por debajo de la mediana del grupo)")

    # precio de mercado (mediana del grupo) para detectar chollos cuando hay varias ofertas
    by_mid = {}
    for it in results:
        by_mid.setdefault(it["mid"], []).append(it["p"])
    for it in results:
        pr = by_mid[it["mid"]]
        if len(pr) >= 2:
            it["mkt"] = int(statistics.median(pr))

    history = group_history(results, load(HISTORY, {}), today)
    print(f"Equipación: {len(results)} productos · {len(by_mid)} grupos · {len(sources)} tiendas")
    if dry:
        return
    DATA.write_text(json.dumps({"updated": today, "sources": sources, "items": results},
                               ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    from . import equip_pages
    n = equip_pages.build(load(DATA, {}), history)
    print(f"Páginas de equipación: {n} ficheros nuevos o cambiados")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    run(dry=args.dry_run)


if __name__ == "__main__":
    main()
