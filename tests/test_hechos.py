"""
Pruebas de la base de conocimiento que expone hechos.py y de su coherencia con
los datos procesados en data/output/.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import hechos
from hechos import (
    BUSES,
    INFO_RUTAS,
    PARADEROS,
    RUTAS,
    RUTAS_CIRCULARES,
    TIPOS_PARADEROS,
)


class TestFormaDeLaBase(unittest.TestCase):
    """Lo que el resto del sistema da por hecho sobre hechos.py."""

    def test_no_esta_vacia(self):
        self.assertGreater(len(PARADEROS), 1000)
        self.assertGreater(len(RUTAS), 100)

    def test_constantes_positivas(self):
        for nombre in (
            "TIEMPO_ENTRE_PARADEROS",
            "TIEMPO_TRANSBORDO",
            "VELOCIDAD_PROMEDIO_KM_MIN",
            "VELOCIDAD_COMERCIAL_KMH",
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

    def test_info_rutas_cubre_todas_las_rutas(self):
        self.assertEqual(set(INFO_RUTAS), set(RUTAS))
        for id_ruta, info in INFO_RUTAS.items():
            for campo in (
                "nombre_largo",
                "tipo",
                "dias_operacion",
                "horario_inicio",
                "horario_fin",
                "es_circular",
            ):
                self.assertIn(campo, info, id_ruta)

    def test_tipos_de_paradero_conocidos(self):
        for id_paradero, tipo in TIPOS_PARADEROS.items():
            self.assertIn(id_paradero, PARADEROS)
            self.assertIn(tipo, ("", "troncal", "zonal"))

    def test_los_buses_referencian_rutas_existentes(self):
        for id_ruta, registro in BUSES.items():
            self.assertIn(id_ruta, RUTAS)
            self.assertIn("tipo_vehiculo", registro)


if __name__ == "__main__":
    unittest.main()
