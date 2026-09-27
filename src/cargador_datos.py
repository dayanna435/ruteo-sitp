"""
cargador_datos.py
=================
Carga y valida la base de conocimiento desde un archivo de datos externo
(`data/data.json`) en lugar de tenerla escrita a mano en el código.

Este módulo es el ÚNICO punto del sistema que abre archivos. El resto
(`hechos.py`, `reglas.py`, `motor_busqueda.py`, `main.py`) solo consume los
hechos ya validados, de modo que un error de formato se reporta aquí con un
mensaje claro en vez de exploding más adelante dentro del grafo o del A*.

Formato esperado del JSON (las cuatro claves de primer nivel son obligatorias):

    {
      "paraderos":        { "<id>": {"nombre": str, "lat": num, "lon": num} },
      "rutas":            { "<id_ruta>": ["<id_paradero>", ...] },
      "rutas_circulares": ["<id_ruta>", ...],
      "constantes":       {"<nombre>": num}
    }

Las constantes obligatorias son `tiempo_entre_paraderos`,
`tiempo_transbordo` y `velocidad_promedio_km_min`; todas deben ser > 0
(`velocidad_promedio_km_min` además debe ser > 0 porque la heurística de A*
divide por ella).

Ubicación del archivo, en orden de precedencia:
    1. Variable de entorno `RUTEO_SITP_DATA` (ruta absoluta o relativa al CWD).
    2. `data/data.json` respecto a la raíz del repositorio, es decir un nivel
       por encima del directorio de este archivo.

Para la entrega final, este mismo cargador puede alimentarse de los datasets
oficiales de TransMilenio S.A. (GeoJSON/CSV) sin tocar `hechos.py`: basta
convertirlos a este formato, o reemplazar `_leer_json` por un parser del
formato oficial.
"""

import json
import os
from pathlib import Path

NOMBRE_ARCHIVO_POR_DEFECTO = "data.json"
RUTA_RELATIVA_POR_DEFECTO = Path("data") / NOMBRE_ARCHIVO_POR_DEFECTO
VARIABLE_ENTORNO = "RUTEO_SITP_DATA"

CLAVES_OBLIGATORIAS = ("paraderos", "rutas", "rutas_circulares", "constantes")
CONSTANTES_OBLIGATORIAS = (
    "tiempo_entre_paraderos",
    "tiempo_transbordo",
    "velocidad_promedio_km_min",
)


class ErrorDatos(Exception):
    """Error de formato o de coherencia en la base de conocimiento."""


def ruta_por_defecto():
    """Ruta del archivo de datos por defecto: `<raíz del repo>/data/data.json`."""
    return Path(__file__).resolve().parent.parent / RUTA_RELATIVA_POR_DEFECTO


def resolver_ruta(ruta=None):
    """
    Resuelve la ruta del archivo de datos.

    Args:
        ruta: ruta explícita. Si es None se usa la variable de entorno
              `RUTEO_SITP_DATA` y, si no está definida, la ruta por defecto.

    Returns:
        Path: ruta resuelta.
    """
    if ruta is not None:
        return Path(ruta)
    desde_entorno = os.environ.get(VARIABLE_ENTORNO)
    if desde_entorno:
        return Path(desde_entorno)
    return ruta_por_defecto()


def _leer_json(ruta):
    """Lee y parsea el archivo, traduciendo los errores de E/S a ErrorDatos."""
    if not ruta.is_file():
        raise ErrorDatos(
            f"No se encontró el archivo de datos '{ruta}'. Se esperaba en "
            f"{ruta_por_defecto()} o en la ruta definida por {VARIABLE_ENTORNO}."
        )
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except json.JSONDecodeError as error:
        raise ErrorDatos(f"'{ruta}' no contiene JSON válido: {error}") from error
    except OSError as error:
        raise ErrorDatos(f"No se pudo leer '{ruta}': {error}") from error


def _exigir_mapa(datos, clave):
    if clave not in datos:
        raise ErrorDatos(f"Falta la clave obligatoria '{clave}' en los datos.")
    valor = datos[clave]
    if not isinstance(valor, dict):
        raise ErrorDatos(
            f"La clave '{clave}' debe ser un objeto JSON con pares clave-valor, "
            f"pero es de tipo {type(valor).__name__}."
        )
    return valor


def _cargar_paraderos(bruto):
    """Convierte `paraderos` a {id: (nombre, lat, lon)} validando rangos."""
    paraderos = {}
    for id_paradero, registro in _exigir_mapa(bruto, "paraderos").items():
        if not isinstance(registro, dict):
            raise ErrorDatos(
                f"El paradero '{id_paradero}' debe ser un objeto con "
                f"'nombre', 'lat' y 'lon'."
            )
        for campo in ("nombre", "lat", "lon"):
            if campo not in registro:
                raise ErrorDatos(
                    f"Falta '{campo}' en el paradero '{id_paradero}'."
                )

        nombre = registro["nombre"]
        if not isinstance(nombre, str) or not nombre.strip():
            raise ErrorDatos(
                f"El campo 'nombre' del paradero '{id_paradero}' debe ser un "
                f"texto no vacío."
            )

        try:
            lat = float(registro["lat"])
            lon = float(registro["lon"])
        except (TypeError, ValueError) as error:
            raise ErrorDatos(
                f"Las coordenadas del paradero '{id_paradero}' deben ser "
                f"numéricas (lat={registro['lat']!r}, lon={registro['lon']!r})."
            ) from error

        if not -90.0 <= lat <= 90.0:
            raise ErrorDatos(
                f"La latitud del paradero '{id_paradero}' ({lat}) está fuera "
                f"del rango [-90, 90]."
            )
        if not -180.0 <= lon <= 180.0:
            raise ErrorDatos(
                f"La longitud del paradero '{id_paradero}' ({lon}) está fuera "
                f"del rango [-180, 180]."
            )

        paraderos[id_paradero] = (nombre.strip(), lat, lon)

    if not paraderos:
        raise ErrorDatos("La clave 'paraderos' no define ningún paradero.")
    return paraderos


def _cargar_rutas(bruto, paraderos):
    """Convierte `rutas` a {ruta: [ids]} verificando que los paraderos existan."""
    rutas = {}
    for id_ruta, secuencia in _exigir_mapa(bruto, "rutas").items():
        if not isinstance(secuencia, list) or not secuencia:
            raise ErrorDatos(
                f"La ruta '{id_ruta}' debe ser una lista no vacía de ids de "
                f"paraderos."
            )
        for id_paradero in secuencia:
            if not isinstance(id_paradero, str):
                raise ErrorDatos(
                    f"La ruta '{id_ruta}' contiene un id de paradero que no es "
                    f"texto: {id_paradero!r}."
                )
            if id_paradero not in paraderos:
                raise ErrorDatos(
                    f"La ruta '{id_ruta}' referencia el paradero "
                    f"'{id_paradero}', que no está definido en 'paraderos'."
                )
        for anterior, siguiente in zip(secuencia, secuencia[1:]):
            if anterior == siguiente:
                raise ErrorDatos(
                    f"La ruta '{id_ruta}' repite el paradero '{anterior}' en dos "
                    f"paraderos consecutivos (bucle sin movimiento)."
                )
        rutas[id_ruta] = list(secuencia)
    return rutas


def _cargar_circulares(bruto, rutas):
    """Convierte `rutas_circulares` a set de ids de ruta existentes."""
    if "rutas_circulares" not in bruto:
        raise ErrorDatos("Falta la clave obligatoria 'rutas_circulares' en los datos.")
    declarados = bruto["rutas_circulares"]
    if isinstance(declarados, (str, bytes)) or not isinstance(
        declarados, (list, tuple, set, frozenset)
    ):
        raise ErrorDatos(
            f"La clave 'rutas_circulares' debe ser una lista de ids de ruta, "
            f"pero es de tipo {type(declarados).__name__}."
        )

    circulares = set()
    for id_ruta in declarados:
        if id_ruta not in rutas:
            raise ErrorDatos(
                f"'rutas_circulares' menciona la ruta '{id_ruta}', que no está "
                f"definida en 'rutas'."
            )
        if len(rutas[id_ruta]) < 3:
            raise ErrorDatos(
                f"La ruta circular '{id_ruta}' necesita al menos 3 paraderos "
                f"para cerrar el ciclo sin repetir arcos."
            )
        circulares.add(id_ruta)
    return circulares


def _cargar_constantes(bruto):
    """Convierte `constantes` a {nombre: float>0} validando las obligatorias."""
    constantes = _exigir_mapa(bruto, "constantes")
    valores = {}
    for nombre in CONSTANTES_OBLIGATORIAS:
        if nombre not in constantes:
            raise ErrorDatos(
                f"Falta la constante obligatoria '{nombre}' en 'constantes'."
            )
    for nombre, valor in constantes.items():
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise ErrorDatos(
                f"La constante '{nombre}' debe ser numérica, pero es "
                f"{valor!r}."
            )
        if valor <= 0:
            raise ErrorDatos(
                f"La constante '{nombre}' debe ser mayor que cero, pero es "
                f"{valor}."
            )
        valores[nombre] = float(valor)
    return valores


def validar(datos):
    """
    Valida el diccionario de datos ya parseado.

    Returns:
        dict: {"paraderos", "rutas", "rutas_circulares", "constantes"} con los
              valores ya normalizados a los tipos que consume el resto del
              sistema.

    Raises:
        ErrorDatos: con un mensaje que señala la clave y el elemento exacto
                    que falla.
    """
    if not isinstance(datos, dict):
        raise ErrorDatos(
            f"El archivo de datos debe contener un objeto JSON de primer nivel, "
            f"pero es de tipo {type(datos).__name__}."
        )
    for clave in CLAVES_OBLIGATORIAS:
        if clave not in datos:
            raise ErrorDatos(f"Falta la clave obligatoria '{clave}' en los datos.")

    paraderos = _cargar_paraderos(datos)
    rutas = _cargar_rutas(datos, paraderos)
    return {
        "paraderos": paraderos,
        "rutas": rutas,
        "rutas_circulares": _cargar_circulares(datos, rutas),
        "constantes": _cargar_constantes(datos),
    }


def cargar_datos(ruta=None):
    """
    Punto de entrada: lee el archivo de datos y devuelve los hechos validados.

    Args:
        ruta: ruta al archivo JSON. Si es None se resuelve con
              `resolver_ruta` (variable de entorno o ruta por defecto).

    Returns:
        dict: con las claves "paraderos", "rutas", "rutas_circulares" y
              "constantes". Ver `validar`.

    Raises:
        ErrorDatos: si el archivo no existe, no es JSON válido o no cumple el
                    formato esperado.
    """
    ruta_resuelta = resolver_ruta(ruta)
    return validar(_leer_json(ruta_resuelta))
