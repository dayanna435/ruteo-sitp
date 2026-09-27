# -*- coding: utf-8 -*-
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

from hechos import RUTAS, RUTAS_CIRCULARES, TIEMPO_ENTRE_PARADEROS, TIEMPO_TRANSBORDO


def regla_generar_conexiones():
    """
    Aplica la Regla 1 sobre la base de conocimiento: recorre cada ruta y
    genera el predicado circula(A, B, Ruta, Tiempo) entre paraderos
    consecutivos. Las rutas normales son bidireccionales; las rutas
    circulares (RUTAS_CIRCULARES) solo se recorren en el sentido publicado.

    Retorna:
        dict: { paradero_id: [ (paradero_vecino, ruta, tiempo), ... ] }
    """
    grafo = {}

    def agregar_arco(origen, destino, ruta, tiempo):
        grafo.setdefault(origen, []).append((destino, ruta, tiempo))

    for ruta, paraderos in RUTAS.items():
        es_circular = ruta in RUTAS_CIRCULARES
        n = len(paraderos)
        pares = zip(paraderos, paraderos[1:])
        for a, b in pares:
            agregar_arco(a, b, ruta, TIEMPO_ENTRE_PARADEROS)
            if not es_circular:
                agregar_arco(b, a, ruta, TIEMPO_ENTRE_PARADEROS)
        if es_circular and n > 2:
            # Cierra el ciclo: del último paradero de vuelta al primero.
            agregar_arco(paraderos[-1], paraderos[0], ruta, TIEMPO_ENTRE_PARADEROS)

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


# Grafo lógico derivado de los hechos; se calcula una sola vez al importar.
GRAFO = regla_generar_conexiones()
