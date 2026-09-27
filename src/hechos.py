"""
hechos.py
=========
Base de conocimiento del Sistema Integrado de Transporte Público (SITP) de Bogotá — componente zonal (buses urbanos, alimentadores y complementarios).

Los hechos se representan como predicados lógicos (capítulo 2 de Benítez):

    paradero(Id, Nombre, Latitud, Longitud).
    circula(ParaderoA, ParaderoB, Ruta, TiempoMinutos).

A diferencia de la primera versión del proyecto, los hechos NO están escritos a mano en este archivo: se cargan y validan desde `data/data.json` mediante `cargador_datos.py`. Este módulo sigue siendo la *interfaz* de la base de conocimiento para el resto del sistema (reglas, motor de búsqueda, CLI).

FUENTE DE LOS DATOS:
Los códigos de ruta, el trazado (secuencia de barrios/paraderos) y el sentido de las rutas urbanas 14 y C11, y de la ruta complementaria 18-8, corresponden a información pública divulgada por la Alcaldía de Bogotá / Secretaría Distrital de Movilidad (bogota.gov.co, sección Movilidad - "Nuevas rutas ingresan al SITP"). Las coordenadas de cada paradero son APROXIMADAS (ubicación general del barrio/cruce, no el poste exacto).

También se puede reemplazar estas coordenadas aproximadas por las coordenadas exactas de los paraderos oficiales, disponibles en los datasets abiertos de TransMilenio S.A.:
  - "Rutas Zonales SITP":
    https://datosabiertos-transmilenio.hub.arcgis.com/datasets/rutas-zonales-sitp
  - "Paraderos Zonales del SITP":
    https://datosabiertos-transmilenio.hub.arcgis.com/datasets/paraderos-zonales-del-sitp
  - Dataset "Paraderos SITP" en datos.gov.co:
    https://www.datos.gov.co/d/etwh-dt2e
"""

from cargador_datos import ErrorDatos, cargar_datos

# ---------------------------------------------------------------------------
# Predicado: paradero(Id, Nombre, Latitud, Longitud)
# ---------------------------------------------------------------------------

# Si el archivo de datos no existe o está mal formado se prefiere fallar aquí,
# al importar, con un mensaje explicativo, que fallar más adentro con un
# KeyError. Configura RUTEO_SITP_DATA para apuntar a otro archivo.
try:
    _DATOS = cargar_datos()
except ErrorDatos as _error:
    raise ImportError(
        f"No se pudo cargar la base de conocimiento del SITP: {_error}"
    ) from _error

# {id: (nombre, lat, lon)} — ver cargador_datos._cargar_paraderos
PARADEROS = _DATOS["paraderos"]

# ---------------------------------------------------------------------------
# Predicado: circula(ParaderoA, ParaderoB, Ruta, TiempoMinutos)
# Cada ruta se define como la secuencia ordenada de paraderos de su trazado
# real; el hecho "circula" se genera entre paraderos consecutivos
# (ver regla_generar_conexiones en reglas.py). Se asume viaje bidireccional,
# salvo las rutas circulares, que solo se recorren en un sentido.
# ---------------------------------------------------------------------------

# {id_ruta: [id_paradero, ...]}
RUTAS = _DATOS["rutas"]

# Rutas que operan en un solo sentido (circulares); todas las demás se
# tratan como bidireccionales en reglas.py.
RUTAS_CIRCULARES = _DATOS["rutas_circulares"]

# Tiempo promedio (minutos) entre paraderos consecutivos de una misma ruta.
# En un sistema real este valor debería salir de datos reales por tramo
# (distancia y velocidad comercial del bus).
TIEMPO_ENTRE_PARADEROS = _DATOS["constantes"]["tiempo_entre_paraderos"]

# Tiempo de penalización (minutos) por cada transbordo (cambio de ruta/bus),
# que representa el tiempo de caminar y esperar el siguiente bus.
TIEMPO_TRANSBORDO = _DATOS["constantes"]["tiempo_transbordo"]

# Velocidad comercial promedio aproximada de un bus del SITP zonal (km/min),
# usada para la heurística del algoritmo A* (capítulo 9: búsquedas heurísticas).
VELOCIDAD_PROMEDIO_KM_MIN = _DATOS["constantes"]["velocidad_promedio_km_min"]
