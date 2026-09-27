# -*- coding: utf-8 -*-
"""
motor_busqueda.py
==================
Implementa el algoritmo de búsqueda heurística A* (capítulo 9 de Benítez)
para encontrar la ruta de menor tiempo entre dos paraderos del SITP, usando
el grafo lógico generado por reglas.py a partir de la base de conocimiento.

El "estado" de búsqueda es el par (paradero, ruta_actual), porque el costo
de un movimiento depende de si se debe hacer transbordo o no (Regla 2).

La heurística h(n) estima el tiempo restante como la distancia en línea
recta entre el paradero actual y el destino, dividida por la velocidad
comercial promedio del sistema. Esta heurística es admisible (nunca
sobreestima) porque la distancia real por las rutas siempre es mayor o
igual a la distancia en línea recta.
"""

import heapq
import math

from hechos import PARADEROS, VELOCIDAD_PROMEDIO_KM_MIN
from reglas import GRAFO, regla_costo_movimiento, regla_meta


def distancia_km(id_a, id_b):
    """Distancia aproximada en línea recta entre dos paraderos (km)."""
    _, lat1, lon1 = PARADEROS[id_a]
    _, lat2, lon2 = PARADEROS[id_b]
    # Aproximación simple: 1 grado ~ 111 km (suficiente para distancias cortas)
    dx = (lat1 - lat2) * 111.0
    dy = (lon1 - lon2) * 111.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.sqrt(dx ** 2 + dy ** 2)


def heuristica(paradero_actual, destino):
    """h(n): tiempo estimado (minutos) restante hasta el destino."""
    return distancia_km(paradero_actual, destino) / VELOCIDAD_PROMEDIO_KM_MIN


def buscar_ruta(origen, destino):
    """
    Ejecuta A* sobre el grafo lógico.

    Args:
        origen:  id del paradero de partida.
        destino: id del paradero de llegada.

    Retorna:
        - None si origen o destino no existen en la base de conocimiento.
        - dict con:
            "encontrada": bool
            "pasos": lista de tramos [(paradero_desde, paradero_hasta,
                       ruta, tiempo_tramo, hubo_transbordo), ...]
            "tiempo_total": float (minutos) o None si no se encontró ruta.
    """
    if origen not in PARADEROS or destino not in PARADEROS:
        return None

    # Estado = (paradero, ruta_actual). ruta_actual=None al iniciar.
    estado_inicial = (origen, None)

    # Cola de prioridad: (f(n), contador, g(n), estado, camino)
    contador = 0
    frontera = [(heuristica(origen, destino), contador, 0.0, estado_inicial, [])]
    visitados = {}

    while frontera:
        f, _, g, estado, camino = heapq.heappop(frontera)
        paradero_actual, ruta_actual = estado

        if regla_meta(paradero_actual, destino):
            return {
                "encontrada": True,
                "pasos": camino,
                "tiempo_total": round(g, 1),
            }

        if estado in visitados and visitados[estado] <= g:
            continue
        visitados[estado] = g

        for vecino, ruta_vecina, tiempo_base in GRAFO.get(paradero_actual, []):
            costo_movimiento, hubo_transbordo = regla_costo_movimiento(
                ruta_actual, ruta_vecina, tiempo_base
            )
            nuevo_g = g + costo_movimiento
            nuevo_estado = (vecino, ruta_vecina)

            if nuevo_estado in visitados and visitados[nuevo_estado] <= nuevo_g:
                continue

            nuevo_camino = camino + [
                (paradero_actual, vecino, ruta_vecina, costo_movimiento, hubo_transbordo)
            ]
            nuevo_f = nuevo_g + heuristica(vecino, destino)
            contador += 1
            heapq.heappush(frontera, (nuevo_f, contador, nuevo_g, nuevo_estado, nuevo_camino))

    return {"encontrada": False, "pasos": [], "tiempo_total": None}
