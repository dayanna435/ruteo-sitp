"""
Pruebas del motor de búsqueda heurística A* (motor_busqueda.py).

La red real tiene ~8 000 paraderos, así que en lugar de probar todas las
parejas se usa una muestra determinista y un Dijkstra de referencia sobre el
mismo espacio de estados.
"""

import heapq
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import reglas  # noqa: E402
from hechos import PARADEROS, TIEMPO_ENTRE_PARADEROS, VELOCIDAD_PROMEDIO_KM_MIN  # noqa: E402
from motor_busqueda import buscar_ruta, distancia_km, heuristica  # noqa: E402
from reglas import GRAFO, regla_costo_movimiento, regla_meta  # noqa: E402

IDS = sorted(PARADEROS)
RNG = random.Random(2026)
MUESTRA = [RNG.sample(IDS, 2) for _ in range(12)]


def tiempo_optimo(origen, destino, grafo=None):
    """
    Dijkstra de referencia sobre el mismo espacio de estados que usa A*:
    el estado es la pareja (paradero, ruta_actual), no el paradero solo.
    """
    grafo = GRAFO if grafo is None else grafo
    inicio = (origen, None)
    mejores = {inicio: 0.0}
    frontera = [(0.0, inicio)]
    while frontera:
        g, estado = heapq.heappop(frontera)
        if mejores.get(estado, float("inf")) < g:
            continue
        if regla_meta(estado[0], destino):
            return g
        for vecino, ruta, tiempo in grafo.get(estado[0], []):
            costo, _ = regla_costo_movimiento(estado[1], ruta, tiempo)
            nuevo_g = g + costo
            nuevo_estado = (vecino, ruta)
            if nuevo_g < mejores.get(nuevo_estado, float("inf")):
                mejores[nuevo_estado] = nuevo_g
                heapq.heappush(frontera, (nuevo_g, nuevo_estado))
    return None


class TestContratoDeLaAPI(unittest.TestCase):
    def test_paradero_inexistente_devuelve_none(self):
        self.assertIsNone(buscar_ruta("inventado", IDS[0]))
        self.assertIsNone(buscar_ruta(IDS[0], "inventado"))

    def test_mismo_origen_y_destino(self):
        resultado = buscar_ruta(IDS[0], IDS[0])
        self.assertTrue(resultado["encontrada"])
        self.assertEqual(resultado["pasos"], [])
        self.assertEqual(resultado["tiempo_total"], 0.0)

    def test_todo_paradero_tiene_ruta_hacia_si_mismo(self):
        for id_paradero in RNG.sample(IDS, 50):
            self.assertTrue(buscar_ruta(id_paradero, id_paradero)["encontrada"])


class TestCamino(unittest.TestCase):
    """El camino devuelto debe ser una cadena válida y coherente con el total."""

    def recorrer_muestras(self):
        for origen, destino in MUESTRA:
            resultado = buscar_ruta(origen, destino)
            if resultado["encontrada"] and resultado["pasos"]:
                yield origen, destino, resultado

    def test_camino_empieza_y_termina_donde_debe(self):
        for origen, destino, resultado in self.recorrer_muestras():
            self.assertEqual(resultado["pasos"][0][0], origen)
            self.assertEqual(resultado["pasos"][-1][1], destino)

    def test_camino_es_continuo(self):
        for origen, destino, resultado in self.recorrer_muestras():
            for anterior, siguiente in zip(
                resultado["pasos"], resultado["pasos"][1:]
            ):
                self.assertEqual(anterior[1], siguiente[0])

    def test_los_costos_suman_el_total(self):
        for origen, destino, resultado in self.recorrer_muestras():
            suma = round(sum(paso[3] for paso in resultado["pasos"]), 1)
            self.assertEqual(suma, resultado["tiempo_total"])

    def test_el_costo_coincide_con_la_regla_de_transbordo(self):
        for origen, destino, resultado in self.recorrer_muestras():
            ruta_anterior = None
            for _, _, ruta, tiempo, hubo in resultado["pasos"]:
                esperado, esperado_flag = regla_costo_movimiento(
                    ruta_anterior, ruta, TIEMPO_ENTRE_PARADEROS
                )
                self.assertAlmostEqual(tiempo, esperado, places=6)
                self.assertEqual(hubo, esperado_flag)
                ruta_anterior = ruta

    def test_no_repite_estados(self):
        for origen, destino, resultado in self.recorrer_muestras():
            estados = [(origen, None)] + [(p[1], p[2]) for p in resultado["pasos"]]
            self.assertEqual(len(estados), len(set(estados)))


class TestOptimalidad(unittest.TestCase):
    """A* debe devolver el tiempo óptimo, nunca uno mejorable."""

    def test_muestras_contra_dijkstra(self):
        for origen, destino in MUESTRA:
            resultado = buscar_ruta(origen, destino)
            optimo = tiempo_optimo(origen, destino)
            self.assertEqual(
                resultado["encontrada"], optimo is not None,
                f"{origen} -> {destino}",
            )
            if optimo is not None:
                # buscar_ruta redondea el total a 1 decimal.
                self.assertAlmostEqual(
                    resultado["tiempo_total"], optimo, delta=0.05,
                    msg=f"{origen} -> {destino}",
                )


class TestGrafoInyectado(unittest.TestCase):
    """buscar_ruta debe poder trabajar sobre un grafo alternativo."""

    def test_usa_el_grafo_recibido(self):
        a, b = IDS[0], IDS[1]
        grafo = {a: [(b, "ruta_ficticia", 2.0)], b: []}
        resultado = buscar_ruta(a, b, grafo=grafo)
        self.assertEqual(resultado["tiempo_total"], 2.0)
        self.assertEqual(resultado["pasos"][0][2], "ruta_ficticia")

    def test_ve_un_reconstruir_grafo_sin_reiniciar(self):
        a, b = IDS[0], IDS[1]
        self.addCleanup(reglas.reconstruir_grafo)
        reglas.reconstruir_grafo(
            rutas={"r": [a, b]}, circulares=set(), tiempo_entre_paraderos=1.0
        )
        resultado = buscar_ruta(a, b)
        self.assertEqual(resultado["tiempo_total"], 1.0)


class TestDistanciaYHeuristica(unittest.TestCase):
    def test_distancia_consigo_mismo_es_cero(self):
        for id_paradero in RNG.sample(IDS, 50):
            self.assertEqual(distancia_km(id_paradero, id_paradero), 0.0)

    def test_distancia_es_simetrica_y_no_negativa(self):
        for a, b in MUESTRA:
            self.assertAlmostEqual(distancia_km(a, b), distancia_km(b, a), places=9)
            self.assertGreaterEqual(distancia_km(a, b), 0.0)

    def test_heuristica_nula_en_la_meta(self):
        for id_paradero in RNG.sample(IDS, 50):
            self.assertEqual(heuristica(id_paradero, id_paradero), 0.0)

    def test_heuristica_nunca_sobreestima_el_tramo(self):
        for origen, destino in MUESTRA:
            h = heuristica(origen, destino)
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, TIEMPO_ENTRE_PARADEROS + 1e-9)

    def test_velocidad_positiva_para_la_heuristica(self):
        self.assertGreater(VELOCIDAD_PROMEDIO_KM_MIN, 0.0)


if __name__ == "__main__":
    unittest.main()
