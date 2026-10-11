"""
pipeline_gtfs.py
================
Convierte los archivos GTFS estáticos oficiales (``data/gtfs/``) en los JSON
optimizados que consume ``cargador_datos.py`` (``data/output/``).

El feed GTFS es un modelo relacional (``routes`` -> ``trips`` -> ``stop_times``
-> ``stops``) pensado para una base de datos, no para un motor de ruteo en
memoria. Este módulo lo "aplana" a cuatro archivos con una estructura de
listas, fácil de validar y de indexar:

    paraderos.json    [ {id_paradero, nombre, latitud, longitud, tipo}, ... ]
    rutas.json        [ {id_ruta, nombre_largo, tipo, dias_operacion,
                         horario_inicio, horario_fin, secuencia_paraderos,
                         es_circular}, ... ]
    constantes.json   [ {tiempo_entre_paraderos, tiempo_transbordo,
                         velocidad_comercial_promedio_kmh} ]
    buses.json        [ {id_ruta, tipo_vehiculo, capacidad_promedio}, ... ]

Decisiones de diseño
--------------------
* **Una secuencia por ruta.** Una ruta GTFS tiene muchísimas variantes (una por
  viaje). Para el grafo lógico se elige el viaje con más paraderos, que es el
  trazado completo; las rutas se tratan como bidireccionales en ``reglas.py``,
  de modo que con un sentido basta para cubrir los dos.
* **Dos pasadas.** ``stop_times.txt`` tiene ~9.4 M filas. La primera pasada solo
  cuenta paraderos por viaje (181 k contadores); la segunda retiene únicamente
  las filas de los viajes representativos (~1 045 x ~50). Así la memoria se
  mantiene acotada sin cargar el archivo entero.
* **Datos derivados de los tiempos.** ``tiempo_entre_paraderos`` y la velocidad
  comercial se estiman de los ``stop_times`` reales; ``tiempo_transbordo`` no
  existe en GTFS y se fija con un valor por defecto documentado.

Uso:
    python3 src/pipeline_gtfs.py [--entrada data/gtfs] [--salida data/output]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GTFS_POR_DEFECTO = RAIZ / "data" / "gtfs"
SALIDA_POR_DEFECTO = RAIZ / "data" / "output"

RADIO_TIERRA_KM = 6371.0088

# GTFS usa índices en inglés; los archivos de salida, español.
DIAS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
DIAS_ES = {
    "monday": "Lunes",
    "tuesday": "Martes",
    "wednesday": "Miércoles",
    "thursday": "Jueves",
    "friday": "Viernes",
    "saturday": "Sábado",
    "sunday": "Domingo",
}

# agency_id del feed -> tipo de componente, según agency.txt.
TIPO_POR_AGENCIA = {
    "1": "Troncal",
    "2": "Alimentador",
    "3": "Zonal",
    "4": "Complementario",
    "5": "Especial",
    "6": "Dual",
    "7": "Cable",
}

# route_type GTFS -> tipología de vehículo y capacidad de referencia.
TIPO_VEHICULO = {"0": "Tranvía", "1": "Metro", "2": "Tren", "3": "Bus", "6": "Teleférico"}

# Valores por defecto si el feed no permite estimarlos (documentados).
TIEMPO_ENTRE_PARADEROS_POR_DEFECTO = 3.0  # minutos
VELOCIDAD_COMERCIAL_POR_DEFECTO = 18.0  # km/h
TIEMPO_TRANSBORDO_POR_DEFECTO = 8.0  # minutos


def _leer_tabla(ruta):
    """Lee un .txt GTFS y devuelve una lista de diccionarios (con encabezado)."""
    with open(ruta, encoding="utf-8-sig", newline="") as archivo:
        return list(csv.DictReader(archivo))


def _indices(ruta):
    """Devuelve (encabezado, iterador de filas) sin materializar el archivo."""
    archivo = open(ruta, encoding="utf-8-sig", newline="")
    lector = csv.reader(archivo)
    encabezado = next(lector)
    return archivo, encabezado, lector


def _segundos(hora):
    """Convierte 'HH:MM:SS' (horas pueden pasar de 24) a segundos."""
    partes = hora.strip().split(":")
    if len(partes) != 3:
        raise ValueError(f"hora GTFS inválida: {hora!r}")
    h, m, s = (int(p) for p in partes)
    return h * 3600 + m * 60 + s


def _formato_hora(segundos):
    """Segundos -> 'HH:MM' (módulo 24 h para horarios de operación)."""
    segundos %= 24 * 3600
    return f"{segundos // 3600:02d}:{(segundos % 3600) // 60:02d}"


def _distancia_km(lat1, lon1, lat2, lon2):
    """Distancia en línea recta entre dos coordenadas (haversine, km)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    h = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return 2 * RADIO_TIERRA_KM * math.asin(math.sqrt(min(1.0, h)))


def _leer_paraderos(entrada):
    """stops.txt -> catálogo de paraderos normalizado (solo puntos de abordaje)."""
    paraderos = {}
    for fila in _leer_tabla(entrada / "stops.txt"):
        stop_id = fila["stop_id"].strip()
        if not stop_id:
            continue
        # Solo los puntos de abordaje (location_type 0) aparecen en stop_times;
        # las estaciones (location_type 1) son solo agrupadores y no se rutean.
        if fila.get("location_type", "0").strip() not in ("", "0"):
            continue
        try:
            lat = float(fila["stop_lat"])
            lon = float(fila["stop_lon"])
        except (TypeError, ValueError):
            continue
        paraderos[stop_id] = {
            "id_paradero": stop_id,
            "nombre": fila["stop_name"].strip(),
            "latitud": lat,
            "longitud": lon,
            # Un punto con estación padre pertenece a la troncal; sin ella, a la
            # red zonal. Es una heurística suficiente para etiquetar el nodo.
            "tipo": "troncal" if fila.get("parent_station", "").strip() else "zonal",
        }
    return paraderos


def _leer_calendarios(entrada):
    """calendar.txt -> {service_id: [días en español]}."""
    calendarios = {}
    ruta = entrada / "calendar.txt"
    if not ruta.is_file():
        return calendarios
    for fila in _leer_tabla(ruta):
        dias = [
            DIAS_ES[dia] for dia in DIAS if fila.get(dia, "0").strip() == "1"
        ]
        calendarios[fila["service_id"].strip()] = dias
    return calendarios


def _leer_rutas(entrada):
    """routes.txt -> metadatos por route_id."""
    rutas = {}
    for fila in _leer_tabla(entrada / "routes.txt"):
        route_id = fila["route_id"].strip()
        agencia = fila.get("agency_id", "").strip()
        corto = fila.get("route_short_name", "").strip()
        largo = fila.get("route_long_name", "").strip()
        rutas[route_id] = {
            "nombre_largo": largo or corto or route_id,
            "tipo": TIPO_POR_AGENCIA.get(agencia, "Zonal"),
            "tipo_vehiculo": TIPO_VEHICULO.get(fila.get("route_type", "3").strip(), "Bus"),
        }
    return rutas


def _leer_viajes(entrada):
    """trips.txt -> (viaje -> (ruta, servicio), ruta -> [viajes])."""
    viaje_a_ruta = {}
    viaje_a_servicio = {}
    viajes_por_ruta = defaultdict(list)
    for fila in _leer_tabla(entrada / "trips.txt"):
        trip_id = fila["trip_id"].strip()
        route_id = fila["route_id"].strip()
        viaje_a_ruta[trip_id] = route_id
        viaje_a_servicio[trip_id] = fila.get("service_id", "").strip()
        viajes_por_ruta[route_id].append(trip_id)
    return viaje_a_ruta, viaje_a_servicio, viajes_por_ruta


def _contar_paraderos_por_viaje(entrada):
    """Primera pasada de stop_times: cuántos paraderos tiene cada viaje."""
    archivo, encabezado, lector = _indices(entrada / "stop_times.txt")
    i_trip = encabezado.index("trip_id")
    conteo = defaultdict(int)
    with archivo:
        for fila in lector:
            conteo[fila[i_trip]] += 1
    return conteo


def _elegir_viajes_representativos(viajes_por_ruta, conteo):
    """
    Para cada ruta, el viaje con más paraderos (desempate lexicográfico).

    Solo se consideran viajes con al menos 2 paraderos, porque una ruta de un
    único paradero no genera ningún arco.
    """
    ruta_de = {}
    for route_id, trip_ids in viajes_por_ruta.items():
        candidatos = [t for t in trip_ids if conteo.get(t, 0) >= 2]
        if not candidatos:
            continue
        maximo = max(conteo[t] for t in candidatos)
        # Desempate determinista: el trip_id lexicográficamente menor.
        elegido = min(t for t in candidatos if conteo[t] == maximo)
        ruta_de[route_id] = elegido
    return ruta_de, set(ruta_de.values())


def _leer_secuencias(entrada, viajes_representativos):
    """
    Segunda pasada de stop_times: reconstruye la secuencia de cada viaje elegido.

    Returns:
        dict: {trip_id: [(orden, stop_id, llegada_seg, salida_seg), ...]}
    """
    archivo, encabezado, lector = _indices(entrada / "stop_times.txt")
    i_trip = encabezado.index("trip_id")
    i_llegada = encabezado.index("arrival_time")
    i_salida = encabezado.index("departure_time")
    i_stop = encabezado.index("stop_id")
    i_orden = encabezado.index("stop_sequence")

    secuencias = defaultdict(list)
    with archivo:
        for fila in lector:
            trip_id = fila[i_trip]
            if trip_id not in viajes_representativos:
                continue
            try:
                orden = int(fila[i_orden])
                llegada = _segundos(fila[i_llegada])
                salida = _segundos(fila[i_salida])
            except (ValueError, IndexError):
                continue
            secuencias[trip_id].append(
                (orden, fila[i_stop].strip(), llegada, salida)
            )

    for trip_id in secuencias:
        secuencias[trip_id].sort(key=lambda t: t[0])
    return secuencias


def _dias_operacion(route_id, viajes_por_ruta, viaje_a_servicio, calendarios):
    """Unión de los días de operación de todos los viajes de la ruta."""
    vistos = set()
    for trip_id in viajes_por_ruta.get(route_id, []):
        servicio = viaje_a_servicio.get(trip_id, "")
        vistos.update(calendarios.get(servicio, []))
    orden = {dia: i for i, dia in enumerate(DIAS_ES.values())}
    return sorted(vistos, key=lambda dia: orden.get(dia, 99))


def _construir_rutas(
    entrada, paraderos, calendarios, viaje_a_servicio, viajes_por_ruta,
    ruta_a_viaje, secuencias,
):
    """
    Ensambla la lista de rutas de salida a partir de las secuencias elegidas.

    Returns:
        (rutas, muestras_tiempo, muestras_distancia)
    """
    metadatos = _leer_rutas(entrada)
    rutas = []
    muestras_tiempo = []  # minutos entre paraderos consecutivos
    muestras_distancia = []  # (km, minutos) por viaje representativo

    for route_id, trip_id in sorted(ruta_a_viaje.items()):
        filas = secuencias.get(trip_id)
        if not filas or len(filas) < 2:
            continue

        # Deduplica paraderos consecutivos (GTFS a veces repite el mismo andén).
        secuencia = []
        llegadas = []
        salidas = []
        for _, stop_id, llegada, salida in filas:
            if stop_id not in paraderos:
                continue
            if secuencia and secuencia[-1] == stop_id:
                continue
            secuencia.append(stop_id)
            llegadas.append(llegada)
            salidas.append(salida)

        if len(secuencia) < 2:
            continue

        info = metadatos.get(route_id, {})
        dias = _dias_operacion(
            route_id, viajes_por_ruta, viaje_a_servicio, calendarios
        )
        if not dias:
            dias = calendarios.get(viaje_a_servicio.get(trip_id, ""), [])

        tiempo_total = llegadas[-1] - salidas[0]
        if tiempo_total > 0 and len(secuencia) > 1:
            muestras_tiempo.append(tiempo_total / 60.0 / (len(secuencia) - 1))
            distancia = 0.0
            for a, b in zip(secuencia, secuencia[1:]):
                pa, pb = paraderos[a], paraderos[b]
                distancia += _distancia_km(
                    pa["latitud"], pa["longitud"], pb["latitud"], pb["longitud"]
                )
            muestras_distancia.append((distancia, tiempo_total / 60.0))

        rutas.append(
            {
                "id_ruta": route_id,
                "nombre_largo": info.get("nombre_largo", route_id),
                "tipo": info.get("tipo", "Zonal"),
                "tipo_vehiculo": info.get("tipo_vehiculo", "Bus"),
                "dias_operacion": dias,
                "horario_inicio": _formato_hora(salidas[0]),
                "horario_fin": _formato_hora(llegadas[-1]),
                "secuencia_paraderos": secuencia,
                # Circular = el trazado vuelve al punto de partida.
                "es_circular": secuencia[0] == secuencia[-1] and len(secuencia) >= 3,
            }
        )

    return rutas, muestras_tiempo, muestras_distancia


def _estimar_constantes(muestras_tiempo, muestras_distancia):
    """Estima tiempo entre paraderos y velocidad comercial de los stop_times."""
    if muestras_tiempo:
        tiempo = statistics.median(muestras_tiempo)
    else:
        tiempo = TIEMPO_ENTRE_PARADEROS_POR_DEFECTO

    distancia_total = sum(d for d, _ in muestras_distancia)
    tiempo_total = sum(t for _, t in muestras_distancia)
    if distancia_total > 0 and tiempo_total > 0:
        velocidad_kmh = distancia_total / tiempo_total * 60.0
    else:
        velocidad_kmh = VELOCIDAD_COMERCIAL_POR_DEFECTO

    return {
        "tiempo_entre_paraderos": round(tiempo, 3),
        "tiempo_transbordo": TIEMPO_TRANSBORDO_POR_DEFECTO,
        "velocidad_comercial_promedio_kmh": round(velocidad_kmh, 2),
    }


def _construir_buses(rutas):
    """Un registro de flota por ruta, a partir de la tipología del vehículo."""
    capacidades = {
        "Bus": 80,
        "Teleférico": 10,
        "Tranvía": 250,
        "Metro": 1000,
        "Tren": 1000,
    }
    buses = []
    for ruta in rutas:
        vehiculo = ruta["tipo_vehiculo"]
        buses.append(
            {
                "id_ruta": ruta["id_ruta"],
                "tipo_vehiculo": vehiculo,
                "capacidad_promedio": capacidades.get(vehiculo, 80),
            }
        )
    return buses


def _escribir_json(ruta, contenido):
    with open(ruta, "w", encoding="utf-8") as archivo:
        json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        archivo.write("\n")


def procesar(entrada=GTFS_POR_DEFECTO, salida=SALIDA_POR_DEFECTO):
    """
    Ejecuta el pipeline completo y escribe los cuatro JSON de salida.

    Returns:
        dict: resumen con los conteos de cada archivo generado.
    """
    entrada = Path(entrada)
    salida = Path(salida)
    salida.mkdir(parents=True, exist_ok=True)

    calendarios = _leer_calendarios(entrada)
    viaje_a_ruta, viaje_a_servicio, viajes_por_ruta = _leer_viajes(entrada)

    conteo = _contar_paraderos_por_viaje(entrada)
    ruta_a_viaje, viajes_representativos = _elegir_viajes_representativos(
        viajes_por_ruta, conteo
    )
    secuencias = _leer_secuencias(entrada, viajes_representativos)

    paraderos_brutos = _leer_paraderos(entrada)
    rutas, muestras_tiempo, muestras_distancia = _construir_rutas(
        entrada, paraderos_brutos, calendarios, viaje_a_servicio,
        viajes_por_ruta, ruta_a_viaje, secuencias,
    )

    usados = {stop for ruta in rutas for stop in ruta["secuencia_paraderos"]}
    paraderos = [
        paraderos_brutos[stop] for stop in sorted(usados) if stop in paraderos_brutos
    ]

    constantes = [_estimar_constantes(muestras_tiempo, muestras_distancia)]
    buses = _construir_buses(rutas)

    _escribir_json(salida / "paraderos.json", paraderos)
    _escribir_json(salida / "rutas.json", rutas)
    _escribir_json(salida / "constantes.json", constantes)
    _escribir_json(salida / "buses.json", buses)

    return {
        "paraderos": len(paraderos),
        "rutas": len(rutas),
        "constantes": constantes[0],
        "buses": len(buses),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entrada", default=str(GTFS_POR_DEFECTO))
    parser.add_argument("--salida", default=str(SALIDA_POR_DEFECTO))
    args = parser.parse_args()

    resumen = procesar(args.entrada, args.salida)
    print(f"Paraderos:  {resumen['paraderos']}")
    print(f"Rutas:      {resumen['rutas']}")
    print(f"Buses:      {resumen['buses']}")
    print(f"Constantes: {resumen['constantes']}")


if __name__ == "__main__":
    main()
