"""
Pruebas de la base de conocimiento que expone hechos.py y de su coherencia
con data/data.json.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import hechos
from hechos import PARADEROS, RUTAS, RUTAS_CIRCULARES


class TestFormaDeLaBase(unittest.TestCase):
    """Lo que el resto del sistema da por hecho sobre hechos.py."""

    def test_no_esta_vacia(self):
        # Importar hechos.py ya valida y carga data/data.json; si llegara aquí
        # con la base vacía sería un problema de datos.
        self.assertGreater(len(PARADEROS), 0)
        self.assertGreater(len(RUTAS), 0)

    def test_constantes_positivas(self):
        for nombre in (
            "TIEMPO_ENTRE_PARADEROS",
            "TIEMPO_TRANSBORDO",
            "VELOCIDAD_PROMEDIO_KM_MIN",
        ):
            valor = getattr(hechos, nombre)
            self.assertIsInstance(valor, float, nombre)
            self.assertGreater(valor, 0.0, nombre)

    def test_forma_de_los_paraderos(self):
        for id_paradero, registro in PARADEROS.items():
            self.assertIsInstance(id_paradero, str)
            nombre, lat, lon = registro
            self.assertIsInstance(nombre, str)
            self.assertTrue(nombre.strip(), id_paradero)
            self.assertIsInstance(lat, float)
            self.assertIsInstance(lon, float)
            self.assertTrue(-90 <= lat <= 90, id_paradero)
            self.assertTrue(-180 <= lon <= 180, id_paradero)

    def test_las_rutas_son_listas_de_paraderos_existentes(self):
        for id_ruta, secuencia in RUTAS.items():
            self.assertIsInstance(secuencia, list, id_ruta)
            self.assertGreaterEqual(len(secuencia), 2, id_ruta)
            for id_paradero in secuencia:
                self.assertIn(id_paradero, PARADEROS, id_ruta)

    def test_toda_circular_tiene_tres_o_mas_paraderos(self):
        self.assertIsInstance(RUTAS_CIRCULARES, set)
        for id_ruta in RUTAS_CIRCULARES:
            self.assertIn(id_ruta, RUTAS)
            self.assertGreaterEqual(len(RUTAS[id_ruta]), 3, id_ruta)

    def test_no_hay_paraderos_sin_ninguna_ruta(self):
        usados = {p for secuencia in RUTAS.values() for p in secuencia}
        self.assertEqual(set(PARADEROS), usados)


class TestPuntosDeTransbordo(unittest.TestCase):
    """
    Los paraderos que comparten dos rutas son los únicos puntos donde se puede
    cambiar de bus. Este test fija ese dato porque es fácil equivocarse: el
    comentario antiguo de los datos señalaba solo el_campin, pero
    chapinero_central también lo comparten la 14 y la C11.
    """

    def compartidos(self):
        en_rutas = {}
        for ruta, secuencia in RUTAS.items():
            for id_paradero in secuencia:
                en_rutas.setdefault(id_paradero, set()).add(ruta)
        return {p: rutas for p, rutas in en_rutas.items() if len(rutas) > 1}

    def test_solo_dos_paraderos_comparten_ruta(self):
        compartidos = self.compartidos()
        self.assertEqual(
            sorted(compartidos),
            ["chapinero_central", "el_campin"],
            f"cambió el conjunto de puntos de transbordo: {compartidos}",
        )

    def test_los_compartidos_son_de_la_14_y_la_c11(self):
        for id_paradero, rutas in self.compartidos().items():
            self.assertEqual(rutas, {"urbana_14", "c11"}, id_paradero)

    def test_se_puede_transbordar_en_cada_punto_compartido(self):
        from motor_busqueda import buscar_ruta

        casos = {
            "chapinero_central": ("can", "univ_pedagogica"),
            "el_campin": ("univ_pedagogica", "can"),
        }
        for punto, (origen, destino) in casos.items():
            resultado = buscar_ruta(origen, destino)
            self.assertTrue(resultado["encontrada"], f"{origen} -> {destino}")
            transbordos = [paso for paso in resultado["pasos"] if paso[4]]
            self.assertEqual(len(transbordos), 1, f"{origen} -> {destino}")
            self.assertEqual(
                transbordos[0][0],
                punto,
                f"el transbordo de {origen} -> {destino} no ocurrió en {punto}",
            )

    def test_la_circular_no_tiene_puntos_de_transbordo(self):
        from motor_busqueda import buscar_ruta

        for destino in ("dg57_tv4e", "cl54_kr6"):
            resultado = buscar_ruta("can", destino)
            if resultado["encontrada"]:
                self.assertFalse(any(paso[4] for paso in resultado["pasos"]))


if __name__ == "__main__":
    unittest.main()
