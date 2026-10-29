"""Lee todas las fuentes y actualiza data/listings.json (lo que carga la web).

    python -m scraper.run                       # todas las fuentes, 50 min como mucho cada una
    python -m scraper.run --only motoocasion    # solo algunas
    python -m scraper.run --minutes 5 --dry-run # informe sin tocar data/

Cada fuente va en su propio hilo y a su ritmo (3-6 s entre peticiones, robots.txt respetado).
"""
import argparse
import json
import statistics
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from .common import key
from .fetch import Fetcher
from .sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "data" / "listings.json"
STATE = ROOT / "data" / "state.json"
DROP_AFTER_DAYS = 7    # anuncios de fuentes que se leen por partes y no se han vuelto a ver
MARKET_MIN = 5         # anuncios del mismo modelo y año para dar precio de mercado
MARKET_YEARS = 1       # ± años que entran en la comparación


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def market_prices(items):
    """Mediana de precio por marca + modelo + año (± MARKET_YEARS), si hay MARKET_MIN anuncios o más."""
    by_model = defaultdict(lambda: defaultdict(list))
    for it in items:
        if it.get("mk") and it.get("md") and it.get("y") and it.get("p"):
            by_model[(it["mk"], key(it["md"]))][it["y"]].append(it["p"])
    for it in items:
        it.pop("mkt", None)
        years = by_model.get((it.get("mk"), key(it.get("md"))))
        if not years or not it.get("y") or not it.get("p"):
            continue
        prices = [p for y in range(it["y"] - MARKET_YEARS, it["y"] + MARKET_YEARS + 1) for p in years.get(y, [])]
        if len(prices) >= MARKET_MIN:
            it["mkt"] = int(statistics.median(prices))


def _same_model(a, b):
    """2 = mismo modelo, 1 = uno empieza por el otro ('nc750x' / 'nc750xa2'), 0 = distintos.
    Un modelo sin número no vale contra uno con número ('rc' no es 'rc390')."""
    ka, kb = key(a), key(b)
    if not ka or not kb:
        return 0
    if ka == kb:
        return 2
    short, long_ = sorted((ka, kb), key=len)
    digit = lambda k: any(c.isdigit() for c in k)
    return 1 if long_.startswith(short) and len(short) >= 3 and (digit(short) or not digit(long_)) else 0


def link_duplicates(items):
    """Marca con el mismo `g` la misma moto anunciada en varias webs (p. ej. un concesionario que
    también publica en motos.net): misma marca, año y km, modelo compatible y precio parecido.
    Cada anuncio se empareja como mucho con uno de cada otra web, empezando por los más parecidos.
    La web enseña la más barata del grupo y "también en…" con el resto."""
    by_bike = defaultdict(list)
    for it in items:
        it.pop("g", None)
        if it.get("mk") and it.get("y") and (it.get("km") or 0) >= 100 and it.get("p"):
            by_bike[(it["mk"], it["y"], it["km"])].append(it)
    pairs = 0
    for bikes in by_bike.values():
        if len({b["src"] for b in bikes}) < 2:
            continue
        candidates = []
        for a in bikes:
            for b in bikes:
                score = _same_model(a.get("md"), b.get("md")) if a["src"] < b["src"] else 0
                gap = abs(a["p"] - b["p"]) / min(a["p"], b["p"])
                if score and gap <= 0.3:
                    candidates.append((-score, gap, a["id"], b["id"], a, b))
        paired = set()
        for _, _, _, _, a, b in sorted(candidates, key=lambda c: c[:4]):
            if (a["id"], b["src"]) in paired or (b["id"], a["src"]) in paired:
                continue
            paired.update({(a["id"], b["src"]), (b["id"], a["src"])})
            g = a.get("g") or b.get("g") or a["id"]
            for it in bikes:  # une los grupos de los dos
                if it.get("g") and it["g"] in (a.get("g"), b.get("g")):
                    it["g"] = g
            a["g"] = b["g"] = g
            pairs += 1
    return pairs


def merge(old_items, results, today):
    """Junta lo leído con lo que había. results: {fuente: (anuncios, info)}."""
    old = {it["id"]: it for it in old_items}
    out = {}
    for src, (found, info) in results.items():
        for it in found:
            prev = old.get(it["id"])
            it["fs"] = prev.get("fs", today) if prev else today
            it["ls"] = today
            if prev and prev.get("p") and it.get("p") and prev["p"] != it["p"]:
                it["pa"], it["pc"] = prev["p"], today  # precio anterior y día del cambio
            elif prev and prev.get("pa"):
                it["pa"], it["pc"] = prev["pa"], prev.get("pc")
            out[it["id"]] = {k: v for k, v in it.items() if v is not None}
    limit = (date.fromisoformat(today) - timedelta(days=DROP_AFTER_DAYS)).isoformat()
    for it in old_items:
        if it["id"] in out:
            continue
        found, info = results.get(it["src"], (None, None))
        if info and info.get("complete") and info.get("status") == "ok":
            continue  # la fuente se ha leído entera y ya no está: vendida
        if it.get("ls", today) >= limit:
            out[it["id"]] = it
    return list(out.values())


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="ids de fuente (por defecto, todas)")
    ap.add_argument("--minutes", type=float, default=50, help="tiempo máximo por fuente")
    ap.add_argument("--dry-run", action="store_true", help="no escribe data/")
    args = ap.parse_args(argv)

    chosen = {k: v for k, v in SOURCES.items() if not args.only or k in args.only}
    if not chosen:
        raise SystemExit(f"Ninguna fuente coincide con {args.only}. Disponibles: {', '.join(SOURCES)}")

    data = load(LISTINGS, {"sources": {}, "items": []})
    state = load(STATE, {})
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    deadline = time.monotonic() + args.minutes * 60

    def run_source(src_id):
        mod = chosen[src_id]
        known = {it["id"] for it in data["items"] if it.get("src") == src_id}
        src_state = state.setdefault(src_id, {})
        log = lambda msg: print(f"[{mod.NAME}] {msg}", flush=True)
        try:
            return src_id, mod.scrape(Fetcher(), known, src_state, deadline, now.year, log)
        except Exception as exc:  # una fuente rota no para las demás
            log(f"💥 {type(exc).__name__}: {exc}")
            return src_id, ([], {"status": "error", "detail": f"{type(exc).__name__}: {exc}"[:300]})

    with ThreadPoolExecutor(max_workers=len(chosen)) as pool:
        results = dict(pool.map(run_source, chosen))

    items = merge(data["items"], results, today)
    market_prices(items)
    dups = link_duplicates(items)
    items.sort(key=lambda it: (it.get("p") or 10**9, it["id"]))

    sources = data.get("sources", {})
    for src_id, (found, info) in results.items():
        mod = SOURCES[src_id]
        entry = sources.setdefault(src_id, {})
        entry.update({"name": mod.NAME, "home": mod.HOME, "status": info.get("status"),
                      "detail": info.get("detail"), "read": len(found), "last_run": now.isoformat(timespec="seconds")})
        if info.get("status") == "ok":
            entry["last_ok"] = entry["last_run"]
    for src_id, entry in sources.items():
        entry["count"] = sum(1 for it in items if it["src"] == src_id)

    for src_id, (found, info) in results.items():
        extra = f" · {info['pages']} páginas" if info.get("pages") else ""
        print(f"[{SOURCES[src_id].NAME}] {info.get('status')} · {len(found)} leídos{extra} · "
              f"{sources[src_id]['count']} en total")
    print(f"Total: {len(items)} motos · {sum(1 for it in items if 'mkt' in it)} con precio de mercado · "
          f"{dups} anunciadas en más de una web")

    if args.dry_run:
        return
    LISTINGS.parent.mkdir(parents=True, exist_ok=True)
    out = {"updated": now.isoformat(timespec="seconds"), "sources": sources, "items": items}
    LISTINGS.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
