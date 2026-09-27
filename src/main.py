"""
main.py
=======
Interfaz de línea de comandos del sistema inteligente de ruteo sobre la red
zonal del SITP (Bogotá).

Uso interactivo:
    python3 src/main.py

Uso directo (sin menú), útil para pruebas y para el video:
    python3 src/main.py <id_paradero_origen> <id_paradero_destino>

Ejemplo:
    python3 src/main.py chapinero_central portal_americas

En ambos modos hay que ejecutarlo desde la raíz del repositorio: los módulos
del paquete plano se importan por nombre (`from hechos import ...`) y solo
resuelven porque el directorio del script entra en `sys.path`.
"""

import sys

from hechos import PARADEROS
from motor_busqueda import buscar_ruta


def listar_paraderos():
    print("\nParaderos disponibles:")
    for id_par, (nombre, _, _) in sorted(PARADEROS.items()):
        print(f"  {id_par:<20} -> {nombre}")
    print()


def mostrar_resultado(origen, destino, resultado):
    if resultado is None:
        print(f"\nRuta de '{origen}' a '{destino}'")
        print("-" * 50)
        print("Error: uno de los paraderos no existe en la base de conocimiento.")
        print("Use el modo interactivo (python3 src/main.py) para ver los ids válidos.")
        return

    nombre_origen = PARADEROS[origen][0]
    nombre_destino = PARADEROS[destino][0]

    print(f"\nRuta de '{nombre_origen}' a '{nombre_destino}'")
    print("-" * 50)

    if not resultado["encontrada"]:
        print("No se encontró una ruta posible entre esos paraderos con las")
        print("rutas SITP registradas en la base de conocimiento.")
        return

    transbordos = 0
    for i, (desde, hasta, ruta, tiempo, hubo_transbordo) in enumerate(resultado["pasos"], 1):
        marca = "  <-- TRANSBORDO" if hubo_transbordo else ""
        if hubo_transbordo:
            transbordos += 1
        print(
            f"{i:2d}. {PARADEROS[desde][0]:<22} -> {PARADEROS[hasta][0]:<22} "
            f"[{ruta}]  {tiempo:.1f} min{marca}"
        )

    print("-" * 50)
    print(f"Tiempo total estimado: {resultado['tiempo_total']} minutos")
    print(f"Número de transbordos: {transbordos}")
    print(f"Número de tramos: {len(resultado['pasos'])}")


def modo_interactivo():
    listar_paraderos()
    origen = pedir_paradero("ORIGEN")
    if origen is None:
        return
    destino = pedir_paradero("DESTINO")
    if destino is None:
        return
    resultado = buscar_ruta(origen, destino)
    mostrar_resultado(origen, destino, resultado)


def pedir_paradero(rol):
    """
    Pide un id de paradero válido. Repite la pregunta si el id no existe, en
    lugar de terminar el programa con el primer error.

    Returns:
        str: el id válido,         o None si el usuario decidió salir.
    """
    while True:
        respuesta = input(f"Ingrese el id del paradero de {rol}: ").strip()
        if not respuesta:
            print("Saliendo.")
            return None
        if respuesta in PARADEROS:
            return respuesta
        print(f"'{respuesta}' no es un id válido. Consulte la lista anterior.")


def main():
    if len(sys.argv) == 3:
        origen, destino = sys.argv[1], sys.argv[2]
        resultado = buscar_ruta(origen, destino)
        mostrar_resultado(origen, destino, resultado)
    elif len(sys.argv) == 1:
        modo_interactivo()
    else:
        print("Uso: python3 src/main.py [id_origen id_destino]")
        sys.exit(1)


if __name__ == "__main__":
    main()
