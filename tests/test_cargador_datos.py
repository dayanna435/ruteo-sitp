"""
Pruebas de la carga y validación de la base de conocimiento (cargador_datos.py)
y de la forma que expone hechos.py, sobre el esquema JSON de listas que produce
el pipeline GTFS en `data/output/`.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import cargador_datos
from cargador_datos import ErrorDatos, cargar_datos, resolver_ruta, validar

CONSTANTES_VALIDAS = {
    "tiempo_entre_paraderos": 3.0,
    "tiempo_transbordo": 8.0,
    "velocidad_comercial_promedio_kmh": 18.0,
}


def datos_minimos(**cambios):
    """Un conjunto de datos válido y mínimo, listo para romper a propósito."""
    base = {
        "paraderos": [
            {"id_paradero": "a", "nombre": "Paradero A", "latitud": 4.60,
             "longitud": -74.10, "tipo": "zonal"},
            {"id_paradero": "b", "nombre": "Paradero B", "latitud": 4.61,
             "longitud": -74.10, "tipo": "zonal"},
            {"id_paradero": "c", "nombre": "Paradero C", "latitud": 4.62,
             "longitud": -74.10, "tipo": "zonal"},
        ],
        "rutas": [
            {"id_ruta": "linea_1", "secuencia_paraderos": ["a", "b", "c"],
             "nombre_largo": "Línea 1"},
        ],
        "constantes": [dict(CONSTANTES_VALIDAS)],
    }
    base.update(cambios)
    return base


class TestNormalizacion(unittest.TestCase):
    """Un archivo válido se convierte a las estructuras que consume el sistema."""

    def test_forma_de_los_tipos(self):
        datos = validar(datos_minimos())
        self.assertEqual(datos["paraderos"]["a"], ("Paradero A", 4.60, -74.10))
        self.assertEqual(datos["rutas"]["linea_1"], ["a", "b", "c"])
        self.assertEqual(datos["rutas_circulares"], set())
        self.assertEqual(datos["tipos_paraderos"]["a"], "zonal")
        self.assertEqual(datos["info_rutas"]["linea_1"]["nombre_largo"], "Línea 1")
        for nombre, valor in datos["constantes"].items():
            self.assertIsInstance(valor, float, nombre)
        self.assertEqual(datos["buses"], {})

    def test_la_velocidad_se_normaliza_a_km_por_minuto(self):
        datos = validar(datos_minimos())
        self.assertAlmostEqual(
            datos["constantes"]["velocidad_promedio_km_min"], 18.0 / 60.0
        )

    def test_el_nombre_se_recorta(self):
        datos = validar(datos_minimos(
            paraderos=[
                {"id_paradero": "a", "nombre": "  A  ", "latitud": 1, "longitud": 1},
                {"id_paradero": "b", "nombre": "B", "latitud": 2, "longitud": 2},
            ],
            rutas=[{"id_ruta": "r", "secuencia_paraderos": ["a", "b"]}],
        ))
        self.assertEqual(datos["paraderos"]["a"][0], "A")

    def test_las_coordenadas_aceptan_texto_numerico(self):
        datos = validar(datos_minimos(paraderos=[
            {"id_paradero": "a", "nombre": "A", "latitud": "4.60",
             "longitud": "-74.10"},
            {"id_paradero": "b", "nombre": "B", "latitud": 4.61,
             "longitud": -74.10},
        ], rutas=[{"id_ruta": "r", "secuencia_paraderos": ["a", "b"]}]))
        self.assertEqual(datos["paraderos"]["a"][1:], (4.60, -74.10))

    def test_circulares_se_normalizan_a_conjunto(self):
        datos = validar(datos_minimos(
            rutas=[{"id_ruta": "c", "secuencia_paraderos": ["a", "b", "c"],
                    "es_circular": True}]
        ))
        self.assertEqual(datos["rutas_circulares"], {"c"})

    def test_las_constantes_adicionales_se_conservan(self):
        datos = validar(datos_minimos(
            constantes=[dict(CONSTANTES_VALIDAS, espera_en_paradero=2.0)]
        ))
        self.assertEqual(datos["constantes"]["espera_en_paradero"], 2.0)


class TestErroresDeFormato(unittest.TestCase):
    """Cada dato inválido debe producir un ErrorDatos que diga qué pasa."""

    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(
            fragmento, str(contexto.exception),
            f"el mensaje no menciona {fragmento!r}: {contexto.exception}",
        )

    def test_raiz_que_no_es_objeto(self):
        for raiz in ([], [1, 2], "texto", 42, None):
            with self.assertRaises(ErrorDatos):
                validar(raiz)

    def test_falta_cada_clave_obligatoria(self):
        for clave in ("paraderos", "rutas", "constantes"):
            datos = datos_minimos()
            del datos[clave]
            self.assert_error(datos, clave)

    def test_paraderos_que_no_es_lista(self):
        self.assert_error(datos_minimos(paraderos={"a": {}}), "paraderos")

    def test_falta_cada_constante_obligatoria(self):
        for nombre in CONSTANTES_VALIDAS:
            constantes = dict(CONSTANTES_VALIDAS)
            del constantes[nombre]
            self.assert_error(datos_minimos(constantes=[constantes]), nombre)

    def test_constante_no_numerica(self):
        self.assert_error(
            datos_minimos(constantes=[dict(CONSTANTES_VALIDAS,
                                           velocidad_comercial_promedio_kmh="18")]),
            "velocidad_comercial_promedio_kmh",
        )

    def test_constante_no_positiva(self):
        for valor in (0, -1, -0.5):
            self.assert_error(
                datos_minimos(constantes=[dict(CONSTANTES_VALIDAS,
                                               tiempo_entre_paraderos=valor)]),
                "tiempo_entre_paraderos",
            )

    def test_booleano_no_sirve_como_constante(self):
        self.assert_error(
            datos_minimos(constantes=[dict(CONSTANTES_VALIDAS,
                                           tiempo_transbordo=True)]),
            "tiempo_transbordo",
        )

    def test_constantes_vacias(self):
        self.assert_error(datos_minimos(constantes=[]), "constantes")


class TestErroresDeParaderos(unittest.TestCase):
    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(fragmento, str(contexto.exception))

    def test_no_hay_paraderos(self):
        self.assert_error(datos_minimos(paraderos=[]), "paraderos")

    def test_falta_un_campo_del_paradero(self):
        for campo in ("id_paradero", "nombre", "latitud", "longitud"):
            registro = {"id_paradero": "a", "nombre": "A", "latitud": 1,
                        "longitud": 1}
            del registro[campo]
            self.assert_error(datos_minimos(paraderos=[registro]), "paradero")

    def test_nombre_vacio(self):
        self.assert_error(
            datos_minimos(paraderos=[{"id_paradero": "a", "nombre": "   ",
                                      "latitud": 1, "longitud": 1}]),
            "nombre",
        )

    def test_coordenada_no_numerica(self):
        self.assert_error(
            datos_minimos(paraderos=[{"id_paradero": "a", "nombre": "A",
                                      "latitud": "norte", "longitud": 1}]),
            "numéricas",
        )

    def test_latitud_fuera_de_rango(self):
        self.assert_error(
            datos_minimos(paraderos=[{"id_paradero": "a", "nombre": "A",
                                      "latitud": 90.1, "longitud": 1}]),
            "latitud",
        )

    def test_longitud_fuera_de_rango(self):
        self.assert_error(
            datos_minimos(paraderos=[{"id_paradero": "a", "nombre": "A",
                                      "latitud": 1, "longitud": 180.1}]),
            "longitud",
        )

    def test_id_repetido(self):
        self.assert_error(
            datos_minimos(paraderos=[
                {"id_paradero": "a", "nombre": "A", "latitud": 1, "longitud": 1},
                {"id_paradero": "a", "nombre": "A2", "latitud": 2, "longitud": 2},
            ]),
            "repetido",
        )

    def test_paradero_que_no_es_objeto(self):
        self.assert_error(datos_minimos(paraderos=["a"]), "objeto")


class TestErroresDeRutas(unittest.TestCase):
    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(fragmento, str(contexto.exception))

    def test_ruta_con_menos_de_dos_paraderos(self):
        self.assert_error(
            datos_minimos(rutas=[{"id_ruta": "r", "secuencia_paraderos": ["a"]}]),
            "al menos 2",
        )

    def test_secuencia_que_no_es_lista(self):
        self.assert_error(
            datos_minimos(rutas=[{"id_ruta": "r", "secuencia_paraderos": "abc"}]),
            "secuencia_paraderos",
        )

    def test_ruta_referencia_un_paradero_inexistente(self):
        self.assert_error(
            datos_minimos(rutas=[{"id_ruta": "r",
                                  "secuencia_paraderos": ["a", "fantasma"]}]),
            "fantasma",
        )

    def test_paradero_repetido_en_pares_consecutivos(self):
        self.assert_error(
            datos_minimos(rutas=[{"id_ruta": "r",
                                  "secuencia_paraderos": ["a", "a", "b"]}]),
            "a",
        )

    def test_paradero_repetido_no_consecutivo_si_es_valido(self):
        validar(datos_minimos(rutas=[{"id_ruta": "r",
                                      "secuencia_paraderos": ["a", "b", "a"]}]))

    def test_ruta_sin_id(self):
        self.assert_error(
            datos_minimos(rutas=[{"secuencia_paraderos": ["a", "b"]}]), "id_ruta"
        )


class TestErroresDeCirculares(unittest.TestCase):
    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(fragmento, str(contexto.exception))

    def test_circular_con_menos_de_tres_paraderos(self):
        # ["a", "b"] solo tiene 2 paraderos: no alcanza para cerrar el ciclo.
        self.assert_error(
            datos_minimos(rutas=[{"id_ruta": "c",
                                  "secuencia_paraderos": ["a", "b"],
                                  "es_circular": True}]),
            "al menos 3",
        )

    def test_circular_con_tres_paraderos_es_valida(self):
        validar(datos_minimos(rutas=[{"id_ruta": "c",
                                      "secuencia_paraderos": ["a", "b", "c"],
                                      "es_circular": True}]))


class TestBuses(unittest.TestCase):
    """`buses` es opcional, pero si viene tiene que ser coherente."""

    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(fragmento, str(contexto.exception))

    def test_ausente_equivale_a_vacio(self):
        self.assertEqual(validar(datos_minimos())["buses"], {})

    def test_vacio_es_valido(self):
        self.assertEqual(validar(datos_minimos(buses=[]))["buses"], {})

    def test_buses_que_no_es_lista(self):
        self.assert_error(datos_minimos(buses={"r": {}}), "buses")

    def test_bus_sin_ruta(self):
        self.assert_error(datos_minimos(buses=[{"tipo_vehiculo": "Bus"}]), "id_ruta")

    def test_bus_con_ruta_inexistente(self):
        self.assert_error(
            datos_minimos(buses=[{"id_ruta": "fantasma"}]), "fantasma"
        )

    def test_bus_valido(self):
        datos = validar(datos_minimos(
            buses=[{"id_ruta": "linea_1", "tipo_vehiculo": "Bus",
                    "capacidad_promedio": 80}]
        ))
        self.assertEqual(datos["buses"]["linea_1"]["capacidad_promedio"], 80)


class TestLecturaDeArchivos(unittest.TestCase):
    """cargar_datos: resolución de ruta, variable de entorno y E/S."""

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.directorio.name)
        self.ruta = self.carpeta / "datos.json"
        self.addCleanup(self.directorio.cleanup)

    def escribir(self, datos):
        self.ruta.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
        return self.ruta

    def test_lee_un_archivo_valido(self):
        ruta = self.escribir(datos_minimos())
        self.assertEqual(cargar_datos(ruta)["rutas"]["linea_1"], ["a", "b", "c"])

    def test_archivo_inexistente(self):
        with self.assertRaises(ErrorDatos) as contexto:
            cargar_datos(self.carpeta / "no_existe.json")
        self.assertIn("No se encontró", str(contexto.exception))

    def test_json_mal_formado(self):
        self.ruta.write_text("{esto no es json", encoding="utf-8")
        with self.assertRaises(ErrorDatos) as contexto:
            cargar_datos(self.ruta)
        self.assertIn("no contiene JSON válido", str(contexto.exception))

    def test_ruta_por_defecto_apunta_a_output(self):
        self.assertEqual(
            cargador_datos.ruta_por_defecto(),
            Path(__file__).resolve().parent.parent / "data" / "output",
        )

    def test_la_variable_de_entorno_tiene_prioridad(self):
        variable = cargador_datos.VARIABLE_ENTORNO
        valor_previo = os.environ.get(variable)
        self.addCleanup(
            lambda: os.environ.__setitem__(variable, valor_previo)
            if valor_previo is not None
            else os.environ.pop(variable, None)
        )
        ruta = self.escribir(datos_minimos())
        os.environ[variable] = str(ruta)
        self.assertEqual(resolver_ruta(), ruta)
        self.assertEqual(len(cargar_datos()["paraderos"]), 3)


class TestLecturaDeDirectorio(unittest.TestCase):
    """La base de conocimiento se reparte en un directorio, un archivo por tipo."""

    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.directorio.name)
        self.addCleanup(self.directorio.cleanup)

    def escribir(self, nombre, contenido):
        ruta = self.carpeta / nombre
        ruta.write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")
        return ruta

    def escribir_completo(self, datos=None, con_buses=True):
        datos = datos_minimos() if datos is None else datos
        self.escribir("paraderos.json", datos["paraderos"])
        self.escribir("rutas.json", datos["rutas"])
        self.escribir("constantes.json", datos["constantes"])
        if con_buses:
            self.escribir("buses.json", datos.get("buses", []))
        return self.carpeta

    def test_un_directorio_completo_se_carga(self):
        self.escribir_completo()
        self.assertEqual(
            sorted(cargar_datos(self.carpeta)["paraderos"]), ["a", "b", "c"]
        )

    def test_buses_json_es_opcional(self):
        self.escribir_completo(con_buses=False)
        self.assertEqual(cargar_datos(self.carpeta)["buses"], {})

    def test_cada_archivo_aporta_su_clave(self):
        for nombre in ("paraderos.json", "rutas.json", "constantes.json"):
            with self.subTest(archivo=nombre):
                carpeta = tempfile.TemporaryDirectory()
                self.addCleanup(carpeta.cleanup)
                base = Path(carpeta.name)
                datos = datos_minimos()
                for archivo, contenido in (
                    ("paraderos.json", datos["paraderos"]),
                    ("rutas.json", datos["rutas"]),
                    ("constantes.json", datos["constantes"]),
                ):
                    (base / archivo).write_text(
                        json.dumps(contenido, ensure_ascii=False), encoding="utf-8"
                    )
                (base / nombre).unlink()
                with self.assertRaises(ErrorDatos) as contexto:
                    cargar_datos(base)
                self.assertIn(nombre, str(contexto.exception))

    def test_directorio_inexistente(self):
        with self.assertRaises(ErrorDatos) as contexto:
            cargar_datos(self.carpeta / "no_existe")
        self.assertIn("directorio", str(contexto.exception))

    def test_los_datos_reales_del_repositorio_se_cargan(self):
        """data/output debe ser la fuente válida por defecto."""
        datos = cargar_datos(cargador_datos.ruta_por_defecto())
        self.assertGreater(len(datos["paraderos"]), 1000)
        self.assertGreater(len(datos["rutas"]), 100)
        self.assertIn("tiempo_entre_paraderos", datos["constantes"])


if __name__ == "__main__":
    unittest.main()
