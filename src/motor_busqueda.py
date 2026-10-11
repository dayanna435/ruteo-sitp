"""
motor_busqueda.py
=================
Algoritmo de búsqueda heurística A* (capítulo 9 de Benítez) para encontrar el
trayecto de menor tiempo entre dos paraderos del SITP, sobre el grafo lógico
que construye `reglas.py` a partir de la base de conocimiento.

El "estado" de búsqueda es el par ``(paradero, ruta_actual)``, porque el costo
de un movimiento depende de si hay que transbordar o no (Regla 2). Por eso el
nodo del grafo de búsqueda no es un paradero sino una pareja.

Heurística
----------
h(n) estima el tiempo restante como la distancia en línea recta entre el
paradero actual y el destino, dividida por la velocidad comercial promedio, y
se **acota por el costo del tramo más barato**:

    h(n) = min(distancia_recta(n, meta) / velocidad, costo_tramo_minimo)

El acotamiento no es cosmético: con datos reales hay tramos troncales expresos
de más de 16 km que el modelo cobra como un único tramo, así que
``distancia / velocidad`` puede superarlos y h sobreestimaría el costo
restante, con lo que A* devolvería una ruta que no es la más rápida. Como todo
tramo cuesta al menos ``costo_tramo_minimo`` y desde un nodo que no es la meta
siempre falta al menos un tramo, h nunca sobreestima (es admisible) y además es
monótona (h(n) ≤ costo(n,n') + h(n')), condiciones que garantizan el óptimo.

Rendimiento
-----------
La búsqueda resuelve una consulta en un grafo de ~8 000 paraderos y ~62 000
arcos en milisegundos. Para lograrlo: (1) el grafo no se reconstruye por
consulta sino que se lee de `reglas.grafo_actual()`; (2) el camino no viaja en
la cola de prioridad —se reconstruye al final desde la tabla de antecesores—,
así que la memoria no crece con el largo de la ruta; (3) los estados ya
superados se descartan comparando contra el mejor costo conocido.
"""

import heapq
import math

from hechos import PARADEROS, TIEMPO_ENTRE_PARADEROS, VELOCIDAD_PROMEDIO_KM_MIN
from reglas import grafo_actual, regla_costo_movimiento, regla_meta

RADIO_TIERRA_KM = 6371.0088


def distancia_km(id_a, id_b):
    """Distancia aproximada entre dos paraderos, en línea recta (haversine, km)."""
    _, lat1, lon1 = PARADEROS[id_a]
    _, lat2, lon2 = PARADEROS[id_b]
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    h = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(min(1.0, h)))


def heuristica(paradero_actual, destino, costo_tramo_minimo=None):
    """
    h(n): tiempo estimado (minutos) restante hasta el destino.

    Es admisible y monótona; ver el docstring del módulo para el porqué del
    acotamiento por `costo_tramo_minimo`.
    """
    if paradero_actual == destino:
        return 0.0
    if costo_tramo_minimo is None:
        costo_tramo_minimo = TIEMPO_ENTRE_PARADEROS
    return min(
        distancia_km(paradero_actual, destino) / VELOCIDAD_PROMEDIO_KM_MIN,
        costo_tramo_minimo,
    )


def _reconstruir_camino(estado_final, estado_inicial, antecesores):
    """
    Reconstruye la lista de pasos desde la tabla de antecesores.

    Returns:
        list: [(paradero_desde, paradero_hasta, ruta, tiempo_tramo,
                hubo_transbordo), ...] en orden de recorrido.
    """
    pasos = []
    estado = estado_final
    while estado != estado_inicial:
        anterior, movimiento = antecesores[estado]
        pasos.append(movimiento)
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

    Returns:
        - None si origen o destino no existen en la base de conocimiento.
        - dict con:
            "encontrada": bool
            "pasos": lista de tramos [(paradero_desde, paradero_hasta, ruta,
                     tiempo_tramo, hubo_transbordo), ...]
            "tiempo_total": float (minutos) o None si no se encontró ruta.
            "tramos": int
            "transbordos": int
    """
    if origen not in PARADEROS or destino not in PARADEROS:
        return None

    if origen == destino:
        return {
            "encontrada": True,
            "pasos": [],
            "tiempo_total": 0.0,
            "tramos": 0,
            "transbordos": 0,
        }

    if grafo is None:
        grafo = grafo_actual()
    if costo_tramo_minimo is None:
        costo_tramo_minimo = TIEMPO_ENTRE_PARADEROS

    estado_inicial = (origen, None)

    # Cola de prioridad: (f(n), contador, g(n), estado). El contador desempata
    # de forma determinista cuando dos estados tienen el mismo f.
    contador = 0
    frontera = [(heuristica(origen, destino, costo_tramo_minimo), 0, 0.0, estado_inicial)]
    mejor_g = {estado_inicial: 0.0}
    # {estado: (estado_anterior, (desde, hasta, ruta, tiempo, hubo_transbordo))}
    antecesores = {}

    # Enlaces locales: el bucle de A* es el punto caliente de la aplicación.
    heappop = heapq.heappop
    heappush = heapq.heappush
    h = heuristica

    while frontera:
        _, _, g, estado = heappop(frontera)
        if g > mejor_g.get(estado, math.inf):
            continue  # entrada obsoleta, superada por una mejor ya explorada

        paradero_actual, ruta_actual = estado
        if regla_meta(paradero_actual, destino):
            pasos = _reconstruir_camino(estado, estado_inicial, antecesores)
            transbordos = sum(1 for paso in pasos if paso[4])
            return {
                "encontrada": True,
                "pasos": pasos,
                "tiempo_total": round(g, 1),
                "tramos": len(pasos),
                "transbordos": transbordos,
            }

        for vecino, ruta_vecina, tiempo_base in grafo.get(paradero_actual, ()):
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
            heappush(
                frontera,
                (nuevo_g + h(vecino, destino, costo_tramo_minimo), contador, nuevo_g, nuevo_estado),
            )

    return {
        "encontrada": False,
        "pasos": [],
        "tiempo_total": None,
        "tramos": 0,
        "transbordos": 0,
    }
