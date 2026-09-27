"""
Pruebas de la Regla 1, 2 y 3 (reglas.py) y de la construcción del grafo lógico.
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
        self.grafo = reglas.regla_generar_conexiones()

    def test_toda_ruta_aparece_con_su_tiempo_de_tramo(self):
        # Un par consecutivo puede pertenecer a varias rutas (por ejemplo
        # chapinero_central -> el_campin, que está en urbana_14 y en c11), así
        # que se exige un arco por cada ruta que declare ese par.
        for ruta, secuencia in RUTAS.items():
            for origen, destino in zip(secuencia, secuencia[1:]):
                arcos = {(v, r, t) for v, r, t in self.grafo.get(origen, [])}
                self.assertIn(
                    (destino, ruta, TIEMPO_ENTRE_PARADEROS),
                    arcos,
                    f"falta el arco {origen} -> {destino} de la ruta {ruta}",
                )

    def test_ruta_normal_es_bidireccional(self):
        # urbana_14 no es circular: A -> B implica B -> A.
        for a, b in zip(RUTAS["urbana_14"], RUTAS["urbana_14"][1:]):
            self.assertTrue(
                any(v == a for v, _, _ in self.grafo[b]),
                f"falta el arco inverso {b} -> {a}",
            )

    def test_ruta_circular_es_unidireccional(self):
        secuencia = RUTAS["complementaria_18_8"]
        for a, b in zip(secuencia, secuencia[1:]):
            self.assertTrue(any(v == b for v, _, _ in self.grafo[a]))
            self.assertFalse(
                any(v == a for v, _, _ in self.grafo[b]),
                f"la circular no debe tener el arco inverso {b} -> {a}",
            )

    def test_ruta_circular_cierra_el_ciclo(self):
        secuencia = RUTAS["complementaria_18_8"]
        ultimo, primero = secuencia[-1], secuencia[0]
        self.assertTrue(
            any(v == primero for v, _, _ in self.grafo[ultimo]),
            "la circular debe tener el arco de cierre ultimo -> primero",
        )

    def test_numero_de_arcos(self):
        esperados = 0
        for ruta, secuencia in RUTAS.items():
            n = len(secuencia) - 1
            esperados += n if ruta in RUTAS_CIRCULARES else 2 * n
            if ruta in RUTAS_CIRCULARES and len(secuencia) >= 3:
                esperados += 1  # arco de cierre
        self.assertEqual(
            sum(len(v) for v in self.grafo.values()),
            esperados,
            "el número de arcos no coincide con lo que dicen las reglas",
        )

    def test_todos_los_arcos_usan_el_costo_de_tramo(self):
        for arcos in self.grafo.values():
            for _, _, tiempo in arcos:
                self.assertEqual(tiempo, TIEMPO_ENTRE_PARADEROS)

    def test_grafo_no_tiene_paraderos_fuera_de_la_base(self):
        from hechos import PARADEROS

        for origen, arcos in self.grafo.items():
            self.assertIn(origen, PARADEROS)
            for destino, _, _ in arcos:
                self.assertIn(destino, PARADEROS)

    def test_circular_corta_no_cierra_el_ciclo(self):
        # Con 2 paraderos el arco de cierre duplicaría el arco directo: la
        # circular queda con un único arco y "b" no tiene successors.
        grafo = reglas.regla_generar_conexiones(
            rutas={"corta": ["a", "b"]}, circulares={"corta"}
        )
        arcos = grafo.get("a", []) + grafo.get("b", [])
        self.assertEqual(len(arcos), 1, "una circular de 2 paraderos no debe cerrarse")
        self.assertEqual(arcos[0][:2], ("b", "corta"))


class TestRegla2Transbordo(unittest.TestCase):
    """Regla 2: penaliza el cambio de ruta."""

    def test_misma_ruta_no_penaliza(self):
        self.assertEqual(
            reglas.regla_costo_movimiento("urbana_14", "urbana_14", 3.0),
            (3.0, False),
        )

    def test_ruta_distinta_penaliza(self):
        self.assertEqual(
            reglas.regla_costo_movimiento("urbana_14", "c11", 3.0),
            (3.0 + TIEMPO_TRANSBORDO, True),
        )

    def test_primer_tramo_no_penaliza(self):
        # ruta_actual=None significa que aún no se ha subido a ningún bus.
        self.assertEqual(reglas.regla_costo_movimiento(None, "c11", 3.0), (3.0, False))

    def test_el_tiempo_base_se_conserva(self):
        costo, transbordo = reglas.regla_costo_movimiento("urbana_14", "c11", 7.5)
        self.assertTrue(transbordo)
        self.assertEqual(costo, 7.5 + TIEMPO_TRANSBORDO)


class TestRegla3Meta(unittest.TestCase):
    """Regla 3: determina si se alcanzó el destino."""

    def test_mismo_paradero_es_meta(self):
        self.assertTrue(reglas.regla_meta("can", "can"))

    def test_distinto_paradero_no_es_meta(self):
        self.assertFalse(reglas.regla_meta("can", "portal_americas"))


class TestGrafoVivo(unittest.TestCase):
    """GRAFO, grafo_actual() y reconstruir_grafo()."""

    def tearDown(self):
        # Deja el grafo original para no afectar a otras pruebas.
        reglas.reconstruir_grafo()

    def test_grafo_actual_es_el_global(self):
        self.assertIs(reglas.grafo_actual(), reglas.GRAFO)

    def test_reconstruir_reemplaza_el_global(self):
        original = reglas.grafo_actual()
        nuevo = reglas.reconstruir_grafo(
            rutas={"urbana_14": ["chapinero_central", "portal_americas"]},
            tiempo_entre_paraderos=1.0,
        )
        self.assertIsNot(nuevo, original)
        self.assertIs(reglas.grafo_actual(), nuevo)
        self.assertIs(reglas.GRAFO, nuevo)
        self.assertEqual(set(nuevo), {"chapinero_central", "portal_americas"})
        self.assertEqual(nuevo["chapinero_central"], [("portal_americas", "urbana_14", 1.0)])

    def test_regla_generar_conexiones_no_toca_el_global(self):
        original = reglas.grafo_actual()
        reglas.regla_generar_conexiones(rutas={"x": ["can", "portal_americas"]})
        self.assertIs(reglas.grafo_actual(), original)


if __name__ == "__main__":
    unittest.main()
