# -*- coding: utf-8 -*-
"""
hechos.py
=========
Base de conocimiento del Sistema Integrado de Transporte Público (SITP) de
Bogotá — componente zonal (buses urbanos, alimentadores y complementarios).

Los hechos se representan como predicados lógicos (capítulo 2 de Benítez):

    paradero(Id, Nombre, Latitud, Longitud).
    circula(ParaderoA, ParaderoB, Ruta, TiempoMinutos).

FUENTE DE LOS DATOS:
Los códigos de ruta, el trazado (secuencia de barrios/paraderos) y el
sentido de las rutas urbanas 14 y C11, y de la ruta complementaria 18-8,
corresponden a información pública divulgada por la Alcaldía de Bogotá /
Secretaría Distrital de Movilidad (bogota.gov.co, sección Movilidad -
"Nuevas rutas ingresan al SITP"). Las coordenadas de cada paradero son
APROXIMADAS (ubicación general del barrio/cruce, no el poste exacto).

Para la entrega final, el equipo debe reemplazar estas coordenadas
aproximadas por las coordenadas exactas de los paraderos oficiales,
disponibles en los datasets abiertos de TransMilenio S.A.:
  - "Rutas Zonales SITP":
    https://datosabiertos-transmilenio.hub.arcgis.com/datasets/rutas-zonales-sitp
  - "Paraderos Zonales del SITP":
    https://datosabiertos-transmilenio.hub.arcgis.com/datasets/paraderos-zonales-del-sitp
  - Dataset "Paraderos SITP" en datos.gov.co:
    https://www.datos.gov.co/d/etwh-dt2e
"""

# ---------------------------------------------------------------------------
# Predicado: paradero(Id, Nombre, Latitud, Longitud)
# ---------------------------------------------------------------------------
PARADEROS = {
    # --- Ruta Urbana 14: Chapinero Central - Portal de las Américas ---
    "chapinero_central":  ("Chapinero Central",        4.6480, -74.0620),
    "can":                ("CAN",                      4.6484, -74.0932),
    "biblioteca_tintal":  ("Biblioteca El Tintal",      4.6296, -74.1553),
    "portal_americas":    ("Portal de las Américas",    4.6280, -74.1660),

    # --- Ruta C11: Villa del Río - Porciúncula (comparte "El Campín") ---
    "univ_pedagogica":    ("Universidad Pedagógica",    4.6570, -74.0630),
    "el_campin":          ("Estadio El Campín",         4.6486, -74.0776),  # Paradero de transbordo (14 y C11)
    "galerias":           ("Galerías",                  4.6500, -74.0700),
    "univ_nacional":      ("Universidad Nacional",      4.6380, -74.0840),
    "salitre":            ("Salitre",                   4.6470, -74.1020),
    "estadio_techo":      ("Estadio de Techo",          4.6300, -74.1460),
    "hospital_kennedy":   ("Hospital de Kennedy",       4.6280, -74.1560),
    "villa_del_rio":      ("Villa del Río",             4.6150, -74.1450),

    # --- Ruta Complementaria 18-8: Bosque Calderón (circular, Chapinero) ---
    # Paraderos oficiales publicados como direcciones (cruces de calles/carreras);
    # NO tiene conexión física con las rutas anteriores (útil como caso de
    # prueba de "no existe ruta" o de una ruta aislada de la zona Chapinero).
    "dg57_tv4e":          ("Dg 57 - Tv 4 Este",         4.6465, -74.0605),
    "cl60a_kr3a":         ("Cl 60A - Kr 3A",            4.6478, -74.0615),
    "kr4_cl58bis":        ("Kr 4 - Cl 58 Bis",          4.6455, -74.0600),
    "kr4_cl59a":          ("Kr 4 - Cl 59A",             4.6462, -74.0598),
    "cl53_kr4":           ("Cl 53 - Kr 4",              4.6400, -74.0605),
    "cl54_kr6":           ("Cl 54 - Kr 6",              4.6410, -74.0630),
    "ac53_kr3":           ("AC 53 - Kr 3",              4.6398, -74.0590),
    "ac60bis_tv1a":       ("AC 60 Bis x Tv 1A",         4.6480, -74.0590),
    "dg57_tv2e":          ("Dg 57 - Tv 2 Este",         4.6468, -74.0585),
}

# ---------------------------------------------------------------------------
# Predicado: circula(ParaderoA, ParaderoB, Ruta, TiempoMinutos)
# Cada ruta se define como la secuencia ordenada de paraderos de su trazado
# real; el hecho "circula" se genera entre paraderos consecutivos
# (ver regla_generar_conexiones en reglas.py). Se asume viaje bidireccional,
# salvo la ruta 18-8 que es circular (un solo sentido).
# ---------------------------------------------------------------------------
RUTAS = {
    # Real: Chapinero Central -> ... -> Portal de las Américas (Kennedy)
    "urbana_14": [
        "chapinero_central", "el_campin", "can", "biblioteca_tintal", "portal_americas",
    ],
    # Real: Bosa - Zona Neutra (Villa del Río - Porciúncula), pasa por El Campín
    "c11": [
        "univ_pedagogica", "chapinero_central", "el_campin", "galerias",
        "univ_nacional", "salitre", "estadio_techo", "hospital_kennedy", "villa_del_rio",
    ],
    # Real: ruta complementaria circular en Chapinero (sin conexión con las anteriores)
    "complementaria_18_8": [
        "dg57_tv4e", "cl60a_kr3a", "kr4_cl58bis", "kr4_cl59a", "cl53_kr4",
        "cl54_kr6", "ac53_kr3", "ac60bis_tv1a", "dg57_tv2e",
    ],
}

# Rutas que operan en un solo sentido (circulares); todas las demás se
# tratan como bidireccionales en reglas.py.
RUTAS_CIRCULARES = {"complementaria_18_8"}

# Tiempo promedio (minutos) entre paraderos consecutivos de una misma ruta.
# En un sistema real este valor debería salir de datos reales por tramo
# (distancia y velocidad comercial del bus).
TIEMPO_ENTRE_PARADEROS = 3.0

# Tiempo de penalización (minutos) por cada transbordo (cambio de ruta/bus),
# que representa el tiempo de caminar y esperar el siguiente bus.
TIEMPO_TRANSBORDO = 8.0

# Velocidad comercial promedio aproximada de un bus del SITP zonal (km/min),
# usada para la heurística del algoritmo A* (capítulo 9: búsquedas heurísticas).
VELOCIDAD_PROMEDIO_KM_MIN = 0.30
