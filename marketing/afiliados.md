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
| **outletmotard** | outletmotard.es | Shopify, **sin afiliación pública** | `pendiente` → contactar | `/products.json` (~1.000 prod. Alpinestars outlet) | — | Scrapeable ya como fuente. Pedir feed + comisión. **Borrador listo:** `correos/outletmotard.md`. |
| **FC-Moto** | fc-moto.es | **Webgains** (ES activo desde 2024) · también FlexOffers | `pendiente` → alta Webgains + solicitar | CPA, cookie 30 d, aprobación manual | ~6 % CPA | Catálogo enorme, envía a España. Buen primer anunciante no-Shopify. |
| **Tradeinn / Motardinn** | motardinn.com | **Belboon** (Tradeinn, activo desde 2018) · Motardinn en TradeTracker | `pendiente` | — | 5–10 % (Motardinn, por confirmar) | Grupo español (Girona), multi-tienda. |
| **Motoblouz** | motoblouz.es | **TradeDoubler** (+ otras redes) | `pendiente` | — | Por confirmar en ES | Programa ES figura abierto; verificar comisión. |
| **XLmoto** | xlmoto.es | **TradeDoubler** (FR/UK confirmado; ES por verificar) | `pendiente` | — | Por confirmar | Confirmar que hay programa ES abierto. |
| **Polo Motorrad** | polo-motorrad.com | **Awin** (DE, cookie 60 d) · Webgains ~5 % | `pendiente` | — | ~5 % | Verificar tienda/envío España antes de priorizar. |
| **Motocard** | motocard.com | TradeDoubler / FlexOffers (histórico) | `pendiente` → verificar estado | — | ~2,4 % (dato antiguo) | El programa puede estar cerrado; confirmar antes de invertir tiempo. |
| **24MX** | 24mx.es | Por confirmar (no aparece en Awin ES) | `pendiente` | — | — | Off-road/cross. Buscar su red. |
| **Tienda-Moto** | tienda-moto.com | Por confirmar | `pendiente` | — | — | Recambio genérico. Buscar su red. |

### Seguros (pagan muy bien por lead — prioridad alta)

| Marca | Web | Red / Programa | Estado | Parámetros | Comisión | Notas |
|---|---|---|---|---|---|---|
| **Línea Directa** | lineadirecta.com | **Awin** (merchant 11078) | `pendiente` → alta Awin + solicitar | CPL, `clickref=mootle`, IP española, ventana 30 d | **~8 €/lead** (verificar en Awin) | Lead = completar formulario y ver precios. Solo en una plataforma a la vez. Ya listada en `/seguros` **sin** enlace de afiliado. |
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
| **Awin** | Línea Directa (seguros, ~8 €/lead), Polo Motorrad, y muchos más | `pendiente` → dar de alta a mootle | Tras aprobación del anunciante: "Create a Link" → pegar deeplink + `&clickref=mootle`. Feed de productos en "Toolbox → Product Feeds". |
| **TradeDoubler** | Motoblouz, XLmoto, Motocard (histórico) | `pendiente` | Deeplink + parámetro `epi`/`a` para el subid (usar `mootle`). Feeds en "Product feeds". |
| **Webgains** | FC-Moto (ES) | `pendiente` | Deeplink con `clickref=mootle`. |
| **Belboon** | Tradeinn | `pendiente` | Deeplink + subid. |
| **TradeTracker** | Motardinn, otras | `pendiente` | Deeplink + subid (`ref`). |
| **FlexOffers** | FC-Moto, Motocard (genéricos) | `pendiente` (plan B) | Solo si la red nativa no aprueba. |

> Awin pide normalmente un **depósito reembolsable de 5 $** al registrar el publisher
> y una pequeña validación del sitio. mootle.es (web real, con tráfico y catálogo)
> cumple el perfil sin problema.

---

## 3. Lista priorizada de objetivos (esfuerzo vs. retorno)

Orden recomendado para Manuel. "Esfuerzo" es lo que cuesta ponerlo a facturar.

| # | Objetivo | Vía de monetización | Por qué ahora | Esfuerzo |
|---|---|---|---|---|
| 1 | **Alta de mootle en Awin** | Red (abre Línea Directa + más) | Llave maestra: un alta desbloquea el lead de seguros mejor pagado | Bajo (1 alta + depósito 5 $) |
| 2 | **Línea Directa (seguros)** vía Awin | CPL ~8 €/lead | Ya la listamos en `/seguros`; solo falta el enlace de afiliado | Bajo (solicitar anunciante + cablear 1 enlace) |
| 3 | **Rastreator (seguros)** | CPL alto | Contacto directo conocido; comparador = lead de alto valor | Bajo (1 correo) |
| 4 | **outletmotard** (equipación) | Shopify feed + afiliación directa | Scrapeable **ya** como fuente aunque no haya acuerdo; 1.000 productos Alpinestars | Bajo-medio (1 correo + integrar feed) |
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

1. **¿Damos de alta mootle en Awin?** (incluye depósito reembolsable de ~5 $ y aceptar
   términos — esto lo haces tú, yo te guío paso a paso). Es el paso que más desbloquea.
2. **¿Email de contacto público de mootle** para la correspondencia de afiliación?
   (p. ej. `info@mootle.es`). Los borradores llevan un hueco `[email de contacto]`.
3. **¿Enviamos ya** los borradores a outletmotard y a Rastreator, y reactivamos los de
   Máximo/Albabike? (Los redacto/actualizo yo; los envías tú.)
4. **outletmotard**: ¿quieres que prepare ya la integración como fuente Shopify
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
