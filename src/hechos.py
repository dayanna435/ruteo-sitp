"""
hechos.py
=========
Base de conocimiento del Sistema Integrado de Transporte Público (SITP) de
Bogotá, cargada y validada desde los JSON optimizados de `data/output/`.

Los hechos se representan como predicados lógicos (capítulo 2 de Benítez):

    paradero(Id, Nombre, Latitud, Longitud).
    circula(ParaderoA, ParaderoB, Ruta, TiempoMinutos).

A diferencia de las primeras versiones del proyecto, los hechos NO están
escritos a mano: `pipeline_gtfs.py` aplana el feed GTFS oficial a
`data/output/` y `cargador_datos.py` los valida. Este módulo es la *interfaz*
de la base de conocimiento para el resto del sistema (reglas, motor, CLI):
todos importan de aquí y ninguno abre archivos.

FUENTE DE LOS DATOS:
Datos Abiertos GTFS Estáticos de TransMilenio S.A. (ver `data/gtfs/` y
`docs/pipeline_gtfs.md`). Las coordenadas son las oficiales del feed; las
secuencias de rutas son el viaje representativo (el de más paraderos) de cada
ruta, tal como se documenta en `pipeline_gtfs.py`.
"""

from cargador_datos import ErrorDatos, cargar_datos

# Si los datos no existen o están mal formados se prefiere fallar aquí, al
# importar, con un mensaje explicativo, que fallar más adentro con un KeyError.
# Configura RUTEO_SITP_DATA para apuntar a otro directorio o archivo.
try:
    _DATOS = cargar_datos()
except ErrorDatos as _error:
    raise ImportError(
        f"No se pudo cargar la base de conocimiento del SITP: {_error}"
    ) from _error

# ---------------------------------------------------------------------------
# Predicado: paradero(Id, Nombre, Latitud, Longitud).
# {id: (nombre, lat, lon)} — ver cargador_datos._cargar_paraderos
# ---------------------------------------------------------------------------
PARADEROS = _DATOS["paraderos"]

# Etiqueta de componente de cada paradero ("troncal" / "zonal"), para la CLI.
TIPOS_PARADEROS = _DATOS["tipos_paraderos"]

# ---------------------------------------------------------------------------
# Predicado: circula(ParaderoA, ParaderoB, Ruta, TiempoMinutos).
# Cada ruta es la secuencia ordenada de paraderos de su trazado; el hecho
# "circula" se genera entre paraderos consecutivos (ver reglas.py). Las rutas
# normales son bidireccionales; las circulares solo en el sentido publicado.
# {id_ruta: [id_paradero, ...]}
# ---------------------------------------------------------------------------
RUTAS = _DATOS["rutas"]

# Rutas que operan en un solo sentido (marcadas por el pipeline).
RUTAS_CIRCULARES = _DATOS["rutas_circulares"]

# Metadatos por ruta para la presentación de resultados:
# {id_ruta: {nombre_largo, tipo, dias_operacion, horario_inicio,
#            horario_fin, es_circular}}
INFO_RUTAS = _DATOS["info_rutas"]

# Tiempo promedio (minutos) entre paraderos consecutivos de una misma ruta.
TIEMPO_ENTRE_PARADEROS = _DATOS["constantes"]["tiempo_entre_paraderos"]

# Tiempo de penalización (minutos) por cada transbordo (cambio de ruta/bus).
TIEMPO_TRANSBORDO = _DATOS["constantes"]["tiempo_transbordo"]

# Velocidad comercial promedio aproximada del sistema, en km/min. Es la unidad
# que usa la heurística del algoritmo A* (capítulo 9: búsquedas heurísticas).
VELOCIDAD_PROMEDIO_KM_MIN = _DATOS["constantes"]["velocidad_promedio_km_min"]

# Velocidad comercial promedio en km/h, tal como viene del feed (para reportes).
VELOCIDAD_COMERCIAL_KMH = _DATOS["constantes"]["velocidad_comercial_promedio_kmh"]

# ---------------------------------------------------------------------------
# Flota asignada a rutas. El motor de ruteo NO lo usa (no hay frecuencia ni
# espera en el modelo de tiempos); se expone para que el componente de demanda
# pueda leerlo desde el mismo lugar. {id_ruta: {tipo_vehiculo, ...}}
# ---------------------------------------------------------------------------
BUSES = _DATOS["buses"]
