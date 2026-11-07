"""Publicación diaria de Instagram para @mootle_es.

Elige el contenido del día (según el día de la semana, o --kind), lo genera como
imagen 1080x1080 con la marca mootle a partir de datos reales, sube la imagen al
repo (se sirve en raw.githubusercontent) y la publica con su texto.

  Lun/Mié/Vie -> comparativa de equipación (varias tiendas)
  Mar/Jue     -> chollo del día (moto o equipación que ha bajado)
  Sáb/Dom     -> post de marca / notoriedad

Uso:
  python -m scraper.social_daily                 # elige por el día de hoy y publica
  python -m scraper.social_daily --kind comparativa
  python -m scraper.social_daily --dry           # genera la imagen, no publica ni commitea
"""
import argparse
import json
import subprocess
import time
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

from .equip import CAT_NAMES

ROOT = Path(__file__).resolve().parent.parent
LISTINGS = ROOT / "data" / "listings.json"
EQUIP = ROOT / "data" / "equipacion.json"
STATE = ROOT / "data" / "social_state.json"
OUTDIR = ROOT / "marketing" / "instagram" / "daily"
RAW = "https://raw.githubusercontent.com/logistips01-rgb/Mootle/main/marketing/instagram/daily/"

TAGS_MOTO = "#motos #motosdeocasion #segundamano #motos2manos #moteros #chollo #mootle"
TAGS_EQUIP = "#equipacionmoto #cascos #guantesmoto #chaquetamoto #moteros #comparador #mootle"

MARCA = [
    {"badge": "mootle", "title": "La misma moto está en 10 webs\ny a precios distintos.",
     "sub": "mootle las junta todas y te enseña la más barata.", "cta": "Gratis en mootle.es",
     "cap": "¿Buscando moto de ocasión? La misma moto está en decenas de webs y a precios distintos. "
            "mootle las junta todas y te enseña la más barata de un vistazo, con histórico de precios. "
            "Gratis y sin registro 👉 mootle.es\n\n" + TAGS_MOTO},
    {"badge": "mootle", "title": "¿Está cara o es chollo?",
     "sub": "Vemos el precio día a día para que lo sepas.", "cta": "mootle.es",
     "cap": "En mootle guardamos el histórico de precios de cada moto y cada producto de equipación, "
            "así sabes si lo que ves es un chollo de verdad o no. 👉 mootle.es\n\n" + TAGS_MOTO},
    {"badge": "equipación", "title": "No solo motos.\nTambién equipación.",
     "sub": "Cascos, guantes, chaquetas… comparados entre tiendas.", "cta": "mootle.es",
     "cap": "Cascos, guantes, chaquetas, botas… en mootle comparamos equipación de moto entre tiendas "
            "para que pilles el mejor precio. 👉 mootle.es\n\n" + TAGS_EQUIP},
]


def load(p, d):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return d


def _listings():
    L = load(LISTINGS, {})
    return L if isinstance(L, list) else L.get("items", [])


def pick_comparativa(used):
    data = load(EQUIP, {})
    sources = data.get("sources", {})
    g = defaultdict(list)
    for it in data.get("items", []):
        if it.get("mid") and it.get("p"):
            g[it["mid"]].append(it)
    cand = []
    for mid, offs in g.items():
        shops = {o["src"] for o in offs}
        if len(shops) < 2 or mid in used:
            continue
        offs = sorted(offs, key=lambda o: o["p"])
        best = offs[0]
        img = next((o["img"] for o in offs if o.get("img")), None)
        if not img:
            continue
        # una oferta por tienda (la más barata de cada una)
        per = {}
        for o in offs:
            if o["src"] not in per or o["p"] < per[o["src"]]["p"]:
                per[o["src"]] = o
        shoplist = sorted(per.values(), key=lambda o: o["p"])[:4]
        cand.append({"mid": mid, "n": len(shops), "spread": offs[-1]["p"] - best["p"],
                     "d": {"kind": "comparativa", "title": f'{best["mk"]} {best["md"]}'[:48],
                           "cat": CAT_NAMES.get(best["cat"], best["cat"]), "img": img,
                           "min": best["p"], "n": len(shops),
                           "shops": [{"name": sources.get(o["src"], {}).get("name", o["src"]), "p": o["p"]}
                                     for o in shoplist]}})
    if not cand:
        return None
    cand.sort(key=lambda c: (-c["n"], -c["spread"]))
    c = cand[0]
    cap = (f'🛡️ {c["d"]["title"]} — lo comparamos en {c["n"]} tiendas.\n'
           f'Desde {c["d"]["min"]} €. Mira todas las ofertas y el histórico de precios en mootle.es 👉\n\n'
           + TAGS_EQUIP)
    return c["mid"], c["d"], cap


def pick_chollo(used):
    cand = []
    # motos que han bajado (pa -> p), filtrando bajadas absurdas
    for it in _listings():
        p, pa = it.get("p"), it.get("pa")
        if not (p and pa and pa > p and it.get("img")) or it["id"] in used:
            continue
        if p < 800:
            continue
        pct = round((pa - p) * 100 / pa)
        if pct < 8 or pct > 50:
            continue
        t = (it.get("t") or f'{it.get("mk","")} {it.get("md","")}').strip()
        if it.get("y"):
            t = f'{t} {it["y"]}'
        cand.append({"id": it["id"], "save": pa - p, "pct": pct,
                     "d": {"kind": "chollo", "cat": "Moto de ocasión", "title": t[:46],
                           "img": it["img"], "p": p, "was": pa, "save": pa - p, "pct": pct},
                     "tags": TAGS_MOTO})
    # equipación que ha bajado (p0 tachado o pa detectado)
    for it in load(EQUIP, {}).get("items", []):
        p = it.get("p")
        ref = max(it.get("p0") or 0, it.get("pa") or 0)
        if not (p and ref > p and it.get("img")) or it.get("id") in used:
            continue
        if p < 40:
            continue
        pct = round((ref - p) * 100 / ref)
        if pct < 10 or pct > 55:
            continue
        cand.append({"id": it["id"], "save": ref - p, "pct": pct,
                     "d": {"kind": "chollo", "cat": CAT_NAMES.get(it["cat"], it["cat"]),
                           "title": f'{it["mk"]} {it["md"]}'[:46], "img": it["img"],
                           "p": p, "was": ref, "save": ref - p, "pct": pct},
                     "tags": TAGS_EQUIP})
    if not cand:
        return None
    cand.sort(key=lambda c: (-c["pct"], -c["save"]))
    c = cand[0]
    cap = (f'🔥 CHOLLO · {c["d"]["title"]}\n'
           f'Ha bajado a {c["d"]["p"]} € (antes {c["d"]["was"]} €, −{c["pct"]}%). '
           f'Ficha e histórico en mootle.es 👉\n\n' + c["tags"])
    return c["id"], c["d"], cap


def pick_marca(state):
    i = state.get("marca_i", 0) % len(MARCA)
    m = MARCA[i]
    state["marca_i"] = i + 1
    return f"marca-{i}", {"kind": "marca", "badge": m["badge"], "title": m["title"],
                          "sub": m["sub"], "cta": m["cta"]}, m["cap"]


def kind_for_today():
    wd = date.today().weekday()   # 0=lunes
    return "comparativa" if wd in (0, 2, 4) else "chollo" if wd in (1, 3) else "marca"


def render(data, out):
    OUTDIR.mkdir(parents=True, exist_ok=True)
    tmp = OUTDIR / "_data.json"
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    subprocess.run(["node", str(ROOT / "scraper" / "render_post.cjs"), str(tmp), str(out)], check=True)
    tmp.unlink(missing_ok=True)


def git_push(pngs):
    subprocess.run(["git", "add", *[str(p) for p in pngs]], cwd=ROOT, check=True)
    r = subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT)
    if r.returncode == 0:
        return
    subprocess.run(["git", "commit", "-q", "-m", f"social: post diario {date.today().isoformat()}"], cwd=ROOT, check=True)
    for attempt in range(5):
        if subprocess.run(["git", "push", "-q", "origin", "HEAD:main"], cwd=ROOT).returncode == 0:
            return
        subprocess.run(["git", "pull", "-q", "--rebase", "origin", "main"], cwd=ROOT)
    raise RuntimeError("no se pudo hacer push de la imagen")


def wait_url(url, tries=40):
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, method="HEAD")
            if urllib.request.urlopen(req, timeout=15).status == 200:
                return True
        except Exception:
            pass
        time.sleep(5)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=["comparativa", "chollo", "marca"])
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args()

    state = load(STATE, {})
    used = state.setdefault("used", {})
    kind = args.kind or kind_for_today()

    picker = {"comparativa": lambda: pick_comparativa(set(used.get("comparativa", []))),
              "chollo": lambda: pick_chollo(set(used.get("chollo", []))),
              "marca": lambda: pick_marca(state)}[kind]
    got = picker()
    if not got:
        print(f"Sin contenido para '{kind}' hoy. Nada publicado.")
        return
    key, data, caption = got

    fname = f'{date.today().isoformat()}-{kind}.png'
    out = OUTDIR / fname
    render(data, out)
    print(f"Imagen generada: {out}")
    print(f"Texto:\n{caption}")
    if args.dry:
        return

    git_push([out])
    url = RAW + fname
    if not wait_url(url):
        print(f"Aviso: la imagen aún no responde en {url}; intento publicar igualmente.")
    from . import social
    res = social.publish_image(url, caption)
    mid = res.get("id")
    perma = ""
    try:
        import os
        tok = os.environ["INSTAGRAM_TOKEN_MOOTLE"]
        with urllib.request.urlopen(f"https://graph.instagram.com/{mid}?fields=permalink&access_token={tok}", timeout=30) as r:
            perma = json.load(r).get("permalink", "")
    except Exception:
        pass

    if kind != "marca":
        used.setdefault(kind, []).append(key)
        used[kind] = used[kind][-400:]
    state.setdefault("log", []).append({"date": date.today().isoformat(), "kind": kind, "id": mid, "permalink": perma})
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"PUBLICADO ({kind}): {perma or mid}")


if __name__ == "__main__":
    main()
