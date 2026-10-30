// Contador de visitas de mootle, sin cookies ni datos personales: solo suma 1 por día a unos contadores en
// Firestore (proyecto guitle-d48d8, colección "cm" para no mezclar con guitle). Las reglas de Firestore solo
// permiten sumar de 1 en 1, nunca leer ni borrar.
//   AAAA-MM-DD_v           visitas (páginas vistas) del día
//   AAAA-MM-DD_p_<página>  vistas de cada página
//   AAAA-MM-DD_r_<origen>  llegadas desde fuera (google.com, instagram.com…; "directo" sin origen)
//   AAAA-MM-DD_t_<tienda>  clics hacia cada tienda
(() => {
  // Las visitas del propio equipo no cuentan: mootle.es/?nocontar lo apaga en ese navegador; ?contar lo vuelve a encender.
  try {
    const q = new URLSearchParams(location.search);
    if (q.has("nocontar")) localStorage.setItem("mootle_nocontar", "1");
    if (q.has("contar")) localStorage.removeItem("mootle_nocontar");
    if (localStorage.getItem("mootle_nocontar")) return;
  } catch (e) {}
  if (location.hostname !== "mootle.es" || navigator.webdriver
      || /bot|crawl|spider|slurp|headless|lighthouse|preview|facebookexternalhit/i.test(navigator.userAgent)) return;
  const DOCS = "projects/guitle-d48d8/databases/(default)/documents/cm/";
  const day = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Madrid" });
  const clean = s => s.toLowerCase().replace(/^www\./, "").replace(/\.html$/, "").replace(/\//g, "~")
    .replace(/[^a-z0-9.~_-]/g, "").slice(0, 150) || "~";
  const add = keys => {
    try {
      fetch("https://firestore.googleapis.com/v1/" + DOCS.split("/cm/")[0] + ":commit", {
        method: "POST", keepalive: true, headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ writes: keys.map(k => ({ transform: {
          document: DOCS + day + "_" + k, fieldTransforms: [{ fieldPath: "n", increment: { integerValue: "1" } }] } })) }),
      }).catch(() => {});
    } catch (e) {}
  };

  // Búsquedas en el buscador (motos y equipación): se cuentan como páginas "buscar~<texto>", sin nada más.
  const searched = new Set();
  window.mootleSearch = q => {
    const term = String(q || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim().replace(/\s+/g, "-").slice(0, 60);
    if (term.length < 3 || searched.has(term)) return;
    searched.add(term);
    add(["p_buscar~" + clean(term)]);
  };

  const keys = ["v", "p_" + clean(location.pathname.replace(/^\//, "") || "inicio")];
  let from = "";
  try { from = document.referrer ? new URL(document.referrer).hostname : ""; } catch (e) {}
  if (from !== location.hostname) keys.push("r_" + (from ? clean(from) : "directo"));
  add(keys);

  // Clics hacia las tiendas (enlaces patrocinados). Awin y similares llevan la URL de la tienda dentro.
  document.addEventListener("click", e => {
    const a = e.target.closest && e.target.closest('a[rel~="sponsored"]');
    if (!a) return;
    try {
      const u = new URL(a.href);
      const inner = u.searchParams.get("ued") || u.searchParams.get("url");
      const host = inner ? new URL(inner).hostname : u.hostname;
      add(["t_" + clean(host.replace(/^(es|m)\./, ""))]);
    } catch (err) {}
  }, true);
})();
