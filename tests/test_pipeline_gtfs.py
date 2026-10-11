"""
Pruebas del pipeline GTFS -> JSON (pipeline_gtfs.py) con un feed mínimo
sintético, para verificar la transformación sin recorrer el feed completo.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pipeline_gtfs


STOPS = """location_type,parent_station,stop_code,stop_id,stop_lat,stop_lon,stop_name,wheelchair_boarding,zone_id
0,,,s1,4.60,-74.10,Paradero Uno,1,
0,,,s2,4.61,-74.10,Paradero Dos,1,
0,,,s3,4.62,-74.11,Paradero Tres,1,
0,,,s4,4.63,-74.10,Paradero Cuatro,1,
"""

ROUTES = """agency_id,route_color,route_id,route_long_name,route_short_name,route_text_color,route_type
3,ff0000,R1,Linea Uno,L1,ffffff,3
3,00ff00,R2,Circular Dos,C2,ffffff,3
"""

CALENDAR = """service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
1,1,1,1,1,1,0,0,20260101,20261231
2,0,0,0,0,0,1,1,20260101,20261231
"""

TRIPS = """route_id,service_id,shape_id,trip_headsign,trip_id
R1,1,sh1,,t1
R2,2,sh2,,t2
"""

STOP_TIMES = """trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,timepoint,shape_dist_traveled
t1,06:00:00,06:00:00,s1,1,,0,0
t1,06:03:00,06:03:00,s2,2,,0,100
t1,06:06:00,06:06:00,s3,3,,0,200
t2,07:00:00,07:00:00,s2,1,,0,0
t2,07:04:00,07:04:00,s3,2,,0,100
t2,07:08:00,07:08:00,s4,3,,0,200
t2,07:12:00,07:12:00,s2,4,,0,300
"""


class TestPipeline(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.directorio.cleanup)
        self.entrada = Path(self.directorio.name) / "gtfs"
        self.salida = Path(self.directorio.name) / "output"
        self.entrada.mkdir()
        self._escribir("stops.txt", STOPS)
        self._escribir("routes.txt", ROUTES)
        self._escribir("calendar.txt", CALENDAR)
        self._escribir("trips.txt", TRIPS)
        self._escribir("stop_times.txt", STOP_TIMES)
        self.resumen = pipeline_gtfs.procesar(self.entrada, self.salida)

    def _escribir(self, nombre, contenido):
        (self.entrada / nombre).write_text(contenido, encoding="utf-8")

    def _leer(self, nombre):
        return json.loads((self.salida / nombre).read_text(encoding="utf-8"))

    def test_resumen(self):
        self.assertEqual(self.resumen["paraderos"], 4)
        self.assertEqual(self.resumen["rutas"], 2)
        self.assertEqual(self.resumen["buses"], 2)

    def test_paraderos(self):
        paraderos = {p["id_paradero"]: p for p in self._leer("paraderos.json")}
        self.assertEqual(paraderos["s1"]["nombre"], "Paradero Uno")
        self.assertEqual(paraderos["s1"]["tipo"], "zonal")

    def test_secuencia_y_bidireccionalidad(self):
        rutas = {r["id_ruta"]: r for r in self._leer("rutas.json")}
        self.assertEqual(rutas["R1"]["secuencia_paraderos"], ["s1", "s2", "s3"])
        self.assertFalse(rutas["R1"]["es_circular"])

    def test_circular_detectada_por_cierre(self):
        rutas = {r["id_ruta"]: r for r in self._leer("rutas.json")}
        self.assertTrue(rutas["R2"]["es_circular"])
        self.assertEqual(rutas["R2"]["secuencia_paraderos"][0], "s2")
        self.assertEqual(rutas["R2"]["secuencia_paraderos"][-1], "s2")

    def test_dias_de_operacion(self):
        rutas = {r["id_ruta"]: r for r in self._leer("rutas.json")}
        self.assertEqual(
            rutas["R1"]["dias_operacion"],
            ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
        )

    def test_constantes_estimadas(self):
        constantes = self._leer("constantes.json")[0]
        self.assertIn("tiempo_entre_paraderos", constantes)
        self.assertIn("tiempo_transbordo", constantes)
        self.assertIn("velocidad_comercial_promedio_kmh", constantes)
        # R1 es 3 min/tramo y R2 4 min/tramo; la mediana es 3.5.
        self.assertAlmostEqual(constantes["tiempo_entre_paraderos"], 3.5, places=3)

    def test_los_json_son_validables_por_el_cargador(self):
        from cargador_datos import cargar_datos

        cargados = cargar_datos(self.salida)
        self.assertEqual(len(cargados["paraderos"]), 4)
        self.assertEqual(len(cargados["rutas"]), 2)
        self.assertIn("R2", cargados["rutas_circulares"])


if __name__ == "__main__":
    unittest.main()
