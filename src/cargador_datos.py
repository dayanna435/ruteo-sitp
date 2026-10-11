"""
cargador_datos.py
=================
Carga y valida la base de conocimiento del SITP a partir de los JSON
optimizados que produce el pipeline GTFS en `data/output/`.

Es el ÚNICO punto del sistema que abre archivos de datos. El resto de módulos
(`hechos.py`, `reglas.py`, `motor_busqueda.py`, `main.py`) solo consume los
hechos ya validados, de modo que un error de formato se reporta aquí con un
mensaje claro en vez de estallar más adelante dentro del grafo o del A*.

FORMATO ESPERADO (esquema de listas)
------------------------------------
El pipeline (`pipeline_gtfs.py`) reparte los datos en cuatro archivos, uno por
tipo, dentro de un directorio:

    paraderos.json   (obligatorio) lista de paraderos:
        {"id_paradero": str, "nombre": str, "latitud": num,
         "longitud": num, "tipo": str opcional}

    rutas.json       (obligatorio) lista de rutas:
        {"id_ruta": str, "secuencia_paraderos": [str, ...],
         "nombre_largo": str opcional, "tipo": str opcional,
         "dias_operacion": [str] opcional, "horario_inicio": str opcional,
         "horario_fin": str opcional, "es_circular": bool opcional}

    constantes.json  (obligatorio) lista con las constantes globales:
        [{"tiempo_entre_paraderos": num > 0, "tiempo_transbordo": num > 0,
          "velocidad_comercial_promedio_kmh": num > 0}]

    buses.json       (opcional) lista de flota por ruta:
        [{"id_ruta": str, "tipo_vehiculo": str, "capacidad_promedio": num}]

`validar()` trabaja sobre el diccionario FUSIONADO (aunque cada clave venga de
un archivo distinto), para que la integridad referencial entre archivos (una
ruta que referencia un paradero inexistente, un bus de una ruta inexistente) se
compruebe igual que si todo estuviera en un único objeto.

Normalización de salida (lo que consumen reglas y motor):
  - paraderos:        {id: (nombre, lat, lon)}
  - rutas:            {id_ruta: [id_paradero, ...]}
  - rutas_circulares: set(id_ruta)
  - info_rutas:       {id_ruta: {nombre_largo, tipo, dias_operacion,
                                 horario_inicio, horario_fin, es_circular}}
  - tipos_paraderos:  {id: str}
  - constantes:       {nombre: float}; incluye además
                      "velocidad_promedio_km_min" (derivada de la km/h), que es
                      la unidad que usa la heurística de A*.
  - buses:            {id_ruta: registro}

Ubicación de los datos, en orden de precedencia:
    1. Ruta explícita pasada a `cargar_datos(ruta=...)`.
    2. Variable de entorno `RUTEO_SITP_DATA`.
    3. El directorio `data/output/` respecto a la raíz del repositorio.
"""

import json
import os
from pathlib import Path

CARPETA_POR_DEFECTO = Path("data") / "output"
VARIABLE_ENTORNO = "RUTEO_SITP_DATA"

# (nombre del archivo, clave que aporta, ¿obligatorio?)
ARCHIVOS_DATOS = (
    ("paraderos.json", "paraderos", True),
    ("rutas.json", "rutas", True),
    ("constantes.json", "constantes", True),
    ("buses.json", "buses", False),
)

CLAVES_OBLIGATORIAS = ("paraderos", "rutas", "constantes")

# Constantes que el motor necesita y que el pipeline debe garantizar.
CONSTANTES_OBLIGATORIAS = (
    "tiempo_entre_paraderos",
    "tiempo_transbordo",
    "velocidad_comercial_promedio_kmh",
)

MIN_PARADEROS_RUTA_CIRCULAR = 3


class ErrorDatos(Exception):
    """Error de formato o de coherencia en la base de conocimiento."""


def ruta_por_defecto():
    """Ruta de los datos por defecto: el directorio `<raíz del repo>/data/output`."""
    return Path(__file__).resolve().parent.parent / CARPETA_POR_DEFECTO


def resolver_ruta(ruta=None):
    """
    Resuelve la ruta de los datos.

    Args:
        ruta: ruta explícita a un directorio o a un archivo. Si es None se usa
              la variable de entorno `RUTEO_SITP_DATA` y, si no está definida,
              la ruta por defecto.

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
            f"No se encontró el archivo de datos '{ruta}'. Se esperaba un "
            f"directorio con los JSON procesados en {ruta_por_defecto()} o en "
            f"la ruta definida por {VARIABLE_ENTORNO}."
        )
    try:
        with open(ruta, encoding="utf-8") as archivo:
            return json.load(archivo)
    except json.JSONDecodeError as error:
        raise ErrorDatos(f"'{ruta}' no contiene JSON válido: {error}") from error
    except OSError as error:
        raise ErrorDatos(f"No se pudo leer '{ruta}': {error}") from error


def _leer_directorio(carpeta):
    """
    Fusiona los archivos de un directorio de datos en un solo diccionario.

    La validación no se hace aquí, sino después sobre el diccionario completo,
    de modo que la integridad referencial entre archivos se compruebe igual que
    con un archivo único.

    Raises:
        ErrorDatos: si el directorio no existe o si falta un archivo obligatorio.
    """
    if not carpeta.is_dir():
        raise ErrorDatos(
            f"No se encontró el directorio de datos '{carpeta}'. Se esperaba en "
            f"{ruta_por_defecto()} o en la ruta definida por {VARIABLE_ENTORNO}."
        )

    datos = {}
    for nombre_archivo, clave, obligatorio in ARCHIVOS_DATOS:
        archivo = carpeta / nombre_archivo
        if not archivo.is_file():
            if obligatorio:
                raise ErrorDatos(
                    f"Falta el archivo obligatorio '{nombre_archivo}' en "
                    f"'{carpeta}'. Ejecute primero el pipeline GTFS "
                    f"(python3 src/pipeline_gtfs.py)."
                )
            continue
        datos[clave] = _leer_json(archivo)
    return datos


def _exigir_lista(datos, clave):
    """Devuelve `datos[clave]` comprobando que sea una lista (no texto ni dict)."""
    if clave not in datos:
        raise ErrorDatos(f"Falta la clave obligatoria '{clave}' en los datos.")
    valor = datos[clave]
    if isinstance(valor, (str, bytes, dict)) or not isinstance(
        valor, (list, tuple)
    ):
        raise ErrorDatos(
            f"La clave '{clave}' debe ser una lista JSON, pero es de tipo "
            f"{type(valor).__name__}."
        )
    return list(valor)


def _texto(valor):
    return isinstance(valor, str) and bool(valor.strip())


def _numero(valor):
    return not isinstance(valor, bool) and isinstance(valor, (int, float))


def _coordenada(valor):
    """Acepta números o texto numérico; devuelve float o None si no sirve."""
    if isinstance(valor, bool):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    if isinstance(valor, str):
        try:
            return float(valor)
        except ValueError:
            return None
    return None


def _cargar_paraderos(datos):
    """
    Valida `paraderos` y lo normaliza.

    Returns:
        (dict, dict): ({id: (nombre, lat, lon)}, {id: tipo})
    """
    lista = _exigir_lista(datos, "paraderos")
    paraderos = {}
    tipos = {}

    for posicion, registro in enumerate(lista):
        if not isinstance(registro, dict):
            raise ErrorDatos(
                f"El paradero en la posición {posicion} debe ser un objeto "
                f"JSON, pero es de tipo {type(registro).__name__}."
            )
        id_paradero = registro.get("id_paradero")
        if not _texto(id_paradero):
            raise ErrorDatos(
                f"El paradero en la posición {posicion} necesita un "
                f"'id_paradero' de texto no vacío."
            )
        id_paradero = id_paradero.strip()
        if id_paradero in paraderos:
            raise ErrorDatos(f"El id de paradero '{id_paradero}' está repetido.")

        nombre = registro.get("nombre")
        if not _texto(nombre):
            raise ErrorDatos(
                f"El campo 'nombre' del paradero '{id_paradero}' debe ser un "
                f"texto no vacío."
            )

        lat, lon = _coordenada(registro.get("latitud")), _coordenada(
            registro.get("longitud")
        )
        if lat is None or lon is None:
            raise ErrorDatos(
                f"Las coordenadas del paradero '{id_paradero}' deben ser "
                f"numéricas (latitud={registro.get('latitud')!r}, "
                f"longitud={registro.get('longitud')!r})."
            )
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

        tipo = registro.get("tipo", "")
        tipos[id_paradero] = tipo.strip() if _texto(tipo) else ""
        paraderos[id_paradero] = (nombre.strip(), lat, lon)

    if not paraderos:
        raise ErrorDatos("La lista 'paraderos' no define ningún paradero.")
    return paraderos, tipos


def _cargar_rutas(datos, paraderos):
    """
    Valida `rutas` y lo normaliza, comprobando la referencia a paraderos.

    Returns:
        (dict, set, dict): ({id_ruta: [ids]}, circulares, info_rutas)
    """
    lista = _exigir_lista(datos, "rutas")
    rutas = {}
    circulares = set()
    info_rutas = {}

    for posicion, registro in enumerate(lista):
        if not isinstance(registro, dict):
            raise ErrorDatos(
                f"La ruta en la posición {posicion} debe ser un objeto JSON, "
                f"pero es de tipo {type(registro).__name__}."
            )
        id_ruta = registro.get("id_ruta")
        if not _texto(id_ruta):
            raise ErrorDatos(
                f"La ruta en la posición {posicion} necesita un 'id_ruta' de "
                f"texto no vacío."
            )
        id_ruta = id_ruta.strip()
        if id_ruta in rutas:
            raise ErrorDatos(f"El id de ruta '{id_ruta}' está repetido.")

        secuencia = registro.get("secuencia_paraderos")
        if isinstance(secuencia, (str, bytes)) or not isinstance(
            secuencia, (list, tuple)
        ):
            raise ErrorDatos(
                f"La ruta '{id_ruta}' necesita 'secuencia_paraderos' como "
                f"lista de ids de paradero."
            )
        secuencia = list(secuencia)
        if len(secuencia) < 2:
            raise ErrorDatos(
                f"La ruta '{id_ruta}' debe tener al menos 2 paraderos, pero "
                f"tiene {len(secuencia)}."
            )

        limpia = []
        for id_paradero in secuencia:
            if not _texto(id_paradero):
                raise ErrorDatos(
                    f"La ruta '{id_ruta}' contiene un id de paradero que no es "
                    f"texto no vacío: {id_paradero!r}."
                )
            id_paradero = id_paradero.strip()
            if id_paradero not in paraderos:
                raise ErrorDatos(
                    f"La ruta '{id_ruta}' referencia el paradero "
                    f"'{id_paradero}', que no está definido en 'paraderos'."
                )
            limpia.append(id_paradero)

        for anterior, siguiente in zip(limpia, limpia[1:]):
            if anterior == siguiente:
                raise ErrorDatos(
                    f"La ruta '{id_ruta}' repite el paradero '{anterior}' en "
                    f"dos posiciones consecutivas (bucle sin movimiento)."
                )

        es_circular = bool(registro.get("es_circular", False))
        if es_circular and len(limpia) < MIN_PARADEROS_RUTA_CIRCULAR:
            raise ErrorDatos(
                f"La ruta circular '{id_ruta}' necesita al menos "
                f"{MIN_PARADEROS_RUTA_CIRCULAR} paraderos, pero tiene "
                f"{len(limpia)}."
            )

        rutas[id_ruta] = limpia
        if es_circular:
            circulares.add(id_ruta)

        dias = registro.get("dias_operacion", [])
        if isinstance(dias, str) or not isinstance(dias, (list, tuple)):
            dias = []
        info_rutas[id_ruta] = {
            "nombre_largo": registro.get("nombre_largo") or id_ruta,
            "tipo": registro.get("tipo", ""),
            "dias_operacion": [str(d) for d in dias],
            "horario_inicio": registro.get("horario_inicio", ""),
            "horario_fin": registro.get("horario_fin", ""),
            "es_circular": es_circular,
        }

    if not rutas:
        raise ErrorDatos("La lista 'rutas' no define ninguna ruta.")
    return rutas, circulares, info_rutas


def _cargar_constantes(datos):
    """
    Valida `constantes` y las normaliza a floats.

    Acepta tanto una lista de objetos (formato del pipeline) como un objeto
    suelto (útil al fusionar datos a mano). Devuelve siempre un diccionario y
    añade `velocidad_promedio_km_min`, que es la unidad que consume A*.
    """
    if "constantes" not in datos:
        raise ErrorDatos("Falta la clave obligatoria 'constantes' en los datos.")
    bruto = datos["constantes"]

    if isinstance(bruto, dict):
        registros = [bruto]
    elif isinstance(bruto, (list, tuple)):
        registros = list(bruto)
    else:
        raise ErrorDatos(
            f"La clave 'constantes' debe ser una lista con las constantes, "
            f"pero es de tipo {type(bruto).__name__}."
        )
    if not registros:
        raise ErrorDatos("La lista 'constantes' está vacía.")

    fusionadas = {}
    for registro in registros:
        if not isinstance(registro, dict):
            raise ErrorDatos(
                f"Cada elemento de 'constantes' debe ser un objeto JSON, pero "
                f"hay uno de tipo {type(registro).__name__}."
            )
        fusionadas.update(registro)

    valores = {}
    for nombre in CONSTANTES_OBLIGATORIAS:
        if nombre not in fusionadas:
            raise ErrorDatos(
                f"Falta la constante obligatoria '{nombre}' en 'constantes'."
            )
    for nombre, valor in fusionadas.items():
        if not _numero(valor):
            raise ErrorDatos(
                f"La constante '{nombre}' debe ser numérica, pero es {valor!r}."
            )
        if valor <= 0:
            raise ErrorDatos(
                f"La constante '{nombre}' debe ser mayor que cero, pero es "
                f"{valor}."
            )
        valores[nombre] = float(valor)

    # La heurística de A* divide por la velocidad en km/min.
    valores["velocidad_promedio_km_min"] = (
        valores["velocidad_comercial_promedio_kmh"] / 60.0
    )
    return valores


def _cargar_buses(datos, rutas):
    """
    Valida `buses` (opcional) comprobando que cada ruta referenciada exista.

    Returns:
        dict: {id_ruta: registro}
    """
    if "buses" not in datos:
        return {}
    lista = _exigir_lista(datos, "buses")
    buses = {}
    for posicion, registro in enumerate(lista):
        if not isinstance(registro, dict):
            raise ErrorDatos(
                f"El bus en la posición {posicion} debe ser un objeto JSON."
            )
        id_ruta = registro.get("id_ruta")
        if not _texto(id_ruta):
            raise ErrorDatos(
                f"El bus en la posición {posicion} necesita un 'id_ruta'."
            )
        id_ruta = id_ruta.strip()
        if id_ruta not in rutas:
            raise ErrorDatos(
                f"El bus de la posición {posicion} referencia la ruta "
                f"'{id_ruta}', que no está definida en 'rutas'."
            )
        if "capacidad_promedio" in registro and not _numero(
            registro["capacidad_promedio"]
        ):
            raise ErrorDatos(
                f"La 'capacidad_promedio' del bus de la ruta '{id_ruta}' debe "
                f"ser numérica."
            )
        buses[id_ruta] = registro
    return buses


def validar(datos):
    """
    Valida el diccionario de datos ya parseado (fusionado) y lo normaliza.

    Returns:
        dict: con "paraderos", "rutas", "rutas_circulares", "info_rutas",
              "tipos_paraderos", "constantes" y "buses", en los tipos que
              consume el resto del sistema.

    Raises:
        ErrorDatos: con un mensaje que señala la clave y el elemento exacto que
                    falla.
    """
    if not isinstance(datos, dict):
        raise ErrorDatos(
            f"El contenedor de datos debe ser un objeto JSON de primer nivel, "
            f"pero es de tipo {type(datos).__name__}."
        )
    for clave in CLAVES_OBLIGATORIAS:
        if clave not in datos:
            raise ErrorDatos(f"Falta la clave obligatoria '{clave}' en los datos.")

    paraderos, tipos = _cargar_paraderos(datos)
    rutas, circulares, info_rutas = _cargar_rutas(datos, paraderos)
    return {
        "paraderos": paraderos,
        "rutas": rutas,
        "rutas_circulares": circulares,
        "info_rutas": info_rutas,
        "tipos_paraderos": tipos,
        "constantes": _cargar_constantes(datos),
        "buses": _cargar_buses(datos, rutas),
    }


def cargar_datos(ruta=None):
    """
    Punto de entrada: lee los datos y devuelve los hechos validados.

    Args:
        ruta: a un directorio con los archivos repartidos, o a un archivo JSON
              que contenga las claves fusionadas. Si es None se resuelve con
              `resolver_ruta` (variable de entorno o ruta por defecto).

    Returns:
        dict: ver `validar`.

    Raises:
        ErrorDatos: si los datos no existen, no son JSON válido o no cumplen el
                    formato esperado.
    """
    ruta_resuelta = resolver_ruta(ruta)
    if ruta_resuelta.is_dir():
        return validar(_leer_directorio(ruta_resuelta))
    return validar(_leer_json(ruta_resuelta))
