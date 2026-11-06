"""Construye data/albabike_seed.json a partir de:
  - data/albabike_raw.json  (lo que leyó scraper/albabike_scrape.cjs: {cat: [items]})
  - data/albabike_curated.json  (los cascos emparejados a mano con Máximo Moto, se conservan)

Parsea marca/modelo/precio de cada producto de Albabike y arma el seed que consume
scraper.equip. Los curados mandan (se mantienen con su `mid` emparejado); el resto son
productos propios de Albabike (su `mid` es slug(marca)-slug(modelo)-categoria).

    python -m scraper.albabike_build
"""
import json
import re
import html as H
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "albabike_raw.json"
CURATED = ROOT / "data" / "albabike_curated.json"
OUT = ROOT / "data" / "albabike_seed.json"

BRANDS = ["seventy degrees", "mt helmets", "by city", "gas gas", "v quattro", "on board", "tucano urbano",
          "rst pro series", "alpinestars", "acerbis", "rev'it", "revit", "racer", "airoh", "arai", "shoei",
          "shark", "scorpion", "nolan", "givi", "kappa", "leatt", "dainese", "sidi", "forma", "gaerne",
          "falco", "bering", "furygan", "macna", "ixon", "rukka", "spidi", "held", "richa", "klim", "nankai",
          "oxford", "hebo", "thor", "caberg", "bell", "nzi", "hjc", "stylmartin", "rainers", "garibaldi",
          "unik", "five", "shot", "fox", "oneal", "o'neal", "tcx", "broger", "ozone", "shima", "moore",
          "noend", "no end", "origine", "cgm", "wunderlich", "tucano", "vquattro", "suomy", "schuberth",
          "kyt", "smk", "eleveit", "booster", "ls2", "mt", "rst", "sd", "t.ur"]
STRIP = re.compile(r'^(cascos?|chaquetas?|guantes?|pantal[oó]n(?:es)?|botas?|zapatillas?|monos?|'
                   r'vaquero|vaqueros?|hombre|mujer|ni[nñ]o|ni[nñ]a|unisex|infantil|junior|kid|lady|'
                   r'de\s+moto)\s+', re.I)
MKFIX = {"ls2": "LS2", "mt": "MT", "mt helmets": "MT Helmets", "hjc": "HJC", "rev'it": "Rev'it",
         "revit": "Rev'it", "tcx": "TCX", "nzi": "NZI", "rst": "RST", "cgm": "CGM", "oneal": "O'Neal",
         "o'neal": "O'Neal", "by city": "By City", "v quattro": "V Quattro", "vquattro": "V Quattro",
         "gas gas": "Gas Gas", "sd": "Seventy Degrees", "t.ur": "Tucano Urbano",
         "tucano urbano": "Tucano Urbano", "tucano": "Tucano Urbano", "noend": "NoEnd", "no end": "NoEnd"}


def slug(s):
    s = H.unescape(s).lower()
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', s)).strip('-')


def disp(s):
    return " ".join(w if (any(c.isdigit() for c in w) or len(w) <= 3 or w.isupper())
                    else w.capitalize() for w in s.split())


def clean_title(t):
    t = re.sub(r'\s+', ' ', H.unescape(t or '')).strip()
    return re.sub(r'\s*\([^)]*\)\s*$', '', t)


def parse(title):
    body = clean_title(title)
    while STRIP.match(body):
        body = STRIP.sub('', body)
    low = body.lower()
    brand, pos = None, None
    for b in BRANDS:
        m = re.search(r'(?:^|\s)' + re.escape(b) + r'(?:\s|$)', low)
        if m and (pos is None or m.start() < pos):
            pos, brand = m.start(), b
    if brand is None:
        parts = body.split()
        mk = parts[0] if parts else "Albabike"
        return (mk.upper() if not any(c.isdigit() for c in mk) else "Albabike"), disp(" ".join(parts[1:]) or body)
    m = re.search(r'(?:^|\s)' + re.escape(brand) + r'(?:\s|$)', body, re.I)
    model = body[m.end():].strip(" -·,") if m else ""
    mk = MKFIX.get(brand, " ".join(w.capitalize() for w in brand.split()))
    return mk, (disp(model) or mk)


def price(s):
    s = (s or '').replace('€', '').replace('.', '').replace(',', '.').strip()
    m = re.search(r'\d+(?:\.\d+)?', s)
    try:
        v = float(m.group()) if m else 0
        return int(round(v)) if v > 0 else None
    except Exception:
        return None


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    curated = json.loads(CURATED.read_text(encoding="utf-8")) if CURATED.exists() else []
    old_ids = {it["id"] for it in curated}
    new, seen = [], set(old_ids)
    for cat, items in raw.items():
        for it in items:
            pid = it["href"].rsplit("/", 1)[-1].replace(".html", "")
            _id = f"albabike:{pid}"
            if _id in seen:
                continue
            p = price(it.get("newp"))
            if not p:
                continue
            p0 = price(it.get("oldp"))
            mk, md = parse(it.get("title") or "")
            if not md or len(md) < 2:
                continue
            seen.add(_id)
            new.append({"id": _id, "src": "albabike",
                        "url": "https://albabike.com" + it["href"] if it["href"].startswith("/") else it["href"],
                        "t": f"{mk} {md}".strip(), "mk": mk, "md": md, "cat": cat,
                        "p": p, "p0": p0 if (p0 and p0 > p) else None, "img": it.get("img"),
                        "mid": f"{slug(mk)}-{slug(md)}-{cat}"})
    merged = curated + new
    OUT.write_text(json.dumps(merged, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(f"albabike_seed.json: {len(merged)} ({len(curated)} curados + {len(new)} nuevos) · "
          f"{dict(Counter(x['cat'] for x in merged))}")


if __name__ == "__main__":
    main()
