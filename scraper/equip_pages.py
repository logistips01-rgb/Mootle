"""Páginas del comparador de equipación (dentro de /equipacion/).

Reutiliza el motor de páginas de motos (cabecera, pie, gráfica de histórico, estilos).
Todas las páginas viven directamente bajo /equipacion/ (un nivel), así que las rutas
relativas ../ a mootle.css / icon.svg / inicio funcionan igual que en m/ y marca/.
"""
import json
import statistics
from collections import defaultdict
from pathlib import Path

from .equip import CAT_NAMES
from .pages import FOOT, SITE, chart, e, eur, head, num, slug, write

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "equipacion"

GEAR = ('<svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 14a8 8 0 1116 0v2H4z"/>'
        '<path d="M4 16h11"/></svg>')


def groups_of(items):
    by = defaultdict(list)
    for it in items:
        if it.get("mid") and it.get("p"):
            by[it["mid"]].append(it)
    out = {}
    for mid, offers in by.items():
        offers.sort(key=lambda m: m["p"])
        best = offers[0]
        prices = [m["p"] for m in offers]
        out[mid] = {"mid": mid, "mk": best["mk"], "md": best["md"], "cat": best["cat"],
                    "offers": offers, "best": best, "n": len(offers),
                    "min": best["p"], "max": max(prices), "med": int(statistics.median(prices)),
                    "img": next((m["img"] for m in offers if m.get("img")), None),
                    "webs": sorted({m["src"] for m in offers})}
    return out


def _name(g):
    return f'{g["mk"]} {g["md"]}'.strip()


def _card(g):
    img = f'<img src="{e(g["img"])}" alt="" loading="lazy" referrerpolicy="no-referrer">' if g["img"] else GEAR
    drop = ""
    pa = g["best"].get("pa")
    if pa and pa > g["min"]:
        drop = f'<span class="drop">−{eur(pa - g["min"])}</span>'
    return (f'<a class="card eq" href="{g["mid"]}.html"><div class="photo">{img}{drop}</div><div class="body">'
            f'<span class="brand">{e(g["mk"])} · {e(CAT_NAMES.get(g["cat"], g["cat"]).rstrip("s"))}</span>'
            f'<span class="name">{e(g["md"])[:60]}</span>'
            f'<span class="price"><strong>{eur(g["min"])}</strong></span>'
            f'<span class="foot">{g["n"]} oferta{"s" if g["n"] > 1 else ""}'
            f'{" · " + str(len(g["webs"])) + " tiendas" if len(g["webs"]) > 1 else ""}</span></div></a>')


def _sim_card(it, ref, sources):
    img = f'<img src="{e(it["img"])}" alt="" loading="lazy" referrerpolicy="no-referrer">' if it.get("img") else GEAR
    d = it["p"] - ref
    diff = (f'<span class="simdiff up">+{eur(d)}</span>' if d > 0 else
            f'<span class="simdiff down">−{eur(-d)}</span>' if d < 0 else
            '<span class="simdiff">mismo precio</span>')
    sh = sources.get(it["src"], {}).get("name", it["src"])
    return (f'<a class="card eq" href="{e(it["mid"])}.html"><div class="photo">{img}{diff}</div><div class="body">'
            f'<span class="brand">{e(it["mk"])} · {e(CAT_NAMES.get(it["cat"], it["cat"]).rstrip("s"))}</span>'
            f'<span class="name">{e(it["md"])[:60]}</span>'
            f'<span class="price"><strong>{eur(it["p"])}</strong></span>'
            f'<span class="foot">en {e(sh)}</span></div></a>')


def _similars(g, cat_items, limit=8):
    """Alternativas de la misma categoría en OTRAS tiendas, en un rango de precio similar.

    Da igual que no sea el mismo producto: así un airbag de la marca X (solo en una
    tienda) se compara con un airbag de la marca Z de otra tienda a precio parecido.
    Primero una por cada tienda ajena (la más cercana en precio); luego se rellena con
    las siguientes más cercanas hasta `limit`.
    """
    ref = g["min"]
    own = set(g["webs"])
    lo, hi = ref * 0.5, ref * 1.8   # "rango de precios" para que la comparación tenga sentido
    cand = [it for it in cat_items
            if it["src"] not in own and it["mid"] != g["mid"] and lo <= it["p"] <= hi]
    per_shop = {}
    for it in cand:
        cur = per_shop.get(it["src"])
        if cur is None or abs(it["p"] - ref) < abs(cur["p"] - ref):
            per_shop[it["src"]] = it
    picks, seen = [], {g["mid"]}
    for it in sorted(per_shop.values(), key=lambda it: abs(it["p"] - ref)):
        if it["mid"] not in seen:
            picks.append(it)
            seen.add(it["mid"])
    for it in sorted(cand, key=lambda it: abs(it["p"] - ref)):
        if len(picks) >= limit:
            break
        if it["mid"] not in seen:
            picks.append(it)
            seen.add(it["mid"])
    picks.sort(key=lambda it: abs(it["p"] - ref))
    return picks[:limit]


def product_page(g, sources, history, cat_items=()):
    name = _name(g)
    catn = CAT_NAMES.get(g["cat"], g["cat"]).rstrip("s")
    title = f"{name} al mejor precio · equipación · mootle"
    desc = (f"{name} ({catn.lower()} de moto) desde {eur(g['min'])}" +
            (f" comparando {len(g['webs'])} tiendas" if len(g["webs"]) > 1 else "") +
            ". Precio, ofertas e histórico de precios.")
    ld = {"@context": "https://schema.org", "@type": "Product", "name": name, "category": catn,
          "brand": {"@type": "Brand", "name": g["mk"]},
          "offers": {"@type": "AggregateOffer", "priceCurrency": "EUR", "lowPrice": g["min"],
                     "highPrice": g["max"], "offerCount": g["n"], "availability": "https://schema.org/InStock"}}
    if g["img"]:
        ld["image"] = g["img"]
    rows = ""
    for m in g["offers"]:
        sh = sources.get(m["src"], {}).get("name", m["src"])
        p0 = f'<span class="was">{eur(m["p0"])}</span>' if m.get("p0") else ""
        rows += (f'<div class="offer"><span class="p">{eur(m["p"])} {p0}</span>'
                 f'<span class="v">{e(m["t"])[:80]}</span>'
                 f'<span class="w">{e(sh)}</span>'
                 f'<a class="go" href="{e(m["url"])}" target="_blank" rel="sponsored nofollow noopener noreferrer">Ver en la tienda ↗</a></div>')
    img = f'<img src="{e(g["img"])}" alt="{e(name)}" referrerpolicy="no-referrer">' if g["img"] else GEAR
    # Alternativas en otras tiendas: SOLO cuando el producto está en una única tienda
    # (si el mismo producto está en varias, ya se compara mismo-contra-mismo en "Ofertas").
    sim_html = ""
    if len(g["webs"]) == 1:
        sims = _similars(g, cat_items)
        if sims:
            cards = "".join(_sim_card(it, g["min"], sources) for it in sims)
            sim_html = (f'  <div class="panel"><h2 class="display">Alternativas en otras tiendas</h2>\n'
                        f'    <p class="muted" style="margin:0 0 12px">No hemos encontrado este {catn.lower()} exacto en otras tiendas. '
                        f'Estos son parecidos, de la misma categoría y en un rango de precio similar.</p>\n'
                        f'    <div class="grid eq">{cards}</div></div>\n')
    body = f"""  <nav class="crumbs" aria-label="Migas"><a href="../">Inicio</a> › <a href="./">Equipación</a> › <a href="{g['cat']}.html">{e(CAT_NAMES.get(g['cat'], g['cat']))}</a> › {e(name)}</nav>
  <div class="ficha-head">
    <div class="photo eq">{img}</div>
    <div>
      <span class="kicker">{e(g['mk'])} · {e(catn)}</span>
      <h1 class="display">{e(name)}</h1>
      <p class="sub">{g['n']} oferta{'s' if g['n'] > 1 else ''}{f" en {len(g['webs'])} tiendas" if len(g['webs']) > 1 else ''}. Desde {eur(g['min'])}.</p>
      <p><a class="btn" href="{e(g['best']['url'])}" target="_blank" rel="sponsored nofollow noopener noreferrer">Ver la más barata ↗</a></p>
    </div>
  </div>
  <div class="panel"><h2 class="display">Ofertas</h2><div class="offers eq">{rows}</div></div>
  <div class="panel"><h2 class="display">Histórico de precios</h2>
    <p class="muted" style="margin:0">Precio más barato de {e(name)}, día a día.</p>{chart(history.get(g['mid']))}</div>
{sim_html}  <p class="aff-note" style="max-width:70ch">Enlaces de afiliados: si compras, mootle puede llevarse una pequeña comisión, sin coste para ti. Precios tomados de cada tienda; compruébalos siempre en la tienda.</p>
"""
    return head(title, desc, f"{SITE}/equipacion/{g['mid']}.html", g["img"], ld,
                search_action="./", search_ph="Casco, guantes, chaqueta, marca…") + body + FOOT


def category_page(cat, groups):
    name = CAT_NAMES.get(cat, cat)
    # Orden: primero por presencia de ofertas (nº de tiendas y de ofertas); el precio desempata.
    groups = sorted(groups, key=lambda g: (-len(g["webs"]), -g["n"], g["min"]))
    cheapest = groups[0]["min"] if groups else 0
    title = f"{name} de moto baratos: {num(len(groups))} desde {eur(cheapest)} · mootle"
    desc = f"Compara {num(len(groups))} {name.lower()} de moto desde {eur(cheapest)}. Precios, ofertas e histórico."
    body = f"""  <nav class="crumbs" aria-label="Migas"><a href="../">Inicio</a> › <a href="./">Equipación</a> › {e(name)}</nav>
  <h1 class="display" style="font-size:clamp(28px,4vw,40px);margin:8px 0 4px">{e(name)} de moto</h1>
  <p class="sub" style="color:var(--text-secondary)">{num(len(groups))} {e(name.lower())} desde {eur(cheapest)}.</p>
  <div class="grid eq">{"".join(_card(g) for g in groups)}</div>
"""
    return head(title, desc, f"{SITE}/equipacion/{cat}.html",
                search_action="./", search_ph="Casco, guantes, chaqueta, marca…") + body + FOOT


def index_page(groups, sources):
    gl = list(groups.values())
    total = sum(g["n"] for g in gl)
    by_cat = defaultdict(list)
    for g in gl:
        by_cat[g["cat"]].append(g)
    # Chollos de hoy = SOLO bajadas de precio reales (histórico), las más recientes primero.
    # Si un día no ha bajado nada, la sección sale vacía (es intencionado).
    drops = sorted([g for g in gl if g["best"].get("pa") and g["best"]["pa"] > g["min"]],
                   key=lambda g: (g["best"].get("pc") or "", g["best"]["pa"] - g["min"]), reverse=True)
    seen_mid, featured = set(), []
    for g in drops:
        if g["mid"] in seen_mid:
            continue
        seen_mid.add(g["mid"])
        featured.append(g)
        if len(featured) >= 12:
            break
    chollo_note = ("Equipación que ha bajado de precio: las rebajas más recientes primero. La lista cambia según detectamos bajadas." if featured else
                   "Hoy no ha bajado de precio ningún producto. En cuanto una tienda baje un precio, aparecerá aquí.")
    cats_tiles = "".join(
        f'<a class="source" href="{cat}.html"><span>{e(CAT_NAMES.get(cat, cat))}<small>desde {eur(min(g["min"] for g in gs))}</small></span>'
        f'<b>{num(len(gs))}</b></a>' for cat, gs in sorted(by_cat.items(), key=lambda kv: -len(kv[1])))
    title = "Equipación de moto al mejor precio: cascos, guantes, chaquetas · mootle"
    desc = (f"Comparador de equipación de moto: {num(total)} productos (cascos, guantes, chaquetas, botas…) "
            "con precios, ofertas e histórico. Encuentra el más barato.")
    cat_chips = '<button class="chip on" data-cat="">Todas</button>' + "".join(
        f'<button class="chip" data-cat="{cat}">{e(CAT_NAMES.get(cat, cat))}</button>'
        for cat in sorted(by_cat, key=lambda c: -len(by_cat[c])))
    body = f"""  <div class="hero" style="padding:26px 0 6px;text-align:center">
    <h1 class="display" style="font-size:clamp(28px,5vw,44px);margin:0">Equipación de moto <span style="color:var(--accent)">al mejor precio</span></h1>
    <p class="sub" style="color:var(--text-muted);margin:8px 0 0">Cascos, guantes, chaquetas, botas y más — comparados entre tiendas.</p>
    <form class="search" id="eq-form" role="search" style="max-width:640px;margin:16px auto 0">
      <input id="q-eq" type="search" placeholder="Busca: casco ls2, guantes verano, chaqueta…" autocomplete="off" aria-label="Buscar equipación">
      <button class="btn" type="submit">Buscar</button>
    </form>
    <div class="sortbar" id="eq-chips" style="justify-content:center;margin-top:12px">{cat_chips}</div>
    <div style="margin-top:10px">
      <select id="eq-price" class="eq-price" aria-label="Precio">
        <option value="">Precio: cualquiera</option>
        <option value="0-50">Menos de 50 €</option>
        <option value="50-100">50 - 100 €</option>
        <option value="100-200">100 - 200 €</option>
        <option value="200-400">200 - 400 €</option>
        <option value="400-">Más de 400 €</option>
      </select>
    </div>
  </div>
  <div id="eq-results" hidden><p class="sec-sub" id="eq-count"></p><div class="grid eq" id="eq-grid"></div></div>
  <div id="eq-browse">
    <div class="panel"><h2 class="display">Por categoría</h2><div class="sources">{cats_tiles}</div></div>
    <section><div class="sec-head"><h2 class="display">Chollos de equipación</h2></div>
      <p class="sub" style="color:var(--text-muted);margin:0 0 14px">{chollo_note}</p>
      <div class="grid eq">{"".join(_card(g) for g in featured)}</div></section>
  </div>
""" + _SEARCH_JS
    return head(title, desc, f"{SITE}/equipacion/",
                search_action="./", search_ph="Casco, guantes, chaqueta, marca…") + body + FOOT


_SEARCH_JS = """<script>
(function(){
  var nf=new Intl.NumberFormat("es-ES");
  var CN={casco:"Casco",guantes:"Guante",chaqueta:"Chaqueta",botas:"Bota",pantalon:"Pantalón",mono:"Mono"};
  var fold=function(s){return String(s||"").normalize("NFD").replace(/[\\u0300-\\u036f]/g,"").toLowerCase();};
  var eur=function(v){return nf.format(v)+" €";};
  var $=function(id){return document.getElementById(id);};
  var DATA=[], cat="";
  function card(g){
    var img=g.img?'<img src="'+g.img+'" alt="" loading="lazy" referrerpolicy="no-referrer">':'';
    var foot=(g.n+" oferta"+(g.n>1?"s":""))+(g.w>1?" \\u00b7 "+g.w+" tiendas":"");
    return '<a class="card eq" href="'+g.mid+'.html"><div class="photo">'+img+'</div><div class="body">'
      +'<span class="brand">'+g.mk+' \\u00b7 '+(CN[g.cat]||g.cat)+'</span>'
      +'<span class="name">'+g.md+'</span>'
      +'<span class="price"><strong>'+eur(g.p)+'</strong></span>'
      +'<span class="foot">'+foot+'</span></div></a>';
  }
  function run(){
    var qs=fold($("q-eq").value).split(/\\s+/).filter(Boolean);
    var pv=$("eq-price").value, lo=0, hi=Infinity;
    if(pv){var pp=pv.split("-"); lo=+pp[0]||0; hi=(pp[1]==="")?Infinity:(+pp[1]||Infinity);}
    var browsing=!qs.length && !cat && !pv;
    $("eq-browse").hidden=!browsing; $("eq-results").hidden=browsing;
    if(browsing){history.replaceState(null,"",location.pathname);return;}
    if(window.mootleSearch) window.mootleSearch($("q-eq").value);
    var r=DATA.filter(function(g){
      if(cat && g.cat!==cat) return false;
      if(g.p<lo || g.p>hi) return false;
      var hay=fold(g.mk+" "+g.md+" "+(CN[g.cat]||""));
      return qs.every(function(w){return hay.indexOf(w)>=0;});
    });
    r.sort(function(a,b){return (b.w-a.w)||(b.n-a.n)||(a.p-b.p);});
    $("eq-count").textContent=nf.format(r.length)+(r.length===1?" producto":" productos");
    $("eq-grid").innerHTML=r.length?r.slice(0,150).map(card).join(""):'<p class="empty">Nada por aquí. Prueba otra búsqueda.</p>';
    var p=new URLSearchParams(); if($("q-eq").value.trim())p.set("q",$("q-eq").value.trim()); if(cat)p.set("cat",cat); if(pv)p.set("precio",pv);
    history.replaceState(null,"","?"+p.toString());
  }
  $("eq-form").addEventListener("submit",function(e){e.preventDefault();run();});
  $("q-eq").addEventListener("input",function(){clearTimeout(window.__t);window.__t=setTimeout(run,180);});
  $("eq-price").addEventListener("change",run);
  $("eq-chips").addEventListener("click",function(e){var b=e.target.closest("[data-cat]");if(!b)return;cat=b.dataset.cat;var cs=document.querySelectorAll("#eq-chips .chip");for(var i=0;i<cs.length;i++)cs[i].classList.toggle("on",cs[i]===b);run();});
  fetch("buscador.json").then(function(r){return r.json();}).then(function(d){
    DATA=d; var p=new URLSearchParams(location.search); var q=p.get("q")||""; cat=p.get("cat")||"";
    $("q-eq").value=q; $("eq-price").value=p.get("precio")||"";
    var cs=document.querySelectorAll("#eq-chips .chip"); for(var i=0;i<cs.length;i++)cs[i].classList.toggle("on",cs[i].dataset.cat===cat);
    run();
  }).catch(function(){});
})();
</script>"""


def build(data, history):
    items, sources = data.get("items", []), data.get("sources", {})
    groups = groups_of(items)
    items_by_cat = defaultdict(list)
    for it in items:
        if it.get("mid") and it.get("p") and it.get("cat"):
            items_by_cat[it["cat"]].append(it)
    changed = 0
    for g in groups.values():
        changed += write(DIR / f'{g["mid"]}.html', product_page(g, sources, history, items_by_cat.get(g["cat"], ())))
    by_cat = defaultdict(list)
    for g in groups.values():
        by_cat[g["cat"]].append(g)
    for cat, gs in by_cat.items():
        changed += write(DIR / f"{cat}.html", category_page(cat, gs))
    changed += write(DIR / "index.html", index_page(groups, sources))
    # índice ligero para el buscador de equipación (cliente)
    idx = [{"mid": g["mid"], "mk": g["mk"], "md": g["md"], "cat": g["cat"], "p": g["min"],
            "n": g["n"], "w": len(g["webs"]), "img": g["img"]} for g in groups.values()]
    idx.sort(key=lambda x: (-x["w"], -x["n"], x["p"]))
    write(DIR / "buscador.json", json.dumps(idx, ensure_ascii=False, separators=(",", ":")))
    urls = [f"{SITE}/equipacion/"] + [f"{SITE}/equipacion/{cat}.html" for cat in sorted(by_cat)] + \
           [f"{SITE}/equipacion/{mid}.html" for mid in sorted(groups)]
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
               "".join(f"  <url><loc>{e(u)}</loc></url>\n" for u in urls) + "</urlset>\n")
    write(ROOT / "sitemap-equipacion.xml", sitemap)
    return changed
