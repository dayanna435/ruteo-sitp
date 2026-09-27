"""
main.py
=======
Interfaz de línea de comandos del sistema inteligente de ruteo sobre la red
zonal del SITP (Bogotá).

Uso interactivo:
    python3 main.py

Uso directo (sin menú), útil para pruebas y para el video:
    python3 main.py <id_paradero_origen> <id_paradero_destino>

Ejemplo:
    python3 main.py chapinero_central portal_americas
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
        print("Use el modo interactivo (python3 main.py) para ver los ids válidos.")
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
    origen = input("Ingrese el id del paradero de ORIGEN: ").strip()
    destino = input("Ingrese el id del paradero de DESTINO: ").strip()
    resultado = buscar_ruta(origen, destino)
    mostrar_resultado(origen, destino, resultado)


def main():
    if len(sys.argv) == 3:
        origen, destino = sys.argv[1], sys.argv[2]
        resultado = buscar_ruta(origen, destino)
        mostrar_resultado(origen, destino, resultado)
    elif len(sys.argv) == 1:
        modo_interactivo()
    else:
        print("Uso: python3 main.py [id_origen id_destino]")
        sys.exit(1)


if __name__ == "__main__":
    main()
