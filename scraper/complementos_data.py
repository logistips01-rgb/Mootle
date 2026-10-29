"""Datos curados para las comparativas de seguros y financiación (monetización).

OJO: son datos ORIENTATIVOS recopilados de fuentes públicas, con fecha. No son ofertas
ni cotizaciones. Hay que revisarlos de vez en cuando (los tipos y precios cambian).
Para actualizar: cambia las cifras aquí y vuelve a generar las páginas.
"""

FECHA_DATOS = "29 de octubre de 2026"

# "desde" orientativo que se muestra en la ficha de cada moto.
SEGURO_DESDE = "~7 €/mes"          # terceros, perfil medio (Mapfre 66€/año oficial, Qualitas 79,65€)
FINANCIACION_EJEMPLO_TIN = 8.95     # % TIN de ejemplo para la cuota por moto (CaixaBank ~9% oficial)
FINANCIACION_EJEMPLO_MESES = 60

# fuente: "oficial" = web de la propia empresa · "comparador" = agregadores (a verificar)
ASEGURADORAS = [
    {"nombre": "Mapfre", "desde": "66 €/año", "fuente": "oficial",
     "cobertura": "Terceros · Ampliado · Todo riesgo", "nota": "RC hasta 50M€, asistencia desde km 0",
     "url": "https://www.mapfre.es/particulares/seguros-para-motos/"},
    {"nombre": "Qualitas Auto", "desde": "79,65 €/año", "fuente": "comparador",
     "cobertura": "Terceros · Ampliado · Todo riesgo", "nota": "De las más baratas en terceros",
     "url": "https://www.qualitasauto.com/"},
    {"nombre": "AMV", "desde": "108 €/año", "fuente": "comparador",
     "cobertura": "Terceros · Ampliado · Todo riesgo", "nota": "Correduría especialista en moto (125cc)",
     "url": "https://www.amvseguros.com/"},
    {"nombre": "Verti", "desde": "118 €/año", "fuente": "comparador",
     "cobertura": "Terceros (3 niveles) · Todo riesgo", "nota": "Grupo Mapfre; descuento por anticipación",
     "url": "https://www.verti.es/"},
    {"nombre": "Línea Directa", "desde": "127 €/año", "fuente": "comparador",
     "cobertura": "Terceros · Ampliado · Todo riesgo", "nota": "Venta directa (no en comparadores)",
     "url": "https://www.lineadirecta.com/"},
    {"nombre": "Balumba", "desde": "~83 €/año", "fuente": "comparador",
     "cobertura": "Terceros · Ampliado · Todo riesgo", "nota": "Según modelo y ciudad",
     "url": "https://www.balumba.es/"},
    {"nombre": "Helvetia", "desde": "40 €/año", "fuente": "oficial",
     "cobertura": "Clásicas (moto de 25+ años)", "nota": "Precio solo para moto clásica",
     "url": "https://www.helvetia.es/"},
    {"nombre": "Pont Grup", "desde": "Presupuesto", "fuente": "comparador",
     "cobertura": "Multirriesgo (varias aseguradoras)", "nota": "Nº1 en calidad/servicio (ranking 2025-2026)",
     "url": "https://www.pont-grup.com/"},
]

FINANCIERAS = [
    {"nombre": "Cofidis — Crédito Proyecto Moto", "tae": "desde ~6,95 % TAE", "fuente": "comparador",
     "plazo": "12–84 meses", "importe": "6.000–60.000 €", "nota": "Producto específico de moto, sin comisión de apertura",
     "url": "https://www.cofidis.es/"},
    {"nombre": "Younited Credit", "tae": "desde ~2,99 % TAE", "fuente": "comparador (a verificar)",
     "plazo": "hasta 84 meses", "importe": "1.000–50.000 €", "nota": "Préstamo personal; cifra de comparador pendiente de confirmar",
     "url": "https://www.younited.com/es/"},
    {"nombre": "N26", "tae": "desde ~4,06 % TAE", "fuente": "comparador",
     "plazo": "hasta 60 meses", "importe": "1.000–25.000 €", "nota": "Préstamo personal 100% online",
     "url": "https://n26.com/es-es"},
    {"nombre": "Cetelem", "tae": "desde ~8,3 % TAE", "fuente": "comparador",
     "plazo": "hasta 96 meses", "importe": "hasta 60.000 €", "nota": "Cualquier vehículo, nuevo o usado",
     "url": "https://www.cetelem.es/"},
    {"nombre": "CaixaBank — Préstamo Auto", "tae": "9,38 % TAE", "fuente": "oficial",
     "plazo": "hasta 72 meses", "importe": "2.000–30.000 €", "nota": "Incluye vehículo de ocasión (ejemplo oficial)",
     "url": "https://www.caixabank.es/particular/prestamos-personales/prestamo-auto-para-coche-moto.html"},
]
