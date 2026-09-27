"""
motor_busqueda.py
==================
Implementa el algoritmo de búsqueda heurística A* (capítulo 9 de Benítez)
para encontrar la ruta de menor tiempo entre dos paraderos del SITP, usando
el grafo lógico generado por reglas.py a partir de la base de conocimiento.

El "estado" de búsqueda es el par (paradero, ruta_actual), porque el costo
de un movimiento depende de si se debe hacer transbordo o no (Regla 2). Por
eso el nodo del grafo de búsqueda no es un paradero sino una pareja.

Heurística
----------
h(n) estima el tiempo restante como la distancia en línea recta entre el
paradero actual y el destino, dividida por la velocidad comercial promedio
del sistema, y se **acota por el costo del tramo más barato**:

    h(n) = min(distancia_recta(n, meta) / velocidad, costo_tramo_minimo)

El acotamiento no es un detalle cosmético: con los datos actuales hay saltos
de hasta 7.18 km (CAN -> Biblioteca El Tintal) que la base de conocimiento
cobra como un solo tramo de 3.0 minutos, así que la distancia en línea recta
puede valer más que el tramo real y h sobreestimaría el costo restante, lo
que puede hacer que A* devuelva una ruta que no es la más rápida.

Como todo tramo cuesta al menos `costo_tramo_minimo`, y desde un nodo que no
es la meta siempre falta al menos un tramo por recorrer, h nunca sobreestima:
la heurística es admisible. Además es monótona (h(n) ≤ costo(n,n') + h(n')),
porque h está acotada por arriba y cada tramo vale al menos `costo_tramo_minimo`.
"""

import heapq
import math

from hechos import PARADEROS, TIEMPO_ENTRE_PARADEROS, VELOCIDAD_PROMEDIO_KM_MIN
from reglas import grafo_actual, regla_costo_movimiento, regla_meta

RADIO_TIERRA_KM = 6371.0088


def distancia_km(id_a, id_b):
    """Distancia aproximada entre dos paraderos, en línea recta (km, fórmula del haversine)."""
    _, lat1, lon1 = PARADEROS[id_a]
    _, lat2, lon2 = PARADEROS[id_b]
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    h = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(min(1.0, h)))


def heuristica(paradero_actual, destino, costo_tramo_minimo=None):
    """
    h(n): tiempo estimado (minutos) restante hasta el destino.

    Es admisible y monótona; ver el docstring del módulo para el porqué del
    acotamiento por `costo_tramo_minimo`.
    """
    if costo_tramo_minimo is None:
        costo_tramo_minimo = TIEMPO_ENTRE_PARADEROS
    if paradero_actual == destino:
        return 0.0
    return min(
        distancia_km(paradero_actual, destino) / VELOCIDAD_PROMEDIO_KM_MIN,
        costo_tramo_minimo,
    )


def _reconstruir_camino(origen, destino, estado_final, antecesores):
    """
    Reconstruye la lista de pasos a partir de la tabla de antecesores.

    Returns:
        list: [(paradero_desde, paradero_hasta, ruta, tiempo_tramo,
                hubo_transbordo), ...] en orden de recorrido.
    """
    pasos = []
    estado = estado_final
    while estado != (origen, None):
        anterior, movimiento = antecesores[estado]
        _, hasta, ruta, tiempo, hubo_transbordo = movimiento
        pasos.append((anterior[0], hasta, ruta, tiempo, hubo_transbordo))
        estado = anterior
    pasos.reverse()
    return pasos


def buscar_ruta(origen, destino, grafo=None, costo_tramo_minimo=None):
    """
    Ejecuta A* sobre el grafo lógico.

    Args:
        origen:  id del paradero de partida.
        destino: id del paradero de llegada.
        grafo: grafo lógico a explorar. Si es None se usa el vigente en
               reglas.py, leído en el momento de la llamada (por eso no se
               importa GRAFO directamente: un `reconstruir_grafo` se refleja
               aquí sin reiniciar el proceso).
        costo_tramo_minimo: cota inferior del costo de un tramo, usada para
               acotar la heurística. Si es None se usa TIEMPO_ENTRE_PARADEROS.

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

    if grafo is None:
        grafo = grafo_actual()
    if costo_tramo_minimo is None:
        costo_tramo_minimo = TIEMPO_ENTRE_PARADEROS

    # Estado = (paradero, ruta_actual). ruta_actual=None al iniciar.
    estado_inicial = (origen, None)
    if origen == destino:
        return {"encontrada": True, "pasos": [], "tiempo_total": 0.0}

    # Cola de prioridad: (f(n), contador, g(n), estado). El camino NO viaja en
    # la cola: se reconstruye al final desde `antecesores`, porque antes cada
    # entrada cargaba una copia del camino completo y el consumo de memoria
    # crecía con el tamaño de la ruta.
    contador = 0
    g_inicial = heuristica(origen, destino, costo_tramo_minimo)
    frontera = [(g_inicial, contador, 0.0, estado_inicial)]
    mejor_g = {estado_inicial: 0.0}
    # {estado: (estado_anterior, (desde, hasta, ruta, tiempo, hubo_transbordo))}
    antecesores = {}

    while frontera:
        _, _, g, estado = heapq.heappop(frontera)
        paradero_actual, ruta_actual = estado

        if g > mejor_g.get(estado, math.inf):
            continue  # entrada obsoleta, superada por una mejor ya explorada

        if regla_meta(paradero_actual, destino):
            return {
                "encontrada": True,
                "pasos": _reconstruir_camino(origen, destino, estado, antecesores),
                "tiempo_total": round(g, 1),
            }

        for vecino, ruta_vecina, tiempo_base in grafo.get(paradero_actual, []):
            costo_movimiento, hubo_transbordo = regla_costo_movimiento(
                ruta_actual, ruta_vecina, tiempo_base
            )
            nuevo_g = g + costo_movimiento
            nuevo_estado = (vecino, ruta_vecina)

            if nuevo_g >= mejor_g.get(nuevo_estado, math.inf):
                continue

            mejor_g[nuevo_estado] = nuevo_g
            antecesores[nuevo_estado] = (
                estado,
                (paradero_actual, vecino, ruta_vecina, costo_movimiento, hubo_transbordo),
            )
            contador += 1
            nuevo_f = nuevo_g + heuristica(vecino, destino, costo_tramo_minimo)
            heapq.heappush(frontera, (nuevo_f, contador, nuevo_g, nuevo_estado))

    return {"encontrada": False, "pasos": [], "tiempo_total": None}
