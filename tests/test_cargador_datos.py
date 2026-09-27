"""
Pruebas de la carga y validación de la base de conocimiento (cargador_datos.py)
y de la forma que expone hechos.py.
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
    "velocidad_promedio_km_min": 0.3,
}


def datos_minimos(**cambios):
    """Un conjunto de datos válido y mínimo, listo para romper a propósito."""
    base = {
        "paraderos": {
            "a": {"nombre": "Paradero A", "lat": 4.60, "lon": -74.10},
            "b": {"nombre": "Paradero B", "lat": 4.61, "lon": -74.10},
            "c": {"nombre": "Paradero C", "lat": 4.62, "lon": -74.10},
        },
        "rutas": {"linea_1": ["a", "b", "c"]},
        "rutas_circulares": [],
        "constantes": dict(CONSTANTES_VALIDAS),
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
        for nombre, valor in datos["constantes"].items():
            self.assertIsInstance(valor, float, nombre)

    def test_el_nombre_se_recorta(self):
        datos = validar(datos_minimos(
            paraderos={"a": {"nombre": "  A  ", "lat": 1, "lon": 1}},
            rutas={"linea_1": ["a"]},
        ))
        self.assertEqual(datos["paraderos"]["a"][0], "A")

    def test_las_coordenadas_aceptan_texto_numerico(self):
        datos = validar(datos_minimos(
            paraderos={"a": {"nombre": "A", "lat": "4.60", "lon": "-74.10"}},
            rutas={"linea_1": ["a"]},
        ))
        self.assertEqual(datos["paraderos"]["a"][1:], (4.60, -74.10))

    def test_circulares_se_normalizan_a_conjunto(self):
        datos = validar(datos_minimos(
            rutas={"c": ["a", "b", "c"]}, rutas_circulares=["c"]
        ))
        self.assertEqual(datos["rutas_circulares"], {"c"})

    def test_las_constantes_adicionales_se_conservan(self):
        datos = validar(datos_minimos(
            constantes=dict(CONSTANTES_VALIDAS, espera_en_paradero=2.0)
        ))
        self.assertEqual(datos["constantes"]["espera_en_paradero"], 2.0)


class TestErroresDeFormato(unittest.TestCase):
    """Cada dato inválido debe producir un ErrorDatos que diga qué pasa."""

    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(
            fragmento,
            str(contexto.exception),
            f"el mensaje no menciona {fragmento!r}: {contexto.exception}",
        )

    def test_raiz_que_no_es_objeto(self):
        for raiz in ([], [1, 2], "texto", 42, None):
            with self.assertRaises(ErrorDatos):
                validar(raiz)

    def test_falta_cada_clave_obligatoria(self):
        for clave in ("paraderos", "rutas", "rutas_circulares", "constantes"):
            datos = datos_minimos()
            del datos[clave]
            self.assert_error(datos, clave)

    def test_falta_cada_constante_obligatoria(self):
        for nombre in CONSTANTES_VALIDAS:
            constantes = dict(CONSTANTES_VALIDAS)
            del constantes[nombre]
            self.assert_error(
                datos_minimos(constantes=constantes), nombre
            )

    def test_constante_no_numerica(self):
        self.assert_error(
            datos_minimos(constantes=dict(CONSTANTES_VALIDAS, tiempo_transbordo="ocho")),
            "tiempo_transbordo",
        )

    def test_constante_no_positiva(self):
        for valor in (0, -1, -0.5):
            self.assert_error(
                datos_minimos(
                    constantes=dict(CONSTANTES_VALIDAS, tiempo_entre_paraderos=valor)
                ),
                "tiempo_entre_paraderos",
            )

    def test_booleano_no_sirve_como_constante(self):
        # True es un int en Python; se rechaza explícitamente.
        self.assert_error(
            datos_minimos(constantes=dict(CONSTANTES_VALIDAS, tiempo_transbordo=True)),
            "tiempo_transbordo",
        )

    def test_velocidad_cero_romperia_la_heuristica(self):
        self.assert_error(
            datos_minimos(
                constantes=dict(CONSTANTES_VALIDAS, velocidad_promedio_km_min=0)
            ),
            "velocidad_promedio_km_min",
        )


class TestErroresDeParaderos(unittest.TestCase):
    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(fragmento, str(contexto.exception))

    def test_no_hay_paraderos(self):
        self.assert_error(datos_minimos(paraderos={}), "paraderos")

    def test_falta_un_campo_del_paradero(self):
        for campo in ("nombre", "lat", "lon"):
            registro = {"nombre": "A", "lat": 1, "lon": 1}
            del registro[campo]
            self.assert_error(
                datos_minimos(paraderos={"a": registro}), campo
            )

    def test_nombre_vacio(self):
        self.assert_error(
            datos_minimos(paraderos={"a": {"nombre": "   ", "lat": 1, "lon": 1}}),
            "nombre",
        )

    def test_coordenada_no_numerica(self):
        self.assert_error(
            datos_minimos(paraderos={"a": {"nombre": "A", "lat": "norte", "lon": 1}}),
            "numéricas",
        )

    def test_latitud_fuera_de_rango(self):
        for lat in (90.1, -91, 1000):
            self.assert_error(
                datos_minimos(paraderos={"a": {"nombre": "A", "lat": lat, "lon": 1}}),
                "latitud",
            )

    def test_longitud_fuera_de_rango(self):
        for lon in (180.1, -181):
            self.assert_error(
                datos_minimos(
                    paraderos={"a": {"nombre": "A", "lat": 1, "lon": lon}}
                ),
                "longitud",
            )

    def test_los_limites_de_rango_son_validos(self):
        validar(datos_minimos(
            paraderos={
                "a": {"nombre": "A", "lat": 90, "lon": 180},
                "b": {"nombre": "B", "lat": -90, "lon": -180},
            },
            rutas={"r": ["a", "b"]},
        ))

    def test_paradero_que_no_es_objeto(self):
        self.assert_error(datos_minimos(paraderos={"a": ["A", 1, 1]}), "a")


class TestErroresDeRutas(unittest.TestCase):
    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(fragmento, str(contexto.exception))

    def test_ruta_vacia(self):
        self.assert_error(datos_minimos(rutas={"linea_1": []}), "linea_1")

    def test_ruta_que_no_es_lista(self):
        self.assert_error(datos_minimos(rutas={"linea_1": "abc"}), "linea_1")

    def test_ruta_referencia_un_paradero_inexistente(self):
        self.assert_error(
            datos_minimos(rutas={"linea_1": ["a", "fantasma"]}), "fantasma"
        )

    def test_id_de_paradero_que_no_es_texto(self):
        self.assert_error(datos_minimos(rutas={"linea_1": ["a", 7]}), "no es texto")

    def test_paradero_repetido_en_pares_consecutivos(self):
        self.assert_error(datos_minimos(rutas={"linea_1": ["a", "a", "b"]}), "a")

    def test_paradero_repetido_no_consecutivo_si_es_valido(self):
        # A -> B -> A es un valide de ida y vuelta, no un error.
        validar(datos_minimos(rutas={"linea_1": ["a", "b", "a"]}))


class TestErroresDeCirculares(unittest.TestCase):
    def assert_error(self, datos, fragmento):
        with self.assertRaises(ErrorDatos) as contexto:
            validar(datos)
        self.assertIn(fragmento, str(contexto.exception))

    def test_circular_inexistente(self):
        self.assert_error(
            datos_minimos(rutas_circulares=["fantasma"]), "fantasma"
        )

    def test_circular_con_menos_de_tres_paraderos(self):
        for secuencia in (["a"], ["a", "b"]):
            self.assert_error(
                datos_minimos(
                    rutas={"c": secuencia}, rutas_circulares=["c"]
                ),
                "al menos 3 paraderos",
            )

    def test_circular_con_tres_paraderos_es_valida(self):
        validar(datos_minimos(
            rutas={"c": ["a", "b", "c"]}, rutas_circulares=["c"]
        ))

    def test_circulares_como_texto_no_sirve(self):
        self.assert_error(datos_minimos(rutas_circulares="linea_1"), "rutas_circulares")

    def test_circulares_acepta_una_tupla(self):
        datos = validar(datos_minimos(
            rutas={"c": ["a", "b", "c"]}, rutas_circulares=("c",)
        ))
        self.assertEqual(datos["rutas_circulares"], {"c"})


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

    def test_un_directorio_no_es_un_archivo_de_datos(self):
        with self.assertRaises(ErrorDatos):
            cargar_datos(self.carpeta)

    def test_ruta_por_defecto_apunta_a_data_json(self):
        self.assertEqual(
            cargador_datos.ruta_por_defecto(),
            Path(__file__).resolve().parent.parent / "data" / "data.json",
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

    def test_el_argumento_explícito_gana_a_la_variable_de_entorno(self):
        variable = cargador_datos.VARIABLE_ENTORNO
        valor_previo = os.environ.get(variable)
        self.addCleanup(
            lambda: os.environ.__setitem__(variable, valor_previo)
            if valor_previo is not None
            else os.environ.pop(variable, None)
        )
        ruta = self.escribir(datos_minimos())
        os.environ[variable] = str(self.carpeta / "no_existe.json")
        self.assertEqual(len(cargar_datos(ruta)["paraderos"]), 3)


if __name__ == "__main__":
    unittest.main()
