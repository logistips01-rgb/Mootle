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
import re
import statistics
from datetime import date
from pathlib import Path

from .fetch import Fetcher, is_challenge
from .models import group_history, price_history
from .pages import slug

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "equipacion.json"
HISTORY = ROOT / "data" / "equip_history.json"
# Productos de Albabike añadidos a mano (datos reales) hasta que llegue su feed. Cada uno
# lleva el `mid` del grupo de Máximo Moto correspondiente, así se comparan en la misma ficha.
SEED_FILE = ROOT / "data" / "albabike_seed.json"

# product_type de Shopify → categoría de Mootle (ACCESORIOS se deja fuera: demasiado amplio)
CATS = {"CASCO": "casco", "GUANTES": "guantes", "CHAQUETA": "chaqueta",
        "BOTAS": "botas", "PANTALON": "pantalon", "MONO": "mono"}
CAT_NAMES = {"casco": "Cascos", "guantes": "Guantes", "chaqueta": "Chaquetas",
             "botas": "Botas", "pantalon": "Pantalones", "mono": "Monos"}

SHOPIFY_STORES = [
    {"id": "maximomoto", "name": "Máximo Moto", "home": "https://maximo-moto.com/"},
]


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


# accesorios que NO son la prenda/casco y ensucian el feed (se descartan)
_ACC = re.compile(r"\b(visor|pantalla|recambio|repuesto|spoiler|bolsa|funda|soporte|mentonera|"
                  r"tornill\w*|adhesiv\w*|pegatina|gafas|c[aá]mara|estuche|spray|limpiador|"
                  r"deflector|carrillera|almohad\w*|interiores?)\b", re.I)
# relleno de categoría en el título de la tienda ("CASCO INTEGRAL DE MOTO", "GUANTES DE MOTO"…)
_FILLER = re.compile(r"\b(cascos?|guantes?|chaquetas?|botas?|pantal[oó]n(?:es)?|monos?)\b"
                     r"(\s+(integral\w*|modular\w*|jet|abierto\w*|trail|cross|infantil\w*))*", re.I)


def _is_accessory(title):
    t = (title or "").lower()
    if "pinlock" in t and "incl" not in t:   # "pinlock included" sí es un casco; un pinlock suelto no
        return True
    return bool(_ACC.search(t))


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
        for p in prods:
            cat = CATS.get((p.get("product_type") or "").upper())
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
            if _is_accessory(raw_title):   # fuera pinlocks, visores, recambios…
                continue
            vendor = (p.get("vendor") or "").strip()
            brand = _disp(vendor)
            model = _clean_model(raw_title, vendor)
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
            found[listing["id"]] = listing
    return list(found.values()), {"name": store["name"], "home": store["home"], "status": "ok", "count": len(found), "complete": pages > 0}


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
