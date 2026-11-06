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
import sys
import time

import requests

CAMPID = "5339241544"   # campid de la cuenta EPN (compartido); el customid separa mootle de guitle
CUSTOMID = "mootle"

OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"

# Marketplace -> moneda esperada (para descartar resultados en otra moneda del país).
MARKETS = {"EBAY_ES": "EUR", "EBAY_FR": "EUR", "EBAY_IT": "EUR", "EBAY_DE": "EUR", "EBAY_GB": "GBP"}

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


def _search(params, marketplace):
    headers = {
        "Authorization": f"Bearer {get_token()}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace,
        "X-EBAY-C-ENDUSERCTX": f"affiliateCampaignId={CAMPID},affiliateReferenceId={CUSTOMID}",
    }
    base = {"filter": "buyingOptions:{FIXED_PRICE},conditionIds:{1000}", "sort": "price", "limit": "5"}
    base.update(params)
    r = requests.get(SEARCH_URL, headers=headers, params=base, timeout=30)
    if r.status_code != 200:
        return []
    return (r.json() or {}).get("itemSummaries") or []


def best_offer(ean=None, text=None, marketplace="EBAY_ES"):
    """Oferta más barata (nuevo, precio fijo, profesional) para un producto. EAN primero;
    si no hay o no devuelve nada, por texto. Devuelve dict o None."""
    cur = MARKETS.get(marketplace, "EUR")
    items = []
    if ean:
        items = _search({"gtin": str(ean)}, marketplace)
    if not items and text:
        items = _search({"q": text}, marketplace)
    for it in items:
        price = it.get("price") or {}
        seller = it.get("seller") or {}
        # moneda del país y, si eBay lo indica, vendedor profesional (business)
        if price.get("currency") != cur:
            continue
        acct = seller.get("sellerAccountType")
        if acct and acct != "BUSINESS":
            continue
        try:
            value = int(round(float(price.get("value"))))
        except (TypeError, ValueError):
            continue
        return {"p": value, "currency": cur, "url": it.get("itemAffiliateWebUrl") or it.get("itemWebUrl"),
                "title": it.get("title"), "market": marketplace,
                "matched": "ean" if ean and items else "texto"}
    return None


def main():
    q = " ".join(sys.argv[1:]).strip()
    if not q:
        print("uso: python -m scraper.ebay \"<EAN>\" | \"<texto>\"")
        return
    is_ean = q.isdigit() and 8 <= len(q) <= 14
    o = best_offer(ean=q if is_ean else None, text=None if is_ean else q)
    print(o if o else "sin resultados (o claves no válidas)")


if __name__ == "__main__":
    main()
