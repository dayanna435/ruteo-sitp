"""
Pruebas del motor de búsqueda heurística A* (motor_busqueda.py).
"""

import heapq
import itertools
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import reglas  # noqa: E402
from hechos import PARADEROS, TIEMPO_ENTRE_PARADEROS, VELOCIDAD_PROMEDIO_KM_MIN  # noqa: E402
from motor_busqueda import buscar_ruta, distancia_km, heuristica  # noqa: E402
from reglas import GRAFO, regla_costo_movimiento, regla_meta  # noqa: E402


def tiempo_optimo(origen, destino, grafo=None):
    """
    Dijkstra de referencia sobre el mismo espacio de estados que usa A*:
    el estado es la pareja (paradero, ruta_actual), no el paradero solo.
    """
    if grafo is None:
        grafo = GRAFO
    inicio = (origen, None)
    mejores = {inicio: 0.0}
    frontera = [(0.0, inicio)]
    while frontera:
        g, estado = heapq.heappop(frontera)
        if estado in mejores and mejores[estado] < g:
            continue
        if regla_meta(estado[0], destino):
            return g
        for vecino, ruta, tiempo in grafo.get(estado[0], []):
            costo, _ = regla_costo_movimiento(estado[1], ruta, tiempo)
            nuevo_g = g + costo
            nuevo_estado = (vecino, ruta)
            if nuevo_estado not in mejores or nuevo_g < mejores[nuevo_estado]:
                mejores[nuevo_estado] = nuevo_g
                heapq.heappush(frontera, (nuevo_g, nuevo_estado))
    return None


class TestResultadosConocidos(unittest.TestCase):
    """Resultados de referencia del enunciado y de los casos de demo."""

    def test_chapinero_a_portal_de_las_americas(self):
        resultado = buscar_ruta("chapinero_central", "portal_americas")
        self.assertTrue(resultado["encontrada"])
        self.assertEqual(resultado["tiempo_total"], 12.0)
        self.assertEqual(len(resultado["pasos"]), 4)
        self.assertFalse(any(paso[4] for paso in resultado["pasos"]))

    def test_ruta_con_un_transbordo(self):
        # Villa del Río -> CAN sale por c11 y pasa a urbana_14 en El Campín.
        resultado = buscar_ruta("villa_del_rio", "can")
        self.assertTrue(resultado["encontrada"])
        self.assertEqual(resultado["tiempo_total"], 29.0)
        transbordos = [paso for paso in resultado["pasos"] if paso[4]]
        self.assertEqual(len(transbordos), 1)
        self.assertEqual(transbordos[0][2], "urbana_14")

    def test_ruta_circular_unidireccional(self):
        resultado = buscar_ruta("cl54_kr6", "dg57_tv4e")
        self.assertTrue(resultado["encontrada"])
        for paso in resultado["pasos"]:
            self.assertEqual(paso[2], "complementaria_18_8")

    def test_sin_ruta_entre_redes_aisladas(self):
        # La 18-8 no tiene conexión física con la red 14/C11: es a propósito.
        resultado = buscar_ruta("dg57_tv4e", "can")
        self.assertFalse(resultado["encontrada"])
        self.assertEqual(resultado["pasos"], [])
        self.assertIsNone(resultado["tiempo_total"])


class TestContratoDeLaAPI(unittest.TestCase):
    """Contrato de retorno de buscar_ruta."""

    def test_paradero_inexistente_devuelve_none(self):
        self.assertIsNone(buscar_ruta("inventado", "can"))
        self.assertIsNone(buscar_ruta("can", "inventado"))
        self.assertIsNone(buscar_ruta("inventado", "tampoco"))

    def test_mismo_origen_y_destino(self):
        resultado = buscar_ruta("can", "can")
        self.assertTrue(resultado["encontrada"])
        self.assertEqual(resultado["pasos"], [])
        self.assertEqual(resultado["tiempo_total"], 0.0)

    def test_todo_paradero_tiene_ruta_hacia_si_mismo(self):
        for id_paradero in PARADEROS:
            resultado = buscar_ruta(id_paradero, id_paradero)
            self.assertTrue(resultado["encontrada"], id_paradero)


class TestCamino(unittest.TestCase):
    """El camino devuelto debe ser una cadena válida y coherente con el total."""

    def pares(self):
        return itertools.permutations(PARADEROS, 2)

    def test_camino_empieza_en_el_origen_y_termina_en_el_destino(self):
        for origen, destino in self.pares():
            resultado = buscar_ruta(origen, destino)
            if not resultado["encontrada"]:
                continue
            pasos = resultado["pasos"]
            self.assertEqual(pasos[0][0], origen, f"{origen} -> {destino}")
            self.assertEqual(pasos[-1][1], destino, f"{origen} -> {destino}")

    def test_camino_es_continuo(self):
        for origen, destino in self.pares():
            resultado = buscar_ruta(origen, destino)
            if not resultado["encontrada"]:
                continue
            for anterior, siguiente in zip(resultado["pasos"], resultado["pasos"][1:]):
                self.assertEqual(
                    anterior[1], siguiente[0], f"corte en {origen} -> {destino}"
                )

    def test_los_costos_suman_el_total(self):
        for origen, destino in self.pares():
            resultado = buscar_ruta(origen, destino)
            if not resultado["encontrada"]:
                continue
            suma = round(sum(paso[3] for paso in resultado["pasos"]), 1)
            self.assertEqual(suma, resultado["tiempo_total"], f"{origen} -> {destino}")

    def test_el_costo_de_cada_tramo_coincide_con_la_regla_de_transbordo(self):
        for origen, destino in self.pares():
            resultado = buscar_ruta(origen, destino)
            if not resultado["encontrada"]:
                continue
            ruta_anterior = None
            for _, _, ruta, tiempo, hubo_transbordo in resultado["pasos"]:
                esperado, esperado_flag = regla_costo_movimiento(
                    ruta_anterior, ruta, TIEMPO_ENTRE_PARADEROS
                )
                self.assertAlmostEqual(tiempo, esperado, places=6)
                self.assertEqual(hubo_transbordo, esperado_flag)
                ruta_anterior = ruta

    def test_no_repite_estados(self):
        """
        El estado es (paradero, ruta_actual). Volver al mismo estado con un
        costo mayor sería un ciclo, y con costos positivos eso nunca mejora la
        ruta. Un paradero sí puede repetirse con otra ruta (por ejemplo
        el_campin, punto de transbordo entre la 14 y la C11).
        """
        for origen, destino in self.pares():
            resultado = buscar_ruta(origen, destino)
            if not resultado["encontrada"]:
                continue
            estados = [(origen, None)] + [
                (paso[1], paso[2]) for paso in resultado["pasos"]
            ]
            self.assertEqual(
                len(estados), len(set(estados)), f"ciclo en {origen} -> {destino}"
            )


class TestOptimalidad(unittest.TestCase):
    """A* debe devolver el tiempo óptimo, nunca uno mejorable."""

    def test_todas_las_paradas_de_paraderos(self):
        suboptimas = 0
        for origen, destino in itertools.permutations(PARADEROS, 2):
            resultado = buscar_ruta(origen, destino)
            optimo = tiempo_optimo(origen, destino)
            if resultado["encontrada"] != (optimo is not None):
                self.fail(
                    f"{origen} -> {destino}: A* dice "
                    f"{resultado['encontrada']}, Dijkstra dice {optimo is not None}"
                )
            if optimo is not None and abs(resultado["tiempo_total"] - optimo) > 1e-9:
                suboptimas += 1
        self.assertEqual(suboptimas, 0, f"{suboptimas} rutas no óptimas")

    def test_ruta_alternativa_explicita_no_gana(self):
        # El 14 directo son 4 tramos (12.0 min); la c11 con transbordo son 7
        # tramos (29.0 min). El óptimo no debe cambiar.
        directa = buscar_ruta("chapinero_central", "portal_americas")
        with_transbordo = buscar_ruta("villa_del_rio", "chapinero_central")
        self.assertEqual(directa["tiempo_total"], 12.0)
        self.assertLess(directa["tiempo_total"], with_transbordo["tiempo_total"])


class TestGrafoInyectado(unittest.TestCase):
    """buscar_ruta debe poder trabajar sobre un grafo alternativo."""

    def test_usa_el_grafo_recibido(self):
        grafo = {
            "chapinero_central": [("portal_americas", "linea_ficticia", 2.0)],
            "portal_americas": [],
        }
        resultado = buscar_ruta("chapinero_central", "portal_americas", grafo=grafo)
        self.assertEqual(resultado["tiempo_total"], 2.0)
        self.assertEqual(resultado["pasos"][0][2], "linea_ficticia")

    def test_ve_un_reconstruir_grafo_sin_reiniciar(self):
        self.addCleanup(reglas.reconstruir_grafo)
        antes = buscar_ruta("chapinero_central", "portal_americas")["tiempo_total"]
        reglas.reconstruir_grafo(
            rutas={"urbana_14": ["chapinero_central", "portal_americas"]},
            tiempo_entre_paraderos=1.0,
        )
        despues = buscar_ruta("chapinero_central", "portal_americas")["tiempo_total"]
        self.assertEqual(antes, 12.0)
        self.assertEqual(despues, 1.0)


class TestDistanciaYHeuristica(unittest.TestCase):
    """distancia_km y las propiedades que necesita la heurística."""

    def test_distancia_consigo_mismo_es_cero(self):
        for id_paradero in PARADEROS:
            self.assertEqual(distancia_km(id_paradero, id_paradero), 0.0)

    def test_distancia_es_simetrica(self):
        for a, b in itertools.combinations(PARADEROS, 2):
            self.assertAlmostEqual(distancia_km(a, b), distancia_km(b, a), places=9)

    def test_distancia_es_no_negativa(self):
        for a, b in itertools.combinations(PARADEROS, 2):
            self.assertGreaterEqual(distancia_km(a, b), 0.0)

    def test_distancia_coincide_con_un_valor_conocido(self):
        # Chapinero Central -> CAN son ~3.46 km: 0.0312° de longitud a 4.65° de
        # latitud, unos 111 km por grado.
        self.assertAlmostEqual(
            distancia_km("chapinero_central", "can"), 3.46, delta=0.05
        )

    def test_heuristica_nula_en_la_meta(self):
        for id_paradero in PARADEROS:
            self.assertEqual(heuristica(id_paradero, id_paradero), 0.0)

    def test_heuristica_nunca_sobreestima(self):
        """
        La admisibilidad es la condición para que A* devuelva la ruta más
        rápida. Con datos donde un tramo de 7 km se cobra como uno de 3 min, la
        distancia en línea recta sobreestimaría, por eso h está acotada por el
        costo del tramo más barato.
        """
        for origen, destino in itertools.permutations(PARADEROS, 2):
            h = heuristica(origen, destino)
            self.assertLessEqual(
                h,
                TIEMPO_ENTRE_PARADEROS,
                f"h({origen}, {destino}) sobreestima el tramo más barato",
            )
            self.assertGreaterEqual(h, 0.0)

    def test_heuristica_sin_acotar_si_sobreestimaria(self):
        """Sin el acotamiento, algunos pares sí sobreestimarían."""
        saltos_largos = [
            ("can", "biblioteca_tintal"),
            ("salitre", "estadio_techo"),
        ]
        for origen, destino in saltos_largos:
            sin_acotar = distancia_km(origen, destino) / VELOCIDAD_PROMEDIO_KM_MIN
            self.assertGreater(
                sin_acotar,
                heuristica(origen, destino),
                "si este par ya no sobreestimara, el acotamiento sería innecesario",
            )


if __name__ == "__main__":
    unittest.main()
