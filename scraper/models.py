"""Agrupación por marca + modelo + año, color e histórico de precios.

Cada web llama al mismo modelo de forma distinta ("Mt 07" / "MT-07 ABS", "Tiger 900" /
"TIGER 900 RALLY PRO"). La referencia es el catálogo de modelos base de motos.net, que se
guarda en data/models.json para seguir usándolo aunque motos.net deje de leerse:
el modelo de un concesionario va al modelo base más largo del catálogo por el que empiece.
"""
import re
import statistics

from .common import fold

# Palabras que no cambian el modelo: equipamiento, carnet, garantía, adornos de anuncio.
NOISE = {"abs", "a2", "a1", "apta", "aptab", "limitable", "limitada", "limitado", "garantia", "oficial", "y", "b",
         "nueva", "nuevo", "km0", "tcs", "quickshifter", "full", "pack", "edition", "edicion", "special"}

COLORS = [
    ("Negro", r"negr[oa]s?|black|nero|schwarz|dark|oscur[oa]|mate"),
    ("Blanco", r"blanc[oa]s?|white|bianco|perla|pearl"),
    ("Rojo", r"roj[oa]s?|red\b|rosso|granate"),
    ("Azul", r"azul|blue|blu\b|navy"),
    ("Gris", r"gris|grey|gray|grigio|antracita|plat[ae]ad[oa]|silver|plata"),
    ("Verde", r"verde|green|lime"),
    ("Amarillo", r"amarill[oa]|yellow|giallo"),
    ("Naranja", r"naranja|orange|arancio"),
]
COLORS = [(name, re.compile(rf"\b(?:{pattern})", re.I)) for name, pattern in COLORS]

HISTORY_DAYS = 400  # puntos diarios que se guardan por grupo


def color(*texts):
    """Color a partir del dato de la web o del título ('Triple Black' → Negro). None si no lo dice."""
    for text in texts:
        for name, pattern in COLORS:
            if text and pattern.search(text):
                return name
    return None


def base_key(model):
    words = [w for w in re.split(r"[^a-z0-9]+", fold(model)) if w and w not in NOISE]
    return "".join(words)


def pretty(model):
    """'Mt 07' → 'MT 07', 'Crf1000l africa twin' → 'CRF1000L Africa Twin', 'r 1250 gs' → 'R 1250 GS'."""
    words = [w for w in re.split(r"\s+", (model or "").strip()) if w and fold(w) not in NOISE]
    out = []
    for w in words:
        if any(c.isdigit() for c in w) or len(w) <= 3:
            out.append(w.upper())
        else:
            out.append(w[:1].upper() + w[1:].lower())
    return " ".join(out)


def _fits(longer, shorter):
    """¿El modelo base `shorter` vale para `longer`? 'tiger900rallypro' → 'tiger900' sí; 'rc390' → 'rc' no."""
    if len(shorter) < 2 or not longer.startswith(shorter):
        return False
    digit = lambda k: any(c.isdigit() for c in k)
    return digit(shorter) or not digit(longer)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", fold(text)).strip("-")


def _generic(k):
    """Modelo que en realidad es una familia: solo número ('890', '125') o sigla corta ('rc')."""
    return k.isdigit() or (k.isalpha() and len(k) <= 3)


def model_name(it):
    """Modelo del anuncio. Si es genérico, se completa con la palabra siguiente del título:
    md '890' + 'KTM 890 Duke' → '890 Duke'; md 'RC' + 'KTM RC 390' → 'RC 390'."""
    md = it.get("md") or ""
    if not _generic(base_key(md)):
        return md
    words = re.split(r"\s+", fold(it.get("t")))
    mine = re.split(r"\s+", fold(md))
    for i in range(len(words) - len(mine)):
        if words[i:i + len(mine)] == mine:
            nxt = re.sub(r"[^a-z0-9-]", "", words[i + len(mine)])
            if nxt and fold(nxt) not in NOISE and not re.fullmatch(r"(19|20)\d\d", nxt):
                original = (it.get("t") or "").split()
                return f"{md} {original[i + len(mine)] if i + len(mine) < len(original) else nxt}"
            break
    return md


def assign(items, catalog, reference="motosnet"):
    """Pone a cada anuncio `mid` (id del grupo: marca-modelo-año) y `mn` (nombre del modelo).

    catalog: {marca: {clave_modelo: nombre}}; se amplía con los modelos base de `reference`.
    """
    for it in items:
        if it.get("src") == reference and it.get("mk") and it.get("md"):
            md = model_name(it)
            k = base_key(md)
            if k and not _generic(k):
                catalog.setdefault(it["mk"], {}).setdefault(k, pretty(md))
    for it in items:
        it.pop("mid", None)
        it.pop("mn", None)
        if not (it.get("mk") and it.get("md") and it.get("y")):
            continue
        md = model_name(it)
        k = base_key(md)
        if not k:
            continue
        models = catalog.get(it["mk"], {})
        if k not in models:
            fits = [ck for ck in models if _fits(k, ck)]
            if fits:
                k = max(fits, key=len)
        name = models.get(k) or pretty(md)
        it["mid"] = f"{slug(it['mk'])}-{slug(name)}-{it['y']}"
        it["mn"] = name


def price_history(it, prev, today):
    """Histórico de precios del anuncio: [[fecha, precio], ...], un punto por cada cambio."""
    ph = list(prev.get("ph") or []) if prev else []
    if not ph and prev and prev.get("p"):
        ph = [[prev.get("fs", today), prev["p"]]]
    if it.get("p") and (not ph or ph[-1][1] != it["p"]):
        ph.append([today, it["p"]])
    return ph


def group_history(items, history, today):
    """Un punto diario por grupo: [fecha, más barata, mediana, nº de anuncios]."""
    groups = {}
    for it in items:
        if it.get("mid") and it.get("p"):
            groups.setdefault(it["mid"], []).append(it["p"])
    for mid, prices in groups.items():
        point = [today, min(prices), int(statistics.median(prices)), len(prices)]
        series = history.setdefault(mid, [])
        if series and series[-1][0] == today:
            series[-1] = point
        else:
            series.append(point)
        del series[:-HISTORY_DAYS]
    return history
