"""
reglas.py
=========
Sistema basado en reglas (capítulo 3 de Benítez) que infiere, a partir de
los hechos declarados en hechos.py, todos los movimientos posibles dentro
de la red de rutas del SITP.

Regla 1 (circulación directa):
    SI existe circula(A, B, Ruta, Tiempo)
    ENTONCES desde A se puede llegar a B usando Ruta en Tiempo minutos.
    (Las rutas normales son bidireccionales; las rutas circulares —ver
    RUTAS_CIRCULARES— solo se recorren en el sentido publicado).

Regla 2 (transbordo):
    SI el estado actual usa la Ruta_actual
    Y el siguiente movimiento usa una Ruta_nueva
    Y Ruta_actual != Ruta_nueva
    ENTONCES sumar TIEMPO_TRANSBORDO al costo del movimiento (bajarse de un
    bus y esperar el siguiente).

Regla 3 (meta):
    SI el paradero actual es igual al paradero destino
    ENTONCES la ruta ha llegado a su meta.

El motor construye una tabla de adyacencia (grafo lógico) que representa
todos los hechos "circula" derivados, para que el motor de búsqueda
(motor_busqueda.py) explore sobre ella.
"""

from hechos import (
    RUTAS,
    RUTAS_CIRCULARES,
    TIEMPO_ENTRE_PARADEROS,
    TIEMPO_TRANSBORDO,
)

# Número mínimo de paraderos para que una ruta circular pueda cerrarse sin
# repetir arcos: con 1 no hay ciclo y con 2 el arco de cierre duplicaría el
# arco directo ya generado.
MIN_PARADEROS_RUTA_CIRCULAR = 3


def regla_generar_conexiones(
    rutas=None,
    circulares=None,
    tiempo_entre_paraderos=None,
):
    """
    Aplica la Regla 1 sobre la base de conocimiento: recorre cada ruta y
    genera el predicado circula(A, B, Ruta, Tiempo) entre paraderos
    consecutivos. Las rutas normales son bidireccionales; las rutas
    circulares (RUTAS_CIRCULARES) solo se recorren en el sentido publicado.

    La función es pura: no lee estado global. Los parámetros `None` significan
    "usar el valor de la base de conocimiento" (hechos.py), lo que permite
    construir grafos alternativos para pruebas sin mutar los hechos.

    Args:
        rutas: {id_ruta: [id_paradero, ...]}. Por defecto, RUTAS.
        circulares: ids de rutas unidireccionales. Por defecto, RUTAS_CIRCULARES.
        tiempo_entre_paraderos: costo de cada tramo. Por defecto,
            TIEMPO_ENTRE_PARADEROS.

    Returns:
        dict: { paradero_id: [ (paradero_vecino, ruta, tiempo), ... ] }
    """
    rutas = RUTAS if rutas is None else rutas
    circulares = RUTAS_CIRCULARES if circulares is None else circulares
    tiempo = (
        TIEMPO_ENTRE_PARADEROS
        if tiempo_entre_paraderos is None
        else tiempo_entre_paraderos
    )

    grafo = {}

    def agregar_arco(origen, destino, ruta, tiempo):
        grafo.setdefault(origen, []).append((destino, ruta, tiempo))

    for ruta, paraderos in rutas.items():
        es_circular = ruta in circulares
        n = len(paraderos)
        for a, b in zip(paraderos, paraderos[1:]):
            agregar_arco(a, b, ruta, tiempo)
            if not es_circular:
                agregar_arco(b, a, ruta, tiempo)
        if es_circular and n >= MIN_PARADEROS_RUTA_CIRCULAR:
            # Cierra el ciclo: del último paradero de vuelta al primero.
            agregar_arco(paraderos[-1], paraderos[0], ruta, tiempo)

    return grafo


def regla_costo_movimiento(ruta_actual, ruta_nueva, tiempo_base):
    """
    Aplica la Regla 2 (transbordo): si la ruta cambia respecto al estado
    anterior, se penaliza el movimiento con TIEMPO_TRANSBORDO adicional.

    Args:
        ruta_actual: ruta con la que se llegó al estado actual (o None si
                     es el punto de partida).
        ruta_nueva:  ruta que se usaría para el siguiente movimiento.
        tiempo_base: tiempo de viaje entre los dos paraderos.

    Retorna:
        (costo_total, hubo_transbordo: bool)
    """
    if ruta_actual is not None and ruta_actual != ruta_nueva:
        return tiempo_base + TIEMPO_TRANSBORDO, True
    return tiempo_base, False


def regla_meta(paradero_actual, paradero_destino):
    """Regla 3: determina si se alcanzó el destino."""
    return paradero_actual == paradero_destino


# Grafo lógico derivado de los hechos. Se calcula una sola vez al importar el
# módulo para que el resto del sistema no lo repita en cada consulta.
GRAFO = regla_generar_conexiones()


def grafo_actual():
    """
    Devuelve el grafo lógico vigente.

    Se consulta por indirección (y no importando GRAFO directamente) para que
    una llamada a `reconstruir_grafo` se refleje en los módulos que ya están
    importados.
    """
    return GRAFO


def reconstruir_grafo(rutas=None, circulares=None, tiempo_entre_paraderos=None):
    """
    Vuelve a derivar el grafo lógico y reemplaza el global `GRAFO`.

    Útil en pruebas o después de editar los hechos en caliente, sin tener que
    reiniciar el proceso. Devuelve el grafo nuevo.

    Returns:
        dict: el grafo que quedó activo.
    """
    global GRAFO
    GRAFO = regla_generar_conexiones(
        rutas=rutas,
        circulares=circulares,
        tiempo_entre_paraderos=tiempo_entre_paraderos,
    )
    return GRAFO
