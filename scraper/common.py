"""Helpers compartidos: normalización de marca, modelo, tipo de moto, carnet A2 y números."""
import re
import unicodedata

# Nombre canónico de las marcas, por su clave en minúsculas y sin separadores.
BRANDS = {
    "honda": "Honda", "yamaha": "Yamaha", "suzuki": "Suzuki", "kawasaki": "Kawasaki", "bmw": "BMW",
    "ducati": "Ducati", "ktm": "KTM", "triumph": "Triumph", "harleydavidson": "Harley-Davidson",
    "aprilia": "Aprilia", "vespa": "Vespa", "piaggio": "Piaggio", "kymco": "Kymco", "sym": "SYM",
    "royalenfield": "Royal Enfield", "husqvarna": "Husqvarna", "benelli": "Benelli", "mvagusta": "MV Agusta",
    "motoguzzi": "Moto Guzzi", "indian": "Indian", "gasgas": "GasGas", "derbi": "Derbi", "rieju": "Rieju",
    "beta": "Beta", "sherco": "Sherco", "montesa": "Montesa", "bultaco": "Bultaco", "peugeot": "Peugeot",
    "daelim": "Daelim", "cfmoto": "CFMoto", "zontes": "Zontes", "voge": "Voge", "keeway": "Keeway",
    "macbor": "Macbor", "hanway": "Hanway", "mitt": "Mitt", "brixton": "Brixton", "fantic": "Fantic",
    "lambretta": "Lambretta", "scomadi": "Scomadi", "mash": "Mash", "um": "UM", "bimota": "Bimota",
    "silence": "Silence", "niu": "NIU", "zero": "Zero", "super soco": "Super Soco", "supersoco": "Super Soco",
    "qjmotor": "QJMotor", "kove": "Kove", "swm": "SWM", "tm": "TM", "can-am": "Can-Am", "canam": "Can-Am",
    "buell": "Buell", "victory": "Victory", "mutt": "Mutt", "orcal": "Orcal", "wottan": "Wottan",
}

# Pistas de texto → tipo de moto (el orden importa: la primera que casa gana).
# Borde de palabra solo al inicio: los modelos mezclan letras y dígitos (CB650F, CBR600RR).
TYPE_HINTS = [
    ("scooter", r"\b(?:scooter|maxiscooter|t-?max|x-?max|burgman|forza|pcx|sh\s?\d{2,3}|nmax|vespa|primavera|liberty"
                r"|x-?adv|c ?400|c ?650|ak ?550|downtown|agility|people|majesty|beverly|medley|mp3|tricity|integra"
                r"|vision|symphony|fiddle|tweet|miler|dink|sky ?town|dtx|delight|ray ?z|x ?10\b|scoopy|zip|typhoon"
                r"|sr ?(?:50|125|gt)|e3\b|silence|s01|s02|cityblade|super ?soco)"),
    ("turismo", r"\b(?:turismo|touring|k ?1[236]00|gtl?\b|nt ?1100|vfr|fjr|deauville|pan ?european|goldwing|gold wing"
                r"|r ?1[12][05]0 ?rt|r ?1300 ?rt|trophy|concours|ninja ?1000 ?sx|grand ?tourer)"),
    ("trail", r"\b(?:trail|adventure|gs\b|enduro|africa\s?twin|t[eé]n[eé]r[eé]|transalp|v-?strom|tiger|multistrada"
              r"|crosstourer|versys|tracer|desert\s?x|norden|nc ?7[05]0 ?x|himalayan|tr[ke] ?\d{3}|[fs] ?\d{3,4} ?xr"
              r"|v ?85|tuareg|crf ?\d+ ?(?:l|rally)|crf-?\d+-rally|nx ?\d|adv\b|dsx|atr|x-?nord|scrambler ?\d{3,4} ?xe"
              r"|xt ?\d{3}|dr ?\d{3}|klr|caponord|g ?310 ?gs)"),
    ("campo", r"\b(?:cross|motocross|trial|supermotard|hypermotard|mrt|se-?r\b|exc|crf ?\d{3}[rf]?\b|yz|kx|rmz|sx-?f)"),
    ("deportiva", r"\b(?:deportiva|sport\b|fireblade|cbr|gsx-?r|zx-?\d|panigale|rsv4|rs ?660|ninja|supersport"
                  r"|superbike|yzf|r1\b|r3\b|r6\b|r7\b|rc ?\d{3}|s ?1000 ?rr|m ?1000 ?rr)"),
    ("custom", r"\b(?:custom|cruiser|chopper|bobber|harley|sportster|softail|rebel|vulcan|diavel|caf[eé]\s?racer"
               r"|scrambler|bonneville|intruder|shadow|virago|drag\s?star|xv ?\d{3,4}|indian|imperiale|bt ?\d{3}"
               r"|cl ?500|r ?18\b|meteor|classic ?350|eliminator|v7)"),
    ("naked", r"\b(?:naked|streetfighter|hornet|mt-?\d+|z ?\d{3,}|cb ?\d+|cbf|gsx-?s|street\s?triple|speed\s?triple"
              r"|duke|monster|svartpilen|vitpilen|brutale|sv ?650|er-?[56]|fz ?\d|xsr|trident|tuono|gladius|bn ?\d"
              r"|leoncino|nkd|nc ?7[05]0 ?s|[fs] ?\d{3,4} ?r\b|r ?nine ?t|r-?ninet|r ?1250 ?r\b|cb ?\d{3} ?r|monkey|msx|grom"
              r"|300 ?r|525 ?r|125 ?r\b|sr ?\d{3}|m ?\d{3}|kymco ?k-?pipe)"),
]
TYPE_HINTS = [(kind, re.compile(pattern, re.I)) for kind, pattern in TYPE_HINTS]

# Tipos que dan las webs con su propio nombre → los nuestros.
TYPE_ALIASES = {
    "trail": "trail", "scooter": "scooter", "naked": "naked", "custom": "custom", "sport": "deportiva",
    "deportiva": "deportiva", "turismo": "turismo", "sport-turismo": "turismo", "touring": "turismo",
    "enduro": "campo", "cross": "campo", "trial": "campo", "supermotard": "campo",
}

PROVINCES = [
    "Álava", "Albacete", "Alicante", "Almería", "Asturias", "Ávila", "Badajoz", "Barcelona", "Burgos", "Cáceres",
    "Cádiz", "Cantabria", "Castellón", "Ciudad Real", "Córdoba", "A Coruña", "Cuenca", "Girona", "Granada",
    "Guadalajara", "Gipuzkoa", "Huelva", "Huesca", "Illes Balears", "Jaén", "León", "Lleida", "Lugo", "Madrid",
    "Málaga", "Murcia", "Navarra", "Ourense", "Palencia", "Las Palmas", "Pontevedra", "La Rioja", "Salamanca",
    "Santa Cruz de Tenerife", "Segovia", "Sevilla", "Soria", "Tarragona", "Teruel", "Toledo", "Valencia",
    "Valladolid", "Bizkaia", "Zamora", "Zaragoza", "Ceuta", "Melilla",
]
_PROVINCE_ALIASES = {"la coruna": "A Coruña", "coruna": "A Coruña", "baleares": "Illes Balears",
                     "islas baleares": "Illes Balears", "guipuzcoa": "Gipuzkoa", "vizcaya": "Bizkaia",
                     "alava": "Álava", "araba": "Álava", "gerona": "Girona", "lerida": "Lleida", "orense": "Ourense",
                     "tenerife": "Santa Cruz de Tenerife", "castellon de la plana": "Castellón"}


def fold(text):
    """Minúsculas y sin tildes: 'Ténéré' → 'tenere'."""
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in text if not unicodedata.combining(c)).lower().strip()


def key(text):
    """Clave compacta para comparar nombres: 'MT-07 ABS' → 'mt07abs'."""
    return re.sub(r"[^a-z0-9]", "", fold(text))


def brand(name):
    if not name:
        return None
    k = key(name)
    return BRANDS.get(k) or BRANDS.get(fold(name)) or str(name).strip().title()


def model(name, dashes=False):
    """'tracer_7' / 'f-900-r' (dashes=True, de una URL) / 'TÉNÉRÉ 700 RALLY' → texto legible."""
    if not name:
        return None
    text = re.sub(r"[-_\s]+" if dashes else r"[_\s]+", " ", str(name)).strip()
    return text.upper() if len(text) <= 4 else text[:1].upper() + text[1:]


def clean_title(title, mk):
    """Quita adornos de los títulos y pone la marca con su nombre canónico.

    'KEEWAY Zahara 125 Versión 2012 - 2024' → 'Keeway Zahara 125'
    'TRIUMPH TIGER 800 XRX ¿A2?' → 'Triumph TIGER 800 XRX A2'
    """
    text = re.sub(r"\s*Versi[oó]n\s+\d{4}(?:\s*-\s*\d{4})?\s*$", "", title or "", flags=re.I)
    text = re.sub(r"[¿?]", "", text)
    text = re.sub(r"\s+-|-\s+|^-|-$", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if mk and fold(text).startswith(fold(mk) + " "):
        text = mk + text[len(mk):]
    return text


def province(name):
    if not name:
        return None
    f = fold(name)
    for p in PROVINCES:
        if fold(p) == f:
            return p
    return _PROVINCE_ALIASES.get(f) or str(name).strip().title()


def moto_type(declared, text):
    if declared:
        found = TYPE_ALIASES.get(fold(declared))
        if found:
            return found
    for kind, pattern in TYPE_HINTS:
        if pattern.search(text or ""):
            return kind
    return None


def is_a2(title, hp=None, licence=None):
    """True si la web la anuncia apta (o limitable) para A2, o tiene 47 CV o menos (35 kW)."""
    if licence and "a2" in fold(licence):
        return True
    if re.search(r"\bA2\b", title or "", re.I):
        return True
    if hp and 0 < hp <= 47:
        return True
    return None


def to_int(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    digits = re.sub(r"\D", "", str(value))
    return int(digits) if digits else None


def year(value, current):
    y = to_int(value)
    return y if y and 1950 <= y <= current + 1 else None
