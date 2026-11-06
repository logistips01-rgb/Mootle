"""Refresca las ofertas de eBay para la equipación, por lotes y con tope de llamadas.

Para cada producto de nuestro catálogo (Máximo Moto, Albabike…) busca su oferta en eBay
(por texto: marca + modelo, con filtro estricto de vendedor profesional y coincidencia de
título) y la guarda en data/ebay_offers.json. Luego scraper.equip la mezcla como una oferta
más del mismo producto, con enlace de afiliado.

No recorre todo el catálogo cada día: lleva un cursor y un presupuesto de llamadas
(EBAY_MAX_CALLS) para no pasarse del cupo compartido de la cuenta. Prioriza lo que aún no
tiene oferta y lo más antiguo; reintenta los "sin resultado" solo pasados unos días.

Variables de entorno (todas opcionales salvo las credenciales):
  EBAY_CLIENT_ID / EBAY_CLIENT_SECRET   credenciales (si faltan, no hace nada)
  EBAY_MAX_CALLS     tope de llamadas HTTP por ejecución (def. 400)
  EBAY_MARKETS       mercados separados por coma (def. EBAY_ES,EBAY_DE,EBAY_IT,EBAY_FR)
  EBAY_MIN_PCT       feedback mínimo del vendedor en % (def. 97)
  EBAY_MIN_SCORE     nº mínimo de valoraciones del vendedor (def. 100)
  EBAY_SELLERS       whitelist de vendedores (usernames) separada por coma (def. vacío = cualquiera que cumpla feedback)
  EBAY_STALE_DAYS    caduca una oferta no refrescada en tantos días (def. 30)
  EBAY_MISS_DAYS     no reintenta un "sin resultado" hasta pasados tantos días (def. 12)
  EBAY_PRICEY_DAYS   si eBay salió mucho más caro, no lo revisa hasta pasados tantos días (def. 45)
  EBAY_COMP_MARGIN   margen sobre nuestro mejor precio para considerar eBay "competitivo", en % (def. 10)

    EBAY_CLIENT_ID=... EBAY_CLIENT_SECRET=... python -m scraper.ebay_offers
"""
import json
import os
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from . import ebay

ROOT = Path(__file__).resolve().parent.parent
EQUIP = ROOT / "data" / "equipacion.json"
OFFERS = ROOT / "data" / "ebay_offers.json"
STATE = ROOT / "data" / "ebay_state.json"


def _load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _envi(name, default):
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _days_since(iso):
    try:
        return (date.today() - datetime.fromisoformat(iso).date()).days
    except Exception:
        return 10**6


def _catalog():
    """mids de nuestro catálogo (solo tiendas reales, no eBay) con marca/modelo/categoría."""
    items = _load(EQUIP, {}).get("items", [])
    cat = {}
    for it in items:
        mid = it.get("mid")
        if not mid or it.get("src") == "ebay" or not it.get("p"):
            continue
        g = cat.setdefault(mid, {"mid": mid, "mk": it["mk"], "md": it["md"], "cat": it["cat"], "p": it["p"]})
        if it["p"] < g["p"]:          # nuestro mejor precio para ese producto
            g["p"] = it["p"]
    return cat


def run():
    if not ebay.creds()[0]:
        print("eBay: faltan EBAY_CLIENT_ID / EBAY_CLIENT_SECRET — no se refresca nada.")
        return
    budget = _envi("EBAY_MAX_CALLS", 400)
    markets = [m.strip() for m in os.environ.get("EBAY_MARKETS", "").split(",") if m.strip()] \
        or ebay.DEFAULT_MARKETS
    min_pct = float(os.environ.get("EBAY_MIN_PCT", "") or 97)
    min_score = _envi("EBAY_MIN_SCORE", 100)
    stale = _envi("EBAY_STALE_DAYS", 30)
    miss_days = _envi("EBAY_MISS_DAYS", 12)
    pricey_days = _envi("EBAY_PRICEY_DAYS", 45)
    comp_margin = (float(os.environ.get("EBAY_COMP_MARGIN", "") or 10)) / 100.0
    sellers = [s.strip() for s in os.environ.get("EBAY_SELLERS", "").split(",") if s.strip()] or None

    catalog = _catalog()
    if not catalog:
        print("eBay: no hay catálogo de equipación todavía.")
        return

    offers = _load(OFFERS, {})
    state = _load(STATE, {})
    misses = state.get("misses", {})
    sellers_seen = Counter(state.get("sellers", {}))
    today = date.today().isoformat()

    # Poda: quita ofertas de productos que ya no existen o caducadas por no refrescarse.
    offers = {mid: o for mid, o in offers.items()
              if mid in catalog and _days_since(o.get("ts", "")) <= stale}
    misses = {mid: ts for mid, ts in misses.items() if mid in catalog}

    def competitive(mid):
        """eBay vale la pena para este producto: su precio guardado está dentro del margen
        sobre nuestro mejor precio (o por debajo). Sin oferta aún -> se considera que sí."""
        o = offers.get(mid)
        if not o:
            return True
        return o.get("p", 10**9) <= catalog[mid]["p"] * (1 + comp_margin)

    def skip(mid):
        """¿No gastar llamada en este producto ahora mismo?"""
        if mid in offers:
            age = _days_since(offers[mid].get("ts", ""))
            # eBay mucho más caro: solo se revisa muy de vez en cuando
            return (not competitive(mid)) and age < pricey_days
        # sin oferta: respeta el "miss" reciente
        return mid in misses and _days_since(misses[mid]) < miss_days

    # Orden de trabajo: primero descubrir (sin oferta) y lo competitivo; luego por antigüedad.
    def key(mid):
        if mid not in offers:
            return (1, "")                              # nuevo o miss caducado: primero
        if competitive(mid):
            return (2, offers[mid].get("ts", ""))       # competitivo: refresca por antigüedad
        return (3, offers[mid].get("ts", ""))           # caro: al final (y casi siempre se salta)

    todo = sorted(catalog, key=key)

    counter = {"calls": 0}
    found = refreshed = gone = 0
    for mid in todo:
        if counter["calls"] >= budget:
            break
        if skip(mid):
            continue
        g = catalog[mid]
        o = ebay.lookup(brand=g["mk"], model=g["md"], markets=markets,
                        min_pct=min_pct, min_score=min_score, sellers=sellers, counter=counter)
        if o:
            if mid not in offers:
                found += 1
            else:
                refreshed += 1
            o["ts"] = today
            o["mid"] = mid
            offers[mid] = o
            misses.pop(mid, None)
            if o.get("seller"):
                sellers_seen[o["seller"]] += 1
        else:
            if mid in offers:        # tenía oferta y ya no casa: fuera
                offers.pop(mid, None)
                gone += 1
            misses[mid] = today

    OFFERS.write_text(json.dumps(offers, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    state["misses"] = misses
    state["sellers"] = dict(sellers_seen.most_common())
    state["last_run"] = today
    state["cursor_calls"] = counter["calls"]
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")

    top = ", ".join(f"{s}({n})" for s, n in sellers_seen.most_common(8))
    print(f"eBay: {counter['calls']} llamadas · {found} nuevas, {refreshed} refrescadas, "
          f"{gone} caídas · {len(offers)} ofertas activas de {len(catalog)} productos")
    print(f"eBay vendedores top: {top or '—'}")


if __name__ == "__main__":
    run()
