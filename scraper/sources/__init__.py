"""Registro de fuentes. Para añadir una web: un módulo con ID, NAME, HOME y
scrape(fetcher, known, state, deadline, current_year, log) → (anuncios, info), y añadirlo aquí."""
from . import maquinamotors, motoocasion, motosnet

SOURCES = {s.ID: s for s in (motosnet, motoocasion, maquinamotors)}
