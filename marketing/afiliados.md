# Afiliados y fuentes de equipación — tracker de mootle

**Fuente de verdad del estado comercial de mootle.** Última actualización: **2026-11-13**.

Mantener aquí cada tienda, red o programa con su estado real. Cuando algo se
apruebe y haya feed/parámetros, se integra en mootle **vía rama + Pull Request**
(nunca cambios de código en `main` directamente) y se anota aquí.

**Leyenda de estado:** `cableado` ✅ (en producción) · `aprobado` (alta hecha, falta
integrar) · `solicitado` (petición enviada, esperando respuesta) · `contactado`
(correo/mensaje enviado) · `pendiente` (sin contactar todavía) · `descartado`.

**Separación de ventas entre mootle y la web hermana Guitle (panel compartido):**
eBay → `customid=mootle` · Amazon → tag `mootle-21` · Awin y redes → `&clickref=mootle`
(o el customparam equivalente de cada red). **Usar siempre el identificador de mootle**
en cada enlace nuevo, o las comisiones se mezclan con las de Guitle.

---

## 1. Tabla de seguimiento

### Equipación, recambios y neumáticos

| Tienda | Web | Red / Programa | Estado | Parámetros / Feed | Comisión | Notas |
|---|---|---|---|---|---|---|
| **eBay** | ebay.es | eBay Partner Network (EPN) | `cableado` ✅ | `campid=5339241544`, `customid=mootle`; feed vía API diaria | Variable (~1–4 % según categoría) | ~430 ofertas y subiendo. `scraper/ebay.py`. |
| **Amazon** | amazon.es | Amazon Afiliados | `cableado` ✅ | `tag=mootle-21` | Variable por categoría | Enlace neumáticos en ficha de moto + botón "Buscar en Amazon" en equipación. PA-API se desbloquea tras 3 ventas. `scraper/pages.py` (`AMAZON_TAG`). |
| **Máximo Moto** | maximo-moto.com | Shopify (fuente de precios, **sin afiliación**) | `contactado` (borrador pendiente de enviar) | `/products.json` diario | — | Fuente de comparación ya integrada. Borrador para formalizar afiliación. |
| **Albabike** | albabike.com | Propio / sin red (fuente de precios) | `contactado` (borrador pendiente de enviar) | Seed manual + scrape semanal | — | Fuente de comparación integrada; sin acuerdo de afiliación todavía. |
| **outletMOTARD** | outletmotard.es | Shopify, **sin afiliación pública** | fuente `cableado` ✅ (PR #1) · afiliación `pendiente` → contactar | `/products.json` (~788 prod.) | — | Integrada como fuente de precios (Scorpion, Alpinestars, HJC, Nox, CGM, Five…). Falta pedir feed oficial + afiliación. **Borrador listo:** `correos/outletmotard.md`. |
| **FC-Moto** | fc-moto.es | **Webgains** (ES activo desde 2024) · también FlexOffers | `pendiente` → alta Webgains + solicitar | CPA, cookie 30 d, aprobación manual | ~6 % CPA | Catálogo enorme, envía a España. Buen primer anunciante no-Shopify. |
| **Tradeinn / Motardinn** | motardinn.com | **Belboon** (Tradeinn, activo desde 2018) · Motardinn en TradeTracker | `pendiente` | — | 5–10 % (Motardinn, por confirmar) | Grupo español (Girona), multi-tienda. |
| **Motocard** | motocard.com | **TradeDoubler** (MOTOCARD ES) | `aprobado` ✅ · código `listo` (PR #2) · **espera 2 pasos de Manuel** | enlace afiliado en `offers[].productUrl`; sitio mootle `a(3505826)` | ~4 % (ref. PT) | Integración lista y probada (PR #2, apilado sobre #1). Para que dé fruto, Manuel debe: (1) conectar el feed al sitio **Mootle 3505826** (Gestionar → Feed de Producto); (2) guardar el secreto `TRADEDOUBLER_PRODUCTS_TOKEN`. Guardia de atribución: solo coge ofertas con `a(3505826)`, nunca de guitle. |
| **Motoblouz** | motoblouz.es | **TradeDoubler** (no aparece en panel) · abierto en **BlueAff / Sale Gains / Effinity** | `pendiente` → vía otra red o pedir a gestor TD | subid `mootle` | Por confirmar en ES | En el panel de TD de mootle no sale; plan B por BlueAff/Sale Gains/Effinity. |
| **XLmoto** | xlmoto.es | TradeDoubler (solo **FR/UK**; sin ES) | `pendiente` → verificar | — | ~8 % (ref. IT) | En TD no hay programa España ahora mismo; revisar si lo abren. |
| **Neumáticos** (Delticom / Neumáticos-online) | — | Red por confirmar (coche + **moto**) | `pendiente` → buscar en directorios | — | ~ (tickets ~210 €) | Complementa a Amazon en neumáticos. Buscar en TD/otras. |
| **Polo Motorrad** | polo-motorrad.com | **Awin** (DE, cookie 60 d) · Webgains ~5 % | `pendiente` | — | ~5 % | Verificar tienda/envío España antes de priorizar. |
| **24MX** | 24mx.es | Por confirmar (no aparece en Awin ES) | `pendiente` | — | — | Off-road/cross. Buscar su red. |
| **Tienda-Moto** | tienda-moto.com | Por confirmar | `pendiente` | — | — | Recambio genérico. Buscar su red. |

### Seguros (pagan muy bien por lead — prioridad alta)

| Marca | Web | Red / Programa | Estado | Parámetros | Comisión | Notas |
|---|---|---|---|---|---|---|
| **Línea Directa** | lineadirecta.com | **Awin** (merchant 11078) | `solicitado` pendiente → **Join programme** (cuenta Awin ✅) | CPL, `clickref=mootle`, IP española, ventana 30 d | **~8 €/lead** (verificar en Awin) | Lead = completar formulario y ver precios. Solo en una plataforma a la vez. Ya listada en `/seguros` **sin** enlace de afiliado — cablear deeplink al aprobar. |
| **Rastreator** | rastreator.com | Programa propio / partner | `pendiente` → contactar | — | CPL (alto) | Contacto: **afiliados@rastreator.com**. **Borrador listo:** `correos/rastreator-seguros.md`. |
| **Acierto** | acierto.com | Por confirmar (red/propio) | `pendiente` | — | CPL | Alternativa/complemento a Rastreator. |

### Financiación

| Marca | Web | Red / Programa | Estado | Comisión | Notas |
|---|---|---|---|---|---|
| **Cetelem** | cetelem.es | Por confirmar (red) | `pendiente` | CPL/CPA | Ya listada en `/financiacion`. |
| **Cofidis** | cofidis.es | Por confirmar (red) | `pendiente` | CPL/CPA | Ya listada en `/financiacion`. |
| **Younited** | younited-credit.com | Por confirmar (red) | `pendiente` | CPL/CPA | Ya listada en `/financiacion`. |

---

## 2. Redes de afiliación (altas que abren varias tiendas a la vez)

Dar de alta a mootle como **publisher/afiliado** en una red desbloquea de golpe
muchos anunciantes. Prioridad por nº de anunciantes de moto relevantes:

| Red | Qué desbloquea para mootle | Estado | Cómo se saca el enlace/feed |
|---|---|---|---|
| **Awin** | Línea Directa (seguros, ~8 €/lead), Polo Motorrad, y muchos más | `aprobado` ✅ (publisher de mootle creado; login `mootle@guitle.com`) | Tras aprobación del anunciante: "Create a Link" → pegar deeplink + `&clickref=mootle`. Feed de productos en "Toolbox → Product Feeds". |
| **TradeDoubler** | **Motocard ES** ✅ (aprobado), Motoblouz (no sale) | `aprobado` ✅ (publisher de mootle aceptado) | **Feeds por API** (probado por Guitle): token PRODUCTS (40 car., 1 por usuario) como secreto `TRADEDOUBLER_PRODUCTS_TOKEN`. Listar: `GET api.tradedoubler.com/1.0/productFeeds?token=…`. Productos: `…/products.json;page=N;pageSize=100;fid=FEEDID?token=…`. El enlace de afiliado ya viene en `offers[].productUrl`. Cada feed se conecta por sitio en Gestionar → Feed de Producto. |
| **Webgains** | FC-Moto (ES) | `pendiente` | Deeplink con `clickref=mootle`. |
| **Belboon** | Tradeinn | `pendiente` | Deeplink + subid. |
| **TradeTracker** | Motardinn, otras | `pendiente` | Deeplink + subid (`ref`). |
| **FlexOffers** | FC-Moto, Motocard (genéricos) | `pendiente` (plan B) | Solo si la red nativa no aprueba. |

> Awin **ya no pide depósito** en el alta de publisher en España (antes pedía uno
> reembolsable de 5 $; a Manuel no se lo han pedido). Solo una pequeña validación del
> sitio, que mootle.es (web real, con tráfico y catálogo) cumple sin problema.

> ⚠️ **TradeDoubler — atribución mootle vs guitle (CRÍTICO).** Con el token actual de
> Manuel solo aparecen los feeds del **sitio de guitle (ID 3505824)** y todos los
> `offers[].productUrl` llevan `a(3505824)`. Antes de cablear Motocard hay que confirmar
> que su feed se conecta al **sitio de mootle** y que el `productUrl` lleva `a(<ID sitio
> mootle>)`. Si mootle no tiene sitio propio en TradeDoubler, hay que crearlo (o pedir un
> token del sitio de mootle). Si el enlace viniera con `a(3505824)`, **no usarlo tal cual**:
> reescribir `a(…)` con el sitio de mootle, o la comisión se la lleva guitle.

---

## 3. Lista priorizada de objetivos (esfuerzo vs. retorno)

Orden recomendado para Manuel. "Esfuerzo" es lo que cuesta ponerlo a facturar.

| # | Objetivo | Vía de monetización | Por qué ahora | Esfuerzo |
|---|---|---|---|---|
| 1 | **Alta de mootle en Awin** | Red (abre Línea Directa + más) | Llave maestra: un alta desbloquea el lead de seguros mejor pagado | ✅ Hecho (login `mootle@guitle.com`) |
| 2 | **Línea Directa (seguros)** vía Awin | CPL ~8 €/lead | Ya la listamos en `/seguros`; solo falta el enlace de afiliado | **Siguiente**: Join programme → deeplink → cablear 1 enlace |
| 3 | **Rastreator (seguros)** | CPL alto | Contacto directo conocido; comparador = lead de alto valor | Bajo (1 correo) |
| 4 | **outletMOTARD** (equipación) | Shopify feed + afiliación directa | ✅ **Integrada como fuente** (PR #1, ~788 prod.); falta el correo pidiendo feed + afiliación | Hecho el código · falta 1 correo |
| 5 | **FC-Moto** vía Webgains | CPA ~6 % | Catálogo enorme, envía a ES, red clara y activa | Medio (alta Webgains + solicitar + enlaces) |
| 6 | **Alta de mootle en TradeDoubler** | Red (Motoblouz, XLmoto…) | Segunda red con varias tiendas de moto | Medio |
| 7 | **Motoblouz** vía TradeDoubler | CPA | Programa ES abierto | Medio |
| 8 | **Tradeinn/Motardinn** vía Belboon/TradeTracker | 5–10 % | Grupo español grande | Medio |
| 9 | **Cetelem / Cofidis / Younited** (financiación) | CPL/CPA | Ya listadas en `/financiacion`; buen lead | Medio (localizar su red) |
| 10 | **Máximo Moto / Albabike** (formalizar) | Afiliación directa | Ya les enviamos tráfico; formalizarlo | Bajo (reusar borradores pendientes) |
| 11 | **XLmoto** vía TradeDoubler | CPA | Si hay programa ES abierto | Medio |
| 12 | **Polo Motorrad / 24MX / Motocard** | Awin / por confirmar | Confirmar estado antes de invertir | Medio-alto (incierto) |

**Regla rápida:** seguros/financiación pagan por **lead** (mucho por poco tráfico) →
atacar primero. Equipación paga **% por venta** (poco por clic) pero suma catálogo y
SEO → tiendas Shopify se integran como fuente **aunque no haya afiliación todavía**.

---

## 4. Decisiones que necesito de Manuel

1. ~~Alta en Awin~~ ✅ **Hecho** (publisher de mootle, login `mootle@guitle.com`).
2. ~~Email de contacto~~ ✅ **mootle@guitle.com** (ya puesto en los borradores).
3. **En Awin, solicitar Línea Directa**: Advertisers → "Línea Directa" → *Join programme*
   (mensaje listo en `correos/alta-red-awin.md`, B.2). Al aprobar, sácame el **deeplink**.
4. **¿Enviamos ya** los borradores a outletmotard y a Rastreator, y reactivamos los de
   Máximo/Albabike? (Los redacto/actualizo yo; los envías tú.)
5. **outletmotard**: ¿quieres que prepare ya la integración como fuente Shopify
   (`scraper/sources/shopify.py` / `scraper/equip.py`) **en una rama + PR**, en paralelo
   al contacto comercial? Se puede listar como fuente de precios sin esperar al acuerdo.

---

## 5. Borradores de correo preparados

- `marketing/correos/outletmotard.md` — pedir feed + afiliación.
- `marketing/correos/rastreator-seguros.md` — alta de afiliación de seguros.
- `marketing/correos/alta-red-awin.md` — texto para el alta en Awin + primeras
  solicitudes de anunciante (Línea Directa, FC-Moto).

> Los borradores están **listos para que los envíe Manuel**. Yo no envío correos ni me
> doy de alta en ninguna red: investigo, redacto y preparo la integración.
