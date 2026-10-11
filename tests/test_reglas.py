"""
Pruebas de las Reglas 1, 2 y 3 (reglas.py), de la construcción del grafo
lógico y de las consultas de conexión directa.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import reglas  # noqa: E402
from hechos import RUTAS, RUTAS_CIRCULARES, TIEMPO_ENTRE_PARADEROS, TIEMPO_TRANSBORDO  # noqa: E402


class TestRegla1CirculacionDirecta(unittest.TestCase):
    """Regla 1: genera un arco por cada par de paraderos consecutivos."""

    def setUp(self):
        self.rutas = {"urbana": ["a", "b", "c"], "circular": ["x", "y", "z"]}
        self.grafo = reglas.regla_generar_conexiones(
            rutas=self.rutas, circulares={"circular"}, tiempo_entre_paraderos=3.0
        )

    def test_ruta_normal_es_bidireccional(self):
        for a, b in (("a", "b"), ("b", "c")):
            self.assertIn((b, "urbana", 3.0), self.grafo[a])
            self.assertIn((a, "urbana", 3.0), self.grafo[b])

    def test_ruta_circular_es_unidireccional(self):
        for a, b in (("x", "y"), ("y", "z")):
            self.assertIn((b, "circular", 3.0), self.grafo[a])
            self.assertNotIn((a, "circular", 3.0), self.grafo[b])

    def test_ruta_circular_cierra_el_ciclo(self):
        self.assertIn(("x", "circular", 3.0), self.grafo["z"])

    def test_circular_que_termina_donde_empieza_no_genera_autolazo(self):
        # Si la secuencia ya vuelve al inicio, no se agrega un arco x -> x.
        grafo = reglas.regla_generar_conexiones(
            rutas={"c": ["a", "b", "c", "a"]}, circulares={"c"}
        )
        for origen, arcos in grafo.items():
            for destino, _, _ in arcos:
                self.assertNotEqual(origen, destino)

    def test_numero_de_arcos(self):
        # urbana no circular: 2 pares x 2 = 4; circular de 3: 2 + cierre = 3.
        self.assertEqual(sum(len(v) for v in self.grafo.values()), 7)

    def test_circular_corta_no_cierra_el_ciclo(self):
        grafo = reglas.regla_generar_conexiones(
            rutas={"corta": ["a", "b"]}, circulares={"corta"}
        )
        arcos = grafo.get("a", []) + grafo.get("b", [])
        self.assertEqual(len(arcos), 1)
        self.assertEqual(arcos[0][:2], ("b", "corta"))

    def test_grafos_reales_no_tienen_autolazos(self):
        for origen, arcos in reglas.GRAFO.items():
            for destino, _, _ in arcos:
                self.assertNotEqual(origen, destino, origen)


class TestRegla2Transbordo(unittest.TestCase):
    """Regla 2: penaliza el cambio de ruta."""

    def test_misma_ruta_no_penaliza(self):
        self.assertEqual(
            reglas.regla_costo_movimiento("urbana", "urbana", 3.0), (3.0, False)
        )

    def test_ruta_distinta_penaliza(self):
        self.assertEqual(
            reglas.regla_costo_movimiento("urbana", "otra", 3.0),
            (3.0 + TIEMPO_TRANSBORDO, True),
        )

    def test_primer_tramo_no_penaliza(self):
        self.assertEqual(reglas.regla_costo_movimiento(None, "otra", 3.0), (3.0, False))


class TestRegla3Meta(unittest.TestCase):
    def test_mismo_paradero_es_meta(self):
        self.assertTrue(reglas.regla_meta("can", "can"))

    def test_distinto_paradero_no_es_meta(self):
        self.assertFalse(reglas.regla_meta("can", "otro"))


class TestConexionesDirectas(unittest.TestCase):
    """rutas_directas y el índice inverso."""

    def test_rutas_directas_con_indice_dado(self):
        indice = {"r1": {"a", "b", "c"}, "r2": {"c", "d"}, "r3": {"a", "b"}}
        self.assertEqual(reglas.rutas_directas("a", "c", indice=indice), ["r1"])
        self.assertEqual(reglas.rutas_directas("a", "b", indice=indice), ["r1", "r3"])
        self.assertEqual(reglas.rutas_directas("a", "d", indice=indice), [])

    def test_mismo_origen_y_destino_no_es_directa(self):
        self.assertEqual(reglas.rutas_directas("a", "a", indice={"r": {"a"}}), [])

    def test_el_indice_real_cubre_todas_las_rutas(self):
        self.assertEqual(set(reglas.INDICE_RUTAS), set(RUTAS))


class TestGrafoVivo(unittest.TestCase):
    """GRAFO, grafo_actual(), indice_rutas_actual() y reconstruir_grafo()."""

    def tearDown(self):
        reglas.reconstruir_grafo()

    def test_grafo_actual_es_el_global(self):
        self.assertIs(reglas.grafo_actual(), reglas.GRAFO)
        self.assertIs(reglas.indice_rutas_actual(), reglas.INDICE_RUTAS)

    def test_reconstruir_reemplaza_los_globales(self):
        original = reglas.grafo_actual()
        nuevo = reglas.reconstruir_grafo(
            rutas={"r": ["a", "b"]}, tiempo_entre_paraderos=1.0
        )
        self.assertIsNot(nuevo, original)
        self.assertIs(reglas.grafo_actual(), nuevo)
        self.assertEqual(nuevo["a"], [("b", "r", 1.0)])
        self.assertEqual(reglas.INDICE_RUTAS, {"r": {"a", "b"}})

    def test_regla_generar_conexiones_no_toca_el_global(self):
        original = reglas.grafo_actual()
        reglas.regla_generar_conexiones(rutas={"x": ["a", "b"]})
        self.assertIs(reglas.grafo_actual(), original)


if __name__ == "__main__":
    unittest.main()
