"""motos.net (motos.coches.net): portal de particulares y profesionales, ~35.000 motos.

Cada página de resultados trae sus 20 anuncios completos en un JSON incrustado
(`window.__INITIAL_PROPS__` → `initialResults.items`): precio, km, año, provincia,
CV, foto... No hace falta leer las tarjetas del HTML (solo pinta 8 de 20).

La paginación es `?pg=N` (con `?page=N` devuelve siempre la primera) y el orden por
defecto pone primero lo más reciente. Para no cargar la web, cada día se leen como
mucho MAX_PAGES_PER_RUN páginas:
  1. Novedades: páginas 1, 2... hasta una página sin anuncios nuevos.
  2. Si sobra cupo, barrido: sigue desde donde lo dejó el día anterior (`cursor` en
     data/state.json) para refrescar precios y ver qué anuncios siguen vivos.
Si la web responde con su página anti-bot, se para ese día sin reintentar.
"""
import json
import re
import time

from ..common import brand, clean_title, is_a2, model, moto_type, province, to_int, year
from ..fetch import is_challenge

ID = "motosnet"
NAME = "motos.net"
HOME = "https://motos.coches.net/"
BASE = "https://motos.coches.net"
SEARCH = BASE + "/segunda-mano/"
MAX_PAGES_PER_RUN = 4  # páginas al día (20 anuncios cada una)
DROP_AFTER_DAYS = 14   # a este ritmo un anuncio tarda en volver a verse: se guarda más tiempo

_PROPS = re.compile(r'window\.__INITIAL_PROPS__\s*=\s*JSON\.parse\("((?:[^"\\]|\\.)*)"\)')


def page_url(n):
    return SEARCH if n <= 1 else f"{SEARCH}?pg={n}"


def parse_page(html):
    """(anuncios en crudo, páginas totales) o None si la página no trae el JSON."""
    m = _PROPS.search(html)
    if not m:
        return None
    props = json.loads(json.loads('"' + m.group(1) + '"'))
    results = props.get("initialResults") or {}
    return results.get("items") or [], results.get("totalPages") or 0


def to_listing(raw, current_year):
    url = raw.get("url") or ""
    parts = [p for p in url.split("/") if p]  # ['ocasion', 'yamaha', 'tracer_7', 'version_...-2021-en-valencia-1021.htm']
    mk = brand(raw.get("make") or (parts[1] if len(parts) > 2 else None))
    md = model(parts[2], dashes=True) if len(parts) > 2 else None
    title = clean_title(raw.get("title") or " ".join(filter(None, [mk, md])), mk)
    hp = to_int(raw.get("hp"))
    price = to_int(raw.get("price"))
    original = to_int(raw.get("originalPrice"))
    loc = raw.get("location") or {}
    return {
        "id": f"{ID}:{raw['id']}",
        "src": ID,
        "url": BASE + url if url.startswith("/") else url,
        "t": title,
        "mk": mk,
        "md": md,
        "y": year(raw.get("year"), current_year),
        "km": to_int(raw.get("km")) if raw.get("km") is not None else None,
        "p": price,
        "p0": original if original and price and original > price else None,
        "prov": province(loc.get("mainProvince")),
        "city": loc.get("cityLiteral"),
        "img": raw.get("imgUrl") or raw.get("img"),
        "cv": hp,
        "tp": moto_type(None, f"{title} {md or ''}"),
        "a2": is_a2(title, hp),
        "pro": bool(raw.get("isProfessional")),
        "pub": (raw.get("publicationDate") or raw.get("creationDate") or "")[:10] or None,
    }


def scrape(fetcher, known, state, deadline, current_year, log):
    """Devuelve (anuncios, info). `known` son los ids que ya tenemos de esta fuente."""
    ok, robots_info = fetcher.allowed(SEARCH)
    if not ok:
        return [], {"status": "robots_disallowed", "detail": robots_info}

    found = {}
    pages_read = 0
    total_pages = state.get("total_pages") or 0

    def read(n):
        nonlocal total_pages, pages_read
        resp = fetcher.get(page_url(n))
        parsed = parse_page(resp.text) if resp.status_code == 200 and not is_challenge(resp) else None
        if parsed is None:  # sin reintentos: si la web dice que no, se para hasta mañana
            status = "challenge" if is_challenge(resp) else (
                f"http_{resp.status_code}" if resp.status_code != 200 else "sin_json")
            raise _Blocked(status, n, _describe(resp))
        items, total = parsed
        total_pages = total or total_pages
        pages_read += 1
        new = 0
        for raw in items:
            if not raw.get("id"):
                continue
            listing = to_listing(raw, current_year)
            if listing["id"] not in known and listing["id"] not in found:
                new += 1
            found[listing["id"]] = listing
        return len(items), new

    status, detail = "ok", None
    try:
        # 1) Novedades.
        n = 1
        while pages_read < MAX_PAGES_PER_RUN and time.monotonic() < deadline:
            count, new = read(n)
            n += 1  # siguiente página sin leer
            if count == 0 or (new == 0 and n > 2):
                break
        log(f"novedades: {pages_read} páginas, {len(found)} anuncios")

        # 2) Barrido desde el cursor, con el cupo que quede.
        cursor = max(state.get("cursor") or 0, n)
        while pages_read < MAX_PAGES_PER_RUN and time.monotonic() < deadline:
            if total_pages and cursor > total_pages:
                cursor = 2
                state["sweeps"] = (state.get("sweeps") or 0) + 1
                log("barrido completo, vuelta a empezar")
            count, _ = read(cursor)
            cursor = cursor + 1 if count else (total_pages or cursor) + 1
        state["cursor"] = cursor
    except _Blocked as blocked:
        status, detail = blocked.status, f"página {blocked.page}: {blocked.what}"
        log(f"⚠ {status} en la página {blocked.page}; se guarda lo leído")

    state["total_pages"] = total_pages
    return list(found.values()), {"status": status, "detail": detail, "pages": pages_read,
                                  "total_pages": total_pages, "complete": False}


def _describe(resp):
    """Qué ha devuelto la web en vez de anuncios: código, tamaño, título y principio del texto."""
    m = re.search(r"<title[^>]*>(.*?)</title>", resp.text[:20000], re.S | re.I)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)\b.*?</\1>", " ", resp.text[:20000], flags=re.S | re.I)))
    return f"HTTP {resp.status_code}, {len(resp.text)} bytes, título {(m.group(1).strip() if m else '')[:80]!r}, texto {text.strip()[:160]!r}"


class _Blocked(Exception):
    def __init__(self, status, page, what=""):
        super().__init__(status)
        self.status, self.page, self.what = status, page, what
