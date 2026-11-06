"""Cliente de la eBay Browse API para traer precios de equipación con enlace de afiliado.

Busca cada producto por EAN (gtin); si no hay EAN o no devuelve nada, cae a búsqueda por
texto (marca + modelo). Solo artículos NUEVOS, a precio fijo y de vendedor profesional, para
comparar lo mismo que en las tiendas. Cada resultado trae `itemAffiliateWebUrl`: el enlace ya
con la comisión (campaña mootle, customid "mootle").

Credenciales (secretos del repo / variables de entorno):
  EBAY_CLIENT_ID      App ID (Client ID) de Production
  EBAY_CLIENT_SECRET  Cert ID (Client Secret) de Production

Prueba rápida:
  EBAY_CLIENT_ID=... EBAY_CLIENT_SECRET=... python -m scraper.ebay "8054633217728"
  EBAY_CLIENT_ID=... EBAY_CLIENT_SECRET=... python -m scraper.ebay "LS2 FF808 casco"
"""
import base64
import os
import re
import sys
import time
import unicodedata

import requests

CAMPID = "5339241544"   # campid de la cuenta EPN (compartido); el customid separa mootle de guitle
CUSTOMID = "mootle"

OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"

# Marketplace -> moneda esperada (para descartar resultados en otra moneda del país).
MARKETS = {"EBAY_ES": "EUR", "EBAY_FR": "EUR", "EBAY_IT": "EUR", "EBAY_DE": "EUR", "EBAY_GB": "GBP"}
# Mercados por defecto (todos EUR, envían a España). ES primero, luego DE (FC-Moto y el
# grueso del catálogo de marcas). IT/FR se añaden con EBAY_MARKETS cuando haya más cupo:
# buscar en 4 mercados multiplica las llamadas en los productos que eBay no tiene.
DEFAULT_MARKETS = ["EBAY_ES", "EBAY_DE"]

_token = {"value": None, "exp": 0}


def creds():
    cid, secret = os.environ.get("EBAY_CLIENT_ID"), os.environ.get("EBAY_CLIENT_SECRET")
    return (cid, secret) if cid and secret else (None, None)


def get_token():
    """Token OAuth client_credentials, cacheado hasta poco antes de caducar."""
    if _token["value"] and time.time() < _token["exp"]:
        return _token["value"]
    cid, secret = creds()
    if not cid:
        raise RuntimeError("Faltan EBAY_CLIENT_ID / EBAY_CLIENT_SECRET")
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    r = requests.post(OAUTH_URL, timeout=30,
                      headers={"Authorization": f"Basic {auth}",
                               "Content-Type": "application/x-www-form-urlencoded"},
                      data={"grant_type": "client_credentials", "scope": SCOPE})
    r.raise_for_status()
    j = r.json()
    _token["value"] = j["access_token"]
    _token["exp"] = time.time() + int(j.get("expires_in", 7200)) - 120
    return _token["value"]


def _search(params, marketplace, sellers=None):
    """Una llamada a item_summary/search. Devuelve (itemSummaries, status_code)."""
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace,
        "X-EBAY-C-ENDUSERCTX": f"affiliateCampaignId={CAMPID},affiliateReferenceId={CUSTOMID}",
    }
    filt = "buyingOptions:{FIXED_PRICE},conditionIds:{1000}"
    if sellers:
        filt += ",sellers:{" + "|".join(sellers) + "}"
    base = {"filter": filt, "sort": "price", "limit": "10"}
    base.update(params)
    try:
        r = requests.get(SEARCH_URL, headers=headers, params=base, timeout=30)
    except requests.RequestException:
        return [], 0
    if r.status_code != 200:
        return [], r.status_code
    return ((r.json() or {}).get("itemSummaries") or []), 200


# --- emparejamiento por texto: evitar que un resultado cualquiera se cuele como "el mismo" ---

def _fold(s):
    s = unicodedata.normalize("NFKD", str(s or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


# palabras de color / talla / relleno que no identifican el modelo
_NOISE = {"casco", "guantes", "guante", "chaqueta", "botas", "bota", "pantalon", "mono", "moto",
          "hombre", "mujer", "unisex", "negro", "blanco", "rojo", "azul", "gris", "verde",
          "amarillo", "naranja", "rosa", "talla", "nuevo", "new", "integral", "modular", "jet"}


def match_ok(brand, model, title):
    """¿El resultado de eBay es de verdad este producto? Exige la marca y los códigos de
    modelo (p. ej. "FF808"); si el modelo no tiene código, pide al menos dos palabras suyas."""
    t = _fold(title)
    if not t:
        return False
    b = _fold(brand)
    if b and b.split(" ")[0] not in t:
        return False
    toks = [w for w in _fold(model).split(" ") if len(w) >= 2 and w not in _NOISE]
    codes = [w for w in toks if any(c.isdigit() for c in w)]
    if codes:
        return all(c in t for c in codes)
    sig = [w for w in toks if len(w) >= 3]
    if not sig:
        return bool(b)          # modelo sin nada distintivo: basta con que coincida la marca
    hits = sum(1 for w in sig if w in t)
    return hits >= min(2, len(sig))


def _pick(items, cur, min_pct, min_score, brand=None, model=None):
    """Primera oferta válida: moneda del país, vendedor profesional con buen feedback y,
    si se pasan marca/modelo, que el título case de verdad. items ya viene de barato a caro."""
    for it in items:
        price = it.get("price") or {}
        if price.get("currency") != cur:
            continue
        seller = it.get("seller") or {}
        if (seller.get("sellerAccountType") or "BUSINESS") != "BUSINESS":
            continue
        try:
            pct = float(seller.get("feedbackPercentage") or 0)
            score = int(seller.get("feedbackScore") or 0)
        except (TypeError, ValueError):
            pct, score = 0, 0
        if pct < min_pct or score < min_score:
            continue
        if brand is not None and not match_ok(brand, model or "", it.get("title") or ""):
            continue
        try:
            value = int(round(float(price.get("value"))))
        except (TypeError, ValueError):
            continue
        mp = it.get("marketingPrice") or {}
        try:
            p0 = int(round(float((mp.get("originalPrice") or {}).get("value"))))
        except (TypeError, ValueError):
            p0 = None
        return {"p": value, "p0": p0 if (p0 and p0 > value) else None, "currency": cur,
                "url": it.get("itemAffiliateWebUrl") or it.get("itemWebUrl"),
                "title": it.get("title"),
                "seller": seller.get("username"), "feedback_pct": pct, "feedback_score": score,
                "img": ((it.get("image") or {}).get("imageUrl"))}
    return None


def lookup(brand=None, model=None, ean=None, text=None, markets=None,
           min_pct=97.0, min_score=100, sellers=None, counter=None):
    """Mejor oferta (nuevo, precio fijo, profesional) recorriendo los mercados en orden y
    parando en el primero con coincidencia válida. `counter` (dict con "calls") suma las
    llamadas HTTP hechas. Devuelve dict (con `market` y `matched`) o None."""
    markets = markets or DEFAULT_MARKETS

    def bump(n=1):
        if counter is not None:
            counter["calls"] = counter.get("calls", 0) + n

    for mp in markets:
        cur = MARKETS.get(mp, "EUR")
        if ean:
            items, st = _search({"gtin": str(ean)}, mp, sellers)
            bump()
            o = _pick(items, cur, min_pct, min_score)   # por EAN no hace falta guard de texto
            if o:
                o.update({"market": mp, "matched": "ean"})
                return o
        q = text or f"{brand or ''} {model or ''}".strip()
        if q:
            items, st = _search({"q": q}, mp, sellers)
            bump()
            o = _pick(items, cur, min_pct, min_score, brand=brand, model=model)
            if o:
                o.update({"market": mp, "matched": "texto"})
                return o
    return None


def best_offer(ean=None, text=None, marketplace="EBAY_ES"):
    """Compatibilidad / CLI: una sola búsqueda en un mercado."""
    return lookup(ean=ean, text=text, markets=[marketplace])


def main():
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        print("uso: python -m scraper.ebay \"<EAN>\" | \"<texto>\"")
        return
    is_ean = q.isdigit() and 8 <= len(q) <= 14
    cnt = {"calls": 0}
    o = lookup(ean=q if is_ean else None,
               text=None if is_ean else q,
               brand=None if is_ean else q.split(" ")[0],
               model=None if is_ean else " ".join(q.split(" ")[1:]),
               counter=cnt)
    print(f"llamadas: {cnt['calls']}")
    print(o if o else "sin resultados (o claves no válidas)")


if __name__ == "__main__":
    main()
