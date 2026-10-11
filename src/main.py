"""
main.py
=======
Interfaz de línea de comandos del sistema inteligente de ruteo sobre la red
del SITP (Bogotá).

Uso interactivo (menú guiado con búsqueda por nombre o id):
    python3 src/main.py

Uso directo (sin menú), para pruebas y para el video. Los argumentos pueden ser
el id del paradero o un fragmento único de su nombre:
    python3 src/main.py <origen> <destino>

Ejemplos:
    python3 src/main.py 49841 61235
    python3 src/main.py "Portal Norte" "Museo Nacional"

Debe ejecutarse desde la raíz del repositorio: los módulos del paquete plano se
importan por nombre (`from hechos import ...`).
"""

import sys
import unicodedata

from hechos import INFO_RUTAS, PARADEROS, TIEMPO_TRANSBORDO, TIPOS_PARADEROS
from motor_busqueda import buscar_ruta
from reglas import rutas_directas

MAX_SUGERENCIAS = 20


def _normalizar(texto):
    """Minúsculas sin acentos, para comparar nombres de forma tolerante."""
    plano = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in plano if not unicodedata.combining(c))
    return sin_tildes.casefold().strip()


def buscar_paraderos(consulta, limite=MAX_SUGERENCIAS):
    """
    Busca paraderos por id exacto o por fragmento de nombre.

    Returns:
        list: [(id, nombre, tipo), ...] ordenados por relevancia.
    """
    consulta = consulta.strip()
    if consulta in PARADEROS:
        return [(consulta, PARADEROS[consulta][0], TIPOS_PARADEROS.get(consulta, ""))]

    patron = _normalizar(consulta)
    exactos, parciales = [], []
    for id_paradero, (nombre, _, _) in PARADEROS.items():
        objetivo = _normalizar(nombre)
        if objetivo == patron:
            exactos.append(id_paradero)
        elif patron and patron in objetivo:
            parciales.append(id_paradero)
    coincidencias = exactos + sorted(parciales, key=lambda p: PARADEROS[p][0])
    return [
        (p, PARADEROS[p][0], TIPOS_PARADEROS.get(p, "")) for p in coincidencias[:limite]
    ]


def resolver_paradero(texto):
    """
    Convierte el texto del usuario en un id de paradero.

    Returns:
        (id, None) si hay coincidencia única; (None, sugerencias) si no hay
        coincidencia o hay varias.
    """
    coincidencias = buscar_paraderos(texto, limite=MAX_SUGERENCIAS + 1)
    if len(coincidencias) == 1:
        return coincidencias[0][0], None
    return None, coincidencias


def mostrar_coincidencias(coincidencias):
    if not coincidencias:
        print("  (sin coincidencias)")
        return
    for id_paradero, nombre, tipo in coincidencias[:MAX_SUGERENCIAS]:
        etiqueta = f" [{tipo}]" if tipo else ""
        print(f"  {id_paradero:<10} {nombre}{etiqueta}")
    if len(coincidencias) > MAX_SUGERENCIAS:
        print(f"  ... y {len(coincidencias) - MAX_SUGERENCIAS} más")


def pedir_paradero(rol):
    """
    Pide un paradero válido, con búsqueda por nombre o id.

    Returns:
        str: id válido, o None si el usuario decidió salir.
    """
    while True:
        try:
            respuesta = input(f"{rol} (nombre o id, vacío para salir): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo.")
            return None
        if not respuesta:
            print("Saliendo.")
            return None
        id_paradero, coincidencias = resolver_paradero(respuesta)
        if id_paradero:
            nombre = PARADEROS[id_paradero][0]
            print(f"  -> {id_paradero} ({nombre})")
            return id_paradero
        print("Varias coincidencias, sea más específico o use el id:")
        mostrar_coincidencias(coincidencias)


def agrupar_tramos(pasos):
    """
    Agrupa los tramos elementales en recorridos por una sola ruta (legs).

    Returns:
        list: [{"ruta", "desde", "hasta", "paradas", "tiempo",
                "hubo_transbordo"}, ...]
    """
    legs = []
    for desde, hasta, ruta, tiempo, hubo_transbordo in pasos:
        if legs and legs[-1]["ruta"] == ruta:
            leg = legs[-1]
            leg["hasta"] = hasta
            leg["paradas"] += 1
            leg["tiempo"] += tiempo
        else:
            legs.append(
                {
                    "ruta": ruta,
                    "desde": desde,
                    "hasta": hasta,
                    "paradas": 1,
                    "tiempo": tiempo,
                    "hubo_transbordo": hubo_transbordo,
                }
            )
    return legs


def _nombre_ruta(id_ruta):
    info = INFO_RUTAS.get(id_ruta, {})
    return info.get("nombre_largo") or id_ruta


def _describir_ruta(id_ruta):
    info = INFO_RUTAS.get(id_ruta, {})
    partes = [_nombre_ruta(id_ruta)]
    if info.get("tipo"):
        partes.append(info["tipo"])
    if info.get("dias_operacion"):
        partes.append("días: " + ", ".join(info["dias_operacion"]))
    if info.get("horario_inicio") and info.get("horario_fin"):
        partes.append(f"{info['horario_inicio']}–{info['horario_fin']}")
    return "  ·  ".join(partes)


def mostrar_resultado(origen, destino, resultado):
    nombre_origen = PARADEROS[origen][0]
    nombre_destino = PARADEROS[destino][0]

    print(f"\nRuta de '{nombre_origen}' a '{nombre_destino}'")
    print("=" * 60)

    directas = rutas_directas(origen, destino)
    if directas:
        print(f"Conexión directa disponible en: {', '.join(directas)}")
    else:
        print("No hay conexión directa; se calculan transbordos.")

    if not resultado or not resultado["encontrada"]:
        print("\nNo se encontró una ruta posible entre esos paraderos con las")
        print("rutas registradas en la base de conocimiento.")
        return

    if not resultado["pasos"]:
        print("\nEl origen y el destino son el mismo paradero.")
        return

    legs = agrupar_tramos(resultado["pasos"])
    print(f"\nTrayecto óptimo ({len(legs)} tramo(s) de bus, "
          f"{resultado['transbordos']} transbordo(s)):\n")

    for i, leg in enumerate(legs, 1):
        if leg["hubo_transbordo"]:
            print(f"  -- TRANSBORDO: esperar ~{TIEMPO_TRANSBORDO:.0f} min --")
        print(f"{i}. {PARADEROS[leg['desde']][0]}")
        print(f"   -> {PARADEROS[leg['hasta']][0]}")
        print(f"   Ruta [{leg['ruta']}] {_describir_ruta(leg['ruta'])}")
        print(f"   {leg['paradas']} parada(s), {leg['tiempo']:.1f} min\n")

    print("=" * 60)
    print(f"Tiempo total estimado: {resultado['tiempo_total']} min")
    print(f"Paradas (arcos): {resultado['tramos']}")
    print(f"Transbordos: {resultado['transbordos']}")


def modo_interactivo():
    print("Búsqueda de paraderos por nombre o id (por ejemplo, 'Portal Norte').")
    origen = pedir_paradero("ORIGEN")
    if origen is None:
        return
    destino = pedir_paradero("DESTINO")
    if destino is None:
        return
    resultado = buscar_ruta(origen, destino)
    mostrar_resultado(origen, destino, resultado)


def ejecutar_consulta(texto_origen, texto_destino):
    """Modo directo: resuelve ambos textos y muestra la ruta."""
    for rol, texto in (("origen", texto_origen), ("destino", texto_destino)):
        id_paradero, coincidencias = resolver_paradero(texto)
        if id_paradero is None:
            print(f"No se pudo resolver el {rol} '{texto}'.")
            print("Coincidencias:")
            mostrar_coincidencias(coincidencias)
            sys.exit(1)
        if rol == "origen":
            origen = id_paradero
        else:
            destino = id_paradero
    mostrar_resultado(origen, destino, buscar_ruta(origen, destino))


def main():
    if len(sys.argv) == 3:
        ejecutar_consulta(sys.argv[1], sys.argv[2])
    elif len(sys.argv) == 1:
        modo_interactivo()
    else:
        print("Uso: python3 src/main.py [origen destino]")
        sys.exit(1)


if __name__ == "__main__":
    main()
