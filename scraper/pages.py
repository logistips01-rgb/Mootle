"""Páginas propias para Google: una por modelo y año (m/<mid>.html), una por marca (marca/<marca>.html),
sitemap.xml y robots.txt. Como en guitle, la ficha va escrita en el HTML (ofertas, km, enlaces, histórico)
para que Google la lea sin JavaScript, y un fichero solo se reescribe si su contenido cambia.

    python -m scraper.pages        # regenera las páginas con los datos de data/ sin leer ninguna web
"""
import html
import json
import re
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path

from .complementos_data import (ASEGURADORAS, FECHA_DATOS, FINANCIACION_EJEMPLO_MESES,
                                FINANCIACION_EJEMPLO_TIN, FINANCIERAS, SEGURO_DESDE)

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://mootle.es"  # dominio propio (antes: https://logistips01-rgb.github.io/Mootle)
MODELS_DIR = ROOT / "m"
BRANDS_DIR = ROOT / "marca"
MONTHS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
TYPES = {"naked": "naked", "trail": "trail", "scooter": "scooter", "deportiva": "deportiva", "custom": "custom",
         "turismo": "turismo", "campo": "de campo"}
WHEELS = ('<svg viewBox="0 0 92 48" aria-hidden="true"><circle cx="22" cy="26" r="16" fill="none" stroke-width="8"/>'
          '<circle cx="70" cy="26" r="16" fill="none" stroke-width="8"/><circle class="hub" cx="22" cy="26" r="3.5"/>'
          '<circle class="hub" cx="70" cy="26" r="3.5"/></svg>')
BIKE = ('<svg width="96" height="56" viewBox="0 0 96 56" fill="none" stroke="currentColor" stroke-width="3" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="20" cy="38" r="14"/>'
        '<circle cx="76" cy="38" r="14"/><path d="M20 38l16-20h18l10 20M36 18l-6-8h-8M54 18l8-6h10"/></svg>')

e = html.escape


def eur(v):
    return f"{int(v):,}".replace(",", ".") + " €"


def num(v):
    return f"{int(v):,}".replace(",", ".")


def day(iso):
    y, m, d = iso[:10].split("-")
    return f"{int(d)} {MONTHS[int(m) - 1]}"


def slug(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def safe_url(u):
    return u if re.match(r"^https?://", u or "", re.I) else "#"


def unique_bikes(offers):
    """La misma moto en varias webs (campo `g`) cuenta una vez: la más barata."""
    best = {}
    for m in offers:
        if m.get("g") and (m["g"] not in best or m["p"] < best[m["g"]]["p"]):
            best[m["g"]] = m
    return [m for m in offers if not m.get("g") or best[m["g"]] is m]


def groups_of(items):
    by = defaultdict(list)
    for m in items:
        if m.get("mid") and m.get("p"):
            by[m["mid"]].append(m)
    out = {}
    for mid, offers in by.items():
        offers.sort(key=lambda m: m["p"])
        bikes = unique_bikes(offers)
        prices = [m["p"] for m in bikes]
        best = offers[0]
        out[mid] = {
            "mid": mid, "mk": best["mk"], "mn": best["mn"], "y": best["y"], "offers": offers, "best": best,
            "tp": next((m["tp"] for m in offers if m.get("tp")), None),
            "img": best.get("img") or next((m["img"] for m in offers if m.get("img")), None),
            "n": len(bikes), "webs": sorted({m["src"] for m in offers}), "min": best["p"], "max": max(prices),
            "med": int(statistics.median(prices)),
        }
    return out


def write(path, text):
    """Escribe solo si cambia (así git no ve miles de ficheros modificados cada día)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


# ───────────────────────────── trozos comunes ─────────────────────────────

def head(title, description, canonical, image=None, ld=None, noindex=False):
    og_image = f'\n<meta property="og:image" content="{e(image)}">' if image else ""
    robots = '\n<meta name="robots" content="noindex">' if noindex else ""
    ld_tag = f'\n<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>' if ld else ""
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#e8590c">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{e(canonical)}">{robots}
<meta property="og:type" content="website">
<meta property="og:site_name" content="mootle">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">{og_image}
<link rel="icon" type="image/svg+xml" href="../icon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../mootle.css">{ld_tag}
</head>
<body>
<main>
  <div class="topbar">
    <a class="logo" aria-label="mootle, inicio" href="../"><img src="../icon.svg" alt=""><span class="stack"><span class="word">m{WHEELS}tle</span><span class="tag">motos de ocasión al mejor precio</span></span></a>
    <form class="slim" role="search" action="../" method="get">
      <input name="q" type="search" placeholder="Modelo, marca, provincia…" autocomplete="off" aria-label="Buscar moto">
      <button class="btn" type="submit">Buscar</button>
    </form>
  </div>
"""


FOOT = """  <footer><span>mootle · comparador de motos de ocasión</span><span>Los datos y las fotos son de cada web: siempre enlazamos al anuncio original.</span></footer>
</main>
</body>
</html>
"""


def elsewhere(query, intro):
    from urllib.parse import quote
    q = quote(query)
    return (f'<div class="elsewhere"><p>{intro}</p>'
            f'<a class="ext" href="https://es.wallapop.com/search?keywords={q}&amp;category_id=14000" target="_blank" rel="noopener noreferrer">Buscar en Wallapop ↗</a>'
            f'<a class="ext" href="https://www.milanuncios.com/motos-de-segunda-mano/?s={q}" target="_blank" rel="noopener noreferrer">Buscar en Milanuncios ↗</a></div>')


# ───────────────────────────── complementos (monetización) ─────────────────────────────
# Todo lo "monetizable" (seguro, equipación, neumáticos, financiación) sale de aquí.
# AMAZON_TAG: ID de afiliado de Amazon para mootle (p. ej. "mootle-21"). Se cambia SOLO aquí
# y lo cogen todas las fichas. Una tarjeta con url=None sale como "Muy pronto" (programa sin dar de alta).
AMAZON_TAG = "TU-TAG"

_COMP_ICONS = {
    "seguro": '<path d="M12 3l7 2.5V11c0 4.2-2.9 7.4-7 8.8C7.9 18.4 5 15.2 5 11V5.5z"/>',
    "equip": '<path d="M4 14a8 8 0 1116 0v2H4z"/><path d="M4 16h11"/>',
    "ruedas": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="3"/>',
    "financ": '<circle cx="12" cy="12" r="8.5"/><path d="M15 9.5a3.5 3.5 0 100 5M8 11.5h5M8 13h4.5"/>',
}


def _amazon(query):
    from urllib.parse import quote
    return f"https://www.amazon.es/s?k={quote(query)}&amp;tag={AMAZON_TAG}"


def financiacion_cuota(precio):
    """Cuota mensual de ejemplo, para el 'desde X €/mes' de la ficha."""
    if not precio:
        return None
    i = FINANCIACION_EJEMPLO_TIN / 100 / 12
    n = FINANCIACION_EJEMPLO_MESES
    return int(round(precio * i / (1 - (1 + i) ** -n)))


def complementos(name, precio=None):
    nm = e(name)
    cuota = financiacion_cuota(precio)
    fin_desc = (f'Desde ~{num(cuota)} €/mes <small>(ejemplo {FINANCIACION_EJEMPLO_MESES} meses)</small>'
                if cuota else "Financia tu moto a plazos")
    # (clave, título, desc-html, url, ¿enlace externo de afiliado?)
    cards = [
        ("seguro", "Seguro de moto", f'Compara aseguradoras · desde {e(SEGURO_DESDE)} <small>(orientativo)</small>', "../seguros/", False),
        ("equip", "Equipación", "Casco, guantes y chaqueta", _amazon("equipacion moto casco"), True),
        ("ruedas", "Neumáticos", f"Ruedas para tu {nm}", _amazon(f"neumatico moto {name}"), True),
        ("financ", "Financiación", fin_desc, "../financiacion/", False),
    ]
    out = []
    for key, title, desc, url, ext in cards:
        ic = f'<span class="comp-ic"><svg viewBox="0 0 24 24" aria-hidden="true">{_COMP_ICONS[key]}</svg></span>'
        cta = (f'<a class="ext" href="{url}" target="_blank" rel="sponsored nofollow noopener noreferrer">Ver ↗</a>'
               if ext else f'<a class="ext" href="{url}">Comparar →</a>')
        out.append(f'<div class="comp">{ic}<span class="comp-t">{e(title)}</span>'
                   f'<span class="comp-d">{desc}</span>{cta}</div>')
    return (f'<div class="panel"><h2 class="display">Complementos para tu {nm}</h2>'
            f'<p class="muted" style="margin:0 0 14px">Lo que necesitas al comprar la moto: seguro, equipación y neumáticos.</p>'
            f'<div class="complementos">{"".join(out)}</div>'
            f'<p class="aff-note">Seguros y financiación: datos orientativos. Equipación y neumáticos: enlaces de afiliados (si compras, mootle puede llevarse una pequeña comisión, sin coste para ti).</p></div>')


# ───────────────────────────── páginas de seguros y financiación ─────────────────────────────

def _fuente_badge(f):
    return f'<span class="fbadge {"ok" if f.startswith("oficial") else "soft"}">{e(f)}</span>'


def _comp_table(headers, rows):
    th = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablebox"><table class="ctable"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def seguros_page():
    title = f"Seguro de moto barato: compara aseguradoras (desde {SEGURO_DESDE}) · mootle"
    desc = ("Compara el precio de partida de las aseguradoras de moto en España: Mapfre, Qualitas, "
            "AMV, Verti, Línea Directa y más. Datos orientativos, no es una cotización.")
    rows = [[f'<strong>{e(a["nombre"])}</strong>', f'{e(a["desde"])} {_fuente_badge(a["fuente"])}',
             e(a["cobertura"]), e(a["nota"]),
             f'<a class="ext" href="{e(a["url"])}" target="_blank" rel="nofollow noopener noreferrer">Ver ↗</a>']
            for a in ASEGURADORAS]
    body = f"""  <nav class="crumbs" aria-label="Migas"><a href="../">Inicio</a> › Seguro de moto</nav>
  <h1 class="display" style="font-size:clamp(28px,4vw,40px);margin:8px 0 6px">Seguro de moto: compara aseguradoras</h1>
  <p class="sub" style="color:var(--text-secondary);max-width:70ch">El precio depende de tu moto, tu perfil y tu provincia, así que estos son <strong>precios de partida orientativos</strong>, no una cotización. Pide presupuesto en la que te interese.</p>
  <div class="panel">
    <h2 class="display">Aseguradoras de moto</h2>
    {_comp_table(["Aseguradora", "Desde", "Coberturas", "Notas", ""], rows)}
    <p class="aff-note">Datos orientativos recopilados el {FECHA_DATOS} de fuentes públicas (<span class="fbadge ok">oficial</span> = web de la aseguradora · <span class="fbadge soft">comparador</span> = agregadores, a verificar). No constituyen oferta ni cotización.</p>
  </div>
"""
    return head(title, desc, f"{SITE}/seguros/") + body + FOOT


def financieras_page():
    tin = str(FINANCIACION_EJEMPLO_TIN).replace(".", ",")
    title = "Financiar una moto de ocasión: compara financieras y cuotas · mootle"
    desc = ("Compara financieras para comprar tu moto de ocasión: Cofidis, Younited, N26, Cetelem y "
            "CaixaBank. TIN/TAE orientativos y cuota de ejemplo por moto.")
    rows = [[f'<strong>{e(f["nombre"])}</strong>', f'{e(f["tae"])} {_fuente_badge(f["fuente"])}',
             e(f["plazo"]), e(f["importe"]), e(f["nota"]),
             f'<a class="ext" href="{e(f["url"])}" target="_blank" rel="nofollow noopener noreferrer">Ver ↗</a>']
            for f in FINANCIERAS]
    body = f"""  <nav class="crumbs" aria-label="Migas"><a href="../">Inicio</a> › Financiación</nav>
  <h1 class="display" style="font-size:clamp(28px,4vw,40px);margin:8px 0 6px">Financiar tu moto de ocasión</h1>
  <p class="sub" style="color:var(--text-secondary);max-width:70ch">En cada ficha de moto verás la <strong>cuota de ejemplo</strong> ({FINANCIACION_EJEMPLO_MESES} meses, TIN {tin}%). Aquí comparas las financieras; los tipos son <strong>orientativos</strong> y están sujetos a aprobación.</p>
  <div class="panel">
    <h2 class="display">Financieras para moto</h2>
    {_comp_table(["Entidad", "TAE desde", "Plazo", "Importe", "Notas", ""], rows)}
    <p class="aff-note">Datos orientativos recopilados el {FECHA_DATOS} de fuentes públicas (<span class="fbadge ok">oficial</span> = web de la entidad · <span class="fbadge soft">comparador</span> = agregadores, a verificar). No constituyen oferta ni cotización. Las promociones al 0% suelen ser solo para moto nueva en concesionario.</p>
  </div>
"""
    return head(title, desc, f"{SITE}/financiacion/") + body + FOOT


def chart(series):
    if not series or len(series) < 2:
        since = day(series[0][0]) if series else "hoy"
        return f'<p class="muted">Empezamos a guardar el precio de este modelo el {since}. La gráfica se irá llenando cada día.</p>'
    W, H, L, R, T, B = 800, 220, 64, 12, 12, 28
    xs = [date.fromisoformat(p[0]).toordinal() for p in series]
    ys = [v for p in series for v in (p[1], p[2])]
    x0, x1, lo, hi = min(xs), max(xs), min(ys) * 0.95, max(ys) * 1.05
    X = lambda t: L + (W - L - R) * (0.5 if x1 == x0 else (t - x0) / (x1 - x0))
    Y = lambda v: T + (H - T - B) * (1 - (v - lo) / ((hi - lo) or 1))
    path = lambda k: "".join(f"{'L' if i else 'M'}{X(xs[i]):.1f},{Y(p[k]):.1f}" for i, p in enumerate(series))
    ticks = "".join(f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--grid)"/>'
                    f'<text x="{L - 8}" y="{Y(v) + 4:.1f}" text-anchor="end">{eur(round(v / 50) * 50)}</text>'
                    for v in (lo, (lo + hi) / 2, hi))
    dates = "".join(f'<text x="{X(xs[i]):.1f}" y="{H - 6}" text-anchor="{"end" if i else "start"}">{day(series[i][0])}</text>'
                    for i in (0, len(series) - 1))
    return (f'<svg class="chart" viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" '
            f'aria-label="Histórico de precios: la más barata y la mediana de cada día">{ticks}{dates}'
            f'<path d="{path(2)}" fill="none" stroke="var(--line-med)" stroke-width="2" stroke-dasharray="5 4" vector-effect="non-scaling-stroke"/>'
            f'<path d="{path(1)}" fill="none" stroke="var(--line-min)" stroke-width="3" vector-effect="non-scaling-stroke"/></svg>'
            '<div class="legend"><span><i style="background:var(--line-min)"></i>La más barata</span>'
            '<span><i style="background:var(--line-med)"></i>Precio mediano</span></div>')


SORT_SCRIPT = """<script>
  // Ordenar las ofertas: más barata, más cara o menos km (las filas ya vienen en el HTML).
  document.querySelector(".sortbar").addEventListener("click", e => {
    const b = e.target.closest("[data-fsort]"); if (!b) return;
    const box = document.querySelector(".offers"), rows = [...box.querySelectorAll(".offer[data-p]")];
    const k = b.dataset.fsort, by = { asc: (x, y) => x.dataset.p - y.dataset.p, desc: (x, y) => y.dataset.p - x.dataset.p, km: (x, y) => x.dataset.km - y.dataset.km };
    rows.sort(by[k]).forEach(r => { r.classList.remove("first"); box.appendChild(r); });
    if (k === "asc") rows[0].classList.add("first");
    document.querySelectorAll("[data-fsort]").forEach(x => x.classList.toggle("on", x === b));
  });
</script>
"""


# ───────────────────────────── ficha de modelo y año ─────────────────────────────

def offer_row(m, g, sources, first):
    ph = m.get("ph") or []
    diff = m["p"] - (ph[0][1] if ph else m["p"])
    trend = (f'<small class="{"up" if diff > 0 else ""}">{"Bajó" if diff < 0 else "Subió"} {eur(abs(diff))}</small>'
             if len(ph) > 1 and diff else "")
    also = [sources.get(x["src"], {}).get("name", x["src"]) for x in g["offers"] if m.get("g") and x.get("g") == m["g"] and x is not m]
    where = ", ".join(dict.fromkeys(v for v in (m.get("city"), m.get("prov")) if v)) or "—"
    km = f'{num(m["km"])} km' if m.get("km") is not None else "—"
    seller = "particular" if m.get("pro") is False else "profesional"
    return (f'<div class="offer{" first" if first else ""}" data-p="{m["p"]}" data-km="{m.get("km") if m.get("km") is not None else 10**9}">'
            f'<span class="p">{eur(m["p"])}{trend}</span>'
            f'<span><span class="lbl">Km</span>{km}</span>'
            f'<span><span class="lbl">Color</span>{e(m.get("col") or "—")}</span>'
            f'<span class="v">{e(m["t"])}{" · <strong>reservada</strong>" if m.get("res") else ""}'
            f'{"<em>Misma moto que en " + e(", ".join(also)) + "</em>" if also else ""}</span>'
            f'<span><span class="lbl">Dónde</span>{e(where)}</span>'
            f'<span class="w">{e(sources.get(m["src"], {}).get("name", m["src"]))}<span class="muted" style="font-weight:400"> · {seller}</span></span>'
            f'<a class="go" href="{e(safe_url(m.get("url")))}" target="_blank" rel="noopener noreferrer nofollow">Ver anuncio ↗</a></div>')


def model_page(g, sources, history, years):
    name = f'{g["mk"]} {g["mn"]}'
    full = f'{name} {g["y"]}'
    web_names = [sources.get(s, {}).get("name", s) for s in g["webs"]]
    best = g["best"]
    best_km = f' con {num(best["km"])} km' if best.get("km") is not None else ""
    title = f"{full} de segunda mano: desde {eur(g['min'])} · mootle"
    desc = (f"{g['n']} {'moto' if g['n'] == 1 else 'motos'} {full} de ocasión en {', '.join(web_names)}: "
            f"desde {eur(g['min'])}{best_km}" + (f" hasta {eur(g['max'])}" if g["n"] > 1 else "") +
            ". Compara precios, km y su histórico de precios.")
    canonical = f"{SITE}/m/{g['mid']}.html"
    ld = {"@context": "https://schema.org", "@type": "Product", "name": full, "brand": {"@type": "Brand", "name": g["mk"]},
          "model": g["mn"], "productionDate": str(g["y"]), "category": "Motos de segunda mano",
          "offers": {"@type": "AggregateOffer", "priceCurrency": "EUR", "lowPrice": g["min"], "highPrice": g["max"],
                     "offerCount": len(g["offers"]), "itemCondition": "https://schema.org/UsedCondition",
                     "availability": "https://schema.org/InStock"}}
    if g["img"]:
        ld["image"] = g["img"]
    save = f'Ahorras {eur(g["max"] - g["min"])} frente a la más cara.' if g["n"] > 1 else ""
    kpis = (f'<div class="kpi best"><span>La más barata</span><b>{eur(g["min"])}</b><small>'
            f'{num(best["km"]) + " km · " if best.get("km") is not None else ""}{e(sources.get(best["src"], {}).get("name", best["src"]))}</small></div>')
    if g["n"] > 1:
        kpis += (f'<div class="kpi"><span>Precio mediano</span><b>{eur(g["med"])}</b></div>'
                 f'<div class="kpi"><span>La más cara</span><b>{eur(g["max"])}</b></div>')
    rows = "".join(offer_row(m, g, sources, i == 0) for i, m in enumerate(g["offers"]))
    other_years = "".join(f'<a class="pill{" on" if y == g["y"] else ""}" href="{mid}.html">{y}</a>' for y, mid in years)
    tp = f' · {TYPES.get(g["tp"], g["tp"])}' if g.get("tp") else ""
    img = f'<img src="{e(g["img"])}" alt="{e(full)}" referrerpolicy="no-referrer">' if g["img"] else BIKE
    body = f"""  <nav class="crumbs" aria-label="Migas"><a href="../">Inicio</a> › <a href="../marca/{slug(g['mk'])}.html">{e(g['mk'])}</a> › {e(full)}</nav>
  <div class="ficha-head">
    <div class="photo">{img}</div>
    <div>
      <span class="kicker">{e(g['mk'])}{e(tp)}</span>
      <h1 class="display">{e(name)} <span class="muted">{g['y']}</span></h1>
      <p class="sub">{num(g['n'])} {'moto a la venta' if g['n'] == 1 else 'motos a la venta'}{f" en {len(g['webs'])} webs" if len(g['webs']) > 1 else ""}. {save}</p>
      <div class="kpis">{kpis}</div>
      <p style="margin-top:16px"><a class="btn" href="{e(safe_url(best.get('url')))}" target="_blank" rel="noopener noreferrer nofollow">Ver la más barata ↗</a></p>
    </div>
  </div>
  <div class="panel">
    <h2 class="display">Todas las ofertas de la {e(full)}</h2>
    <div class="sortbar" role="group" aria-label="Ordenar ofertas">
      <button class="pill on" data-fsort="asc">Más barata primero</button>
      <button class="pill" data-fsort="desc">Más cara primero</button>
      <button class="pill" data-fsort="km">Menos km</button>
    </div>
    <div class="offers">
      <div class="offer head"><span>Precio</span><span>Km</span><span>Color</span><span>Versión</span><span>Dónde</span><span>Web</span><span></span></div>
      {rows}
    </div>
  </div>
  {elsewhere(name, f"<b>¿Y de particular?</b> Mira también la {e(name)} en Wallapop y Milanuncios (comprueba allí el año).")}
  <div class="panel">
    <h2 class="display">Histórico de precios</h2>
    <p class="muted" style="margin:0">La más barata y el precio mediano de la {e(full)}, día a día.</p>
    {chart(history.get(g['mid']))}
  </div>
  {complementos(name, g["min"])}
  {f'<div class="panel"><h2 class="display">Otros años de la {e(name)}</h2><div class="sortbar">{other_years}</div></div>' if len(years) > 1 else ""}
"""
    return head(title, desc, canonical, g["img"], ld) + body + SORT_SCRIPT + FOOT


def gone_page(mid, history):
    """Modelo y año que ya no tiene motos a la venta: se queda la página (sin indexar) con su histórico."""
    title = "Este modelo ya no tiene motos a la venta · mootle"
    body = f"""  <div class="panel">
    <h1 class="display">Ahora no hay motos a la venta de este modelo y año</h1>
    <p>Lo vigilamos cada día: vuelve a mirar más adelante o <a href="../">busca otro modelo</a>.</p>
    {chart(history.get(mid))}
  </div>
"""
    return head(title, title, f"{SITE}/m/{mid}.html", noindex=True) + body + FOOT


# ───────────────────────────── página de marca ─────────────────────────────

def card(g, prefix):
    km = f'con {num(g["best"]["km"])} km' if g["best"].get("km") is not None else ""
    foot = " · ".join(x for x in (f'{g["n"]} {"moto" if g["n"] == 1 else "motos"}', f'{len(g["webs"])} webs' if len(g["webs"]) > 1 else "",
                                   f'hasta {eur(g["max"])}' if g["n"] > 1 else "") if x)
    img = f'<img src="{e(g["img"])}" alt="" loading="lazy" referrerpolicy="no-referrer">' if g["img"] else BIKE
    return (f'<a class="card" href="{prefix}{g["mid"]}.html"><div class="photo">{img}</div><div class="body">'
            f'<span class="brand">{e(g["mk"])}{" · " + e(g["tp"]) if g.get("tp") else ""}</span>'
            f'<span class="name">{e(g["mn"])} <span>· {g["y"]}</span></span>'
            f'<span class="from">{"La más barata" if g["n"] > 1 else "Precio"}</span>'
            f'<span class="price"><strong>{eur(g["min"])}</strong><small>{km}</small></span>'
            f'<span class="foot">{foot}</span></div></a>')


def brand_page(mk, groups):
    by_model = defaultdict(list)
    for g in groups:
        by_model[g["mn"]].append(g)
    bikes = sum(g["n"] for g in groups)
    cheapest = min(g["min"] for g in groups)
    title = f"Motos {mk} de segunda mano: {num(bikes)} a la venta desde {eur(cheapest)} · mootle"
    desc = (f"{num(bikes)} motos {mk} de ocasión en {len(by_model)} modelos, desde {eur(cheapest)}. "
            "Compara por modelo y año la más barata de todas las webs y su histórico de precios.")
    sections = []
    for mn, gs in sorted(by_model.items(), key=lambda kv: -sum(g["n"] for g in kv[1])):
        gs.sort(key=lambda g: -g["y"])
        sections.append(f'<section><div class="sec-head"><h2 class="display">{e(mk)} {e(mn)}</h2></div>'
                        f'<div class="grid">{"".join(card(g, "../m/") for g in gs)}</div></section>')
    body = f"""  <nav class="crumbs" aria-label="Migas"><a href="../">Inicio</a> › {e(mk)}</nav>
  <h1 class="display" style="font-size:clamp(30px,4vw,44px);margin:8px 0 4px">Motos {e(mk)} de segunda mano</h1>
  <p class="sub" style="color:var(--text-secondary)">{num(bikes)} motos en {len(by_model)} modelos, desde {eur(cheapest)}. Toca un modelo y año para ver todas sus ofertas.</p>
  {"".join(sections)}
"""
    return head(title, desc, f"{SITE}/marca/{slug(mk)}.html") + body + FOOT


def brands_index(by_brand):
    rows = sorted(by_brand.items(), key=lambda kv: -sum(g["n"] for g in kv[1]))
    total = sum(g["n"] for gs in by_brand.values() for g in gs)
    links = "".join(f'<a class="source" href="{slug(mk)}.html"><span>{e(mk)}<small>{len({g["mn"] for g in gs})} modelos · desde {eur(min(g["min"] for g in gs))}</small></span>'
                    f'<b>{num(sum(g["n"] for g in gs))}</b></a>' for mk, gs in rows)
    title = "Motos de segunda mano por marca · mootle"
    desc = f"{num(total)} motos de ocasión de {len(by_brand)} marcas. Elige marca y compara cada modelo y año en todas las webs."
    body = f"""  <nav class="crumbs" aria-label="Migas"><a href="../">Inicio</a> › Marcas</nav>
  <h1 class="display" style="font-size:clamp(30px,4vw,44px);margin:8px 0 18px">Motos de segunda mano por marca</h1>
  <div class="sources">{links}</div>
"""
    return head(title, desc, f"{SITE}/marca/") + body + FOOT


# ───────────────────────────── todo junto ─────────────────────────────

def build(listings, history):
    sources, items = listings.get("sources", {}), listings.get("items", [])
    groups = groups_of(items)
    years = defaultdict(list)
    for g in groups.values():
        years[(g["mk"], g["mn"])].append((g["y"], g["mid"]))
    changed = 0
    for g in groups.values():
        changed += write(MODELS_DIR / f'{g["mid"]}.html', model_page(g, sources, history, sorted(years[(g["mk"], g["mn"])])))
    for old in MODELS_DIR.glob("*.html"):
        if old.stem not in groups:
            changed += write(old, gone_page(old.stem, history))
    by_brand = defaultdict(list)
    for g in groups.values():
        by_brand[g["mk"]].append(g)
    for mk, gs in by_brand.items():
        changed += write(BRANDS_DIR / f"{slug(mk)}.html", brand_page(mk, gs))
    changed += write(BRANDS_DIR / "index.html", brands_index(by_brand))
    changed += write(ROOT / "seguros" / "index.html", seguros_page())
    changed += write(ROOT / "financiacion" / "index.html", financieras_page())
    urls = [f"{SITE}/", f"{SITE}/marca/", f"{SITE}/seguros/", f"{SITE}/financiacion/"] + \
           [f"{SITE}/marca/{slug(mk)}.html" for mk in sorted(by_brand)] + \
           [f"{SITE}/m/{mid}.html" for mid in sorted(groups)]
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
               "".join(f"  <url><loc>{e(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    write(ROOT / "sitemap.xml", sitemap)
    write(ROOT / "robots.txt", f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n")
    return len(groups), len(by_brand), changed


def main():
    listings = json.loads((ROOT / "data" / "listings.json").read_text(encoding="utf-8"))
    history = json.loads((ROOT / "data" / "history.json").read_text(encoding="utf-8"))
    models, brands, changed = build(listings, history)
    print(f"Páginas: {models} modelos y años · {brands} marcas · {changed} ficheros nuevos o cambiados")


if __name__ == "__main__":
    main()
