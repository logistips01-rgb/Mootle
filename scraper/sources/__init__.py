"""Registro de fuentes. Para añadir una web: un módulo con ID, NAME, HOME y
scrape(fetcher, known, state, deadline, current_year, log) → (anuncios, info), y añadirlo aquí."""
from . import box77, indalmar, maquinamotors, motoocasion, motosnet
from .shopify import SOURCES as SHOPIFY
from .woocommerce import SOURCES as WOO

SOURCES = {s.ID: s for s in (motosnet, motoocasion, maquinamotors, box77, indalmar, *WOO, *SHOPIFY)}
