"""
main.py
=======
Interfaz de línea de comandos del sistema inteligente de ruteo sobre la red
del SITP (Bogotá), construida con Rich (paneles, tablas, paginación y
preguntas) para ofrecer una experiencia de terminal moderna.

Modos de uso
------------
Menú interactivo (recomendado; no hace falta conocer ids ni nombres exactos):

    python3 src/main.py

Modo directo, para pruebas o scripts (los argumentos pueden ser el id o un
fragmento único de nombre):

    python3 src/main.py <origen> <destino>
    python3 src/main.py "Portal Norte" "Museo Nacional"

Subcomandos de consulta (no interactivos):

    python3 src/main.py paraderos [filtro]   # lista paraderos e ids
    python3 src/main.py rutas [filtro]       # lista rutas disponibles
    python3 src/main.py ruta <id>            # detalle de una ruta
    python3 src/main.py buses [filtro]       # flota asignada
    python3 src/main.py stats                # estadísticas de la red
    python3 src/main.py --help

Debe ejecutarse desde la raíz del repositorio: los módulos del paquete plano se
importan por nombre (`from hechos import ...`).
"""

import sys
import unicodedata

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from hechos import (
    BUSES,
    INFO_RUTAS,
    PARADEROS,
    RUTAS,
    RUTAS_CIRCULARES,
    TIEMPO_ENTRE_PARADEROS,
    TIEMPO_TRANSBORDO,
    TIPOS_PARADEROS,
    VELOCIDAD_COMERCIAL_KMH,
)
from motor_busqueda import buscar_ruta
from reglas import INDICE_RUTAS, grafo_actual, rutas_directas

console = Console()
POR_PAGINA = 15
MAX_LISTADO = 60


# ---------------------------------------------------------------------------
# Utilidades de búsqueda
# ---------------------------------------------------------------------------
def _normalizar(texto):
    """Minúsculas sin acentos, para comparar nombres de forma tolerante."""
    plano = unicodedata.normalize("NFKD", str(texto))
    sin_tildes = "".join(c for c in plano if not unicodedata.combining(c))
    return sin_tildes.casefold().strip()


def filtrar_paraderos(consulta):
    """
    Devuelve ids de paradero que coinciden con `consulta`.

    Si `consulta` es un id exacto o está vacía, se comporta como se espera:
    id exacto -> ese id; vacío -> todos (ordenados por nombre); en otro caso
    busca por fragmento de nombre o de id.
    """
    consulta = (consulta or "").strip()
    if consulta in PARADEROS:
        return [consulta]
    patron = _normalizar(consulta)
    if not patron:
        return sorted(PARADEROS, key=lambda p: _normalizar(PARADEROS[p][0]))
    return sorted(
        (
            p
            for p in PARADEROS
            if patron in _normalizar(PARADEROS[p][0]) or patron in _normalizar(p)
        ),
        key=lambda p: _normalizar(PARADEROS[p][0]),
    )


def filtrar_rutas(consulta):
    """Devuelve ids de ruta que coinciden por id o por nombre largo."""
    consulta = (consulta or "").strip()
    if consulta in RUTAS:
        return [consulta]
    patron = _normalizar(consulta)
    if not patron:
        return sorted(RUTAS)
    return sorted(
        r
        for r in RUTAS
        if patron in _normalizar(r)
        or patron in _normalizar(INFO_RUTAS.get(r, {}).get("nombre_largo", ""))
    )


def rutas_de_paradero(id_paradero):
    """Rutas cuyo trazado incluye el paradero dado."""
    return sorted(r for r, paraderos in INDICE_RUTAS.items() if id_paradero in paraderos)


def _tipo(id_paradero):
    return TIPOS_PARADEROS.get(id_paradero) or "-"


def _nombre_ruta(id_ruta):
    info = INFO_RUTAS.get(id_ruta, {})
    return info.get("nombre_largo") or id_ruta


# ---------------------------------------------------------------------------
# Tablas y paginación
# ---------------------------------------------------------------------------
def _tabla_paraderos(ids, inicio, fin, titulo):
    tabla = Table(
        title=f"{titulo} — {len(ids)} resultado(s) (pág. {inicio // POR_PAGINA + 1})",
        box=box.SIMPLE_HEAVY,
        header_style="bold cyan",
        expand=True,
    )
    tabla.add_column("#", justify="right", style="dim", width=4)
    tabla.add_column("ID", style="cyan")
    tabla.add_column("Nombre", style="white", overflow="fold")
    tabla.add_column("Tipo", style="magenta")
    for i in range(inicio, fin):
        p = ids[i]
        tabla.add_row(str(i + 1), p, PARADEROS[p][0], _tipo(p))
    return tabla


def _tabla_rutas(ids, inicio, fin, titulo):
    tabla = Table(
        title=f"{titulo} — {len(ids)} resultado(s) (pág. {inicio // POR_PAGINA + 1})",
        box=box.SIMPLE_HEAVY,
        header_style="bold cyan",
        expand=True,
    )
    tabla.add_column("#", justify="right", style="dim", width=4)
    tabla.add_column("ID", style="cyan")
    tabla.add_column("Nombre", style="white", overflow="fold")
    tabla.add_column("Tipo", style="magenta")
    tabla.add_column("Paradas", justify="right")
    tabla.add_column("Circular", justify="center")
    for i in range(inicio, fin):
        r = ids[i]
        info = INFO_RUTAS.get(r, {})
        n = len(RUTAS.get(r, ()))
        circular = "Sí" if r in RUTAS_CIRCULARES else "No"
        tabla.add_row(str(i + 1), r, info.get("nombre_largo") or r, info.get("tipo") or "-", str(n), circular)
    return tabla


def _paginar(ids, titulo, constructor, seleccionable=True):
    """
    Muestra `ids` paginados y gestiona la navegación.

    Returns:
        ("ok", id)       si el usuario eligió un elemento (solo si seleccionable).
        ("buscar", None) si el usuario quiere reescribir la búsqueda.
        ("cancelar", None) si el usuario salió.
    """
    if not ids:
        console.print("[yellow]Sin resultados.[/yellow]")
        return ("cancelar", None)

    total = (len(ids) - 1) // POR_PAGINA + 1
    pagina = 0
    while True:
        inicio = pagina * POR_PAGINA
        fin = min(inicio + POR_PAGINA, len(ids))
        console.print(constructor(ids, inicio, fin, titulo))
        console.print(f"[dim]pág. {pagina + 1}/{total}[/dim]")

        if seleccionable:
            ayuda = (
                "Nº para elegir · [cyan]b[/cyan] nueva búsqueda · "
                "[cyan]n[/cyan]ext · [cyan]p[/cyan]rev · [cyan]q[/cyan] cancelar"
            )
        else:
            ayuda = "[cyan]n[/cyan]ext · [cyan]p[/cyan]rev · [cyan]q[/cyan] volver"

        try:
            respuesta = Prompt.ask(ayuda, default="q", show_default=False).strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ("cancelar", None)

        if respuesta in ("", "q"):
            return ("cancelar", None)
        if respuesta == "n":
            if pagina < total - 1:
                pagina += 1
            else:
                console.print("[dim]Ya está en la última página.[/dim]")
            continue
        if respuesta == "p":
            if pagina > 0:
                pagina -= 1
            else:
                console.print("[dim]Ya está en la primera página.[/dim]")
            continue
        if seleccionable and respuesta == "b":
            return ("buscar", None)
        if seleccionable and respuesta.isdigit():
            numero = int(respuesta)
            if inicio < numero <= fin:
                return ("ok", ids[numero - 1])
            console.print("[red]Número fuera de rango.[/red]")
            continue
        console.print("[yellow]Opción no válida.[/yellow]")


def _pausa():
    try:
        console.input("\n[dim]Pulsa Enter para volver al menú...[/dim]")
    except (EOFError, KeyboardInterrupt):
        pass


# ---------------------------------------------------------------------------
# Selección interactiva de paraderos (sin exigir id ni nombre exactos)
# ---------------------------------------------------------------------------
def _explorar_paraderos(consulta, titulo):
    """
    Buscador interactivo de paraderos: filtra, pagina y permite elegir por
    número. Devuelve el id elegido o None si se cancela.
    """
    while True:
        ids = filtrar_paraderos(consulta)
        accion, valor = _paginar(ids, titulo, _tabla_paraderos)
        if accion == "ok":
            return valor
        if accion == "cancelar":
            return None
        try:
            consulta = Prompt.ask(
                "Nueva búsqueda (nombre o id; vacío para ver todos)",
                default="",
                show_default=False,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return None


def elegir_paradero(rol):
    """
    Pide al usuario un paradero para el rol dado ('Origen' / 'Destino').

    El usuario puede buscar por nombre parcial, navegar los resultados y
    elegir por número, o escribir directamente un id. Devuelve el id o None.
    """
    console.print(
        f"[bold]{rol}[/]: busca por nombre o id. Puedes dejar la búsqueda vacía "
        "para ver todos y elegir por número."
    )
    try:
        consulta = Prompt.ask(
            f"[bold]{rol}[/] (nombre o id)", default="", show_default=False
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None

    id_paradero = _explorar_paraderos(consulta, f"{rol}: coincidencias")
    if id_paradero:
        console.print(
            f"[green]Elegido:[/green] [cyan]{id_paradero}[/cyan] "
            f"{PARADEROS[id_paradero][0]}"
        )
    else:
        console.print("[dim]Selección cancelada.[/dim]")
    return id_paradero


# ---------------------------------------------------------------------------
# Fichas de detalle
# ---------------------------------------------------------------------------
def mostrar_detalle_paradero(id_paradero):
    nombre, lat, lon = PARADEROS[id_paradero]
    rutas = rutas_de_paradero(id_paradero)
    console.print(
        Panel.fit(
            f"[bold]{nombre}[/bold]\n"
            f"[dim]ID:[/dim] [cyan]{id_paradero}[/cyan]   "
            f"[dim]Tipo:[/dim] {_tipo(id_paradero)}\n"
            f"[dim]Coordenadas:[/dim] {lat:.6f}, {lon:.6f}\n"
            f"[dim]Rutas que lo sirven:[/dim] {len(rutas)}",
            title="Paradero",
            border_style="blue",
        )
    )
    if rutas:
        tabla = Table(box=box.SIMPLE, header_style="bold cyan", expand=True)
        tabla.add_column("Ruta", style="cyan")
        tabla.add_column("Nombre", overflow="fold")
        tabla.add_column("Tipo", style="magenta")
        for r in rutas[:30]:
            tabla.add_row(r, _nombre_ruta(r), INFO_RUTAS.get(r, {}).get("tipo") or "-")
        console.print(tabla)
        if len(rutas) > 30:
            console.print(f"[dim]... y {len(rutas) - 30} ruta(s) más.[/dim]")


def mostrar_detalle_ruta(id_ruta):
    info = INFO_RUTAS.get(id_ruta, {})
    secuencia = RUTAS.get(id_ruta, [])
    dias = ", ".join(info.get("dias_operacion") or []) or "-"
    horario = "-"
    if info.get("horario_inicio") and info.get("horario_fin"):
        horario = f"{info['horario_inicio']}–{info['horario_fin']}"
    console.print(
        Panel.fit(
            f"[bold]{info.get('nombre_largo') or id_ruta}[/bold]\n"
            f"[dim]ID:[/dim] [cyan]{id_ruta}[/cyan]   "
            f"[dim]Tipo:[/dim] {info.get('tipo') or '-'}   "
            f"[dim]Circular:[/dim] {'Sí' if id_ruta in RUTAS_CIRCULARES else 'No'}\n"
            f"[dim]Días:[/dim] {dias}   [dim]Horario:[/dim] {horario}\n"
            f"[dim]Paraderos:[/dim] {len(secuencia)}",
            title="Ruta",
            border_style="blue",
        )
    )
    tabla = Table(
        title="Secuencia de paraderos",
        box=box.SIMPLE_HEAVY,
        header_style="bold cyan",
        expand=True,
    )
    tabla.add_column("#", justify="right", style="dim", width=4)
    tabla.add_column("ID", style="cyan")
    tabla.add_column("Nombre", overflow="fold")
    tabla.add_column("Tipo", style="magenta")
    for i, p in enumerate(secuencia, 1):
        tabla.add_row(str(i), p, PARADEROS.get(p, ("?",))[0], _tipo(p))
    console.print(tabla)


# ---------------------------------------------------------------------------
# Opciones del menú
# ---------------------------------------------------------------------------
def _correr_busqueda(origen, destino):
    if console.is_terminal:
        with console.status("[cyan]Calculando la ruta óptima...[/cyan]", spinner="dots"):
            return buscar_ruta(origen, destino)
    return buscar_ruta(origen, destino)


def mostrar_viaje(origen, destino, resultado):
    nombre_origen = PARADEROS[origen][0]
    nombre_destino = PARADEROS[destino][0]
    console.print()
    console.rule(f"[bold blue]Ruta de '{nombre_origen}' a '{nombre_destino}'[/bold blue]")

    directas = rutas_directas(origen, destino)
    if directas:
        console.print(
            Panel(
                "[green]Hay conexión directa[/green] en la(s) ruta(s): "
                + ", ".join(f"[cyan]{r}[/cyan] ({_nombre_ruta(r)})" for r in directas),
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                "[yellow]No hay conexión directa;[/yellow] se calculan transbordos.",
                border_style="yellow",
            )
        )

    if resultado is None:
        console.print("[red]Origen o destino no existen en la base de conocimiento.[/red]")
        return
    if not resultado["encontrada"]:
        console.print(
            "[red]No se encontró una ruta posible[/red] entre esos paraderos con "
            "las rutas registradas."
        )
        return
    if not resultado["pasos"]:
        console.print("[yellow]El origen y el destino son el mismo paradero.[/yellow]")
        return

    legs = _agrupar_tramos(resultado["pasos"])
    tabla = Table(
        title=f"Trayecto óptimo — {len(legs)} tramo(s) de bus",
        box=box.SIMPLE_HEAVY,
        header_style="bold cyan",
        expand=True,
    )
    tabla.add_column("#", justify="right", style="dim", width=3)
    tabla.add_column("Transbordo", style="yellow")
    tabla.add_column("Sube en", style="green", overflow="fold")
    tabla.add_column("Baja en", style="magenta", overflow="fold")
    tabla.add_column("Ruta", style="cyan")
    tabla.add_column("Paradas", justify="right")
    tabla.add_column("Tiempo", justify="right")
    for i, leg in enumerate(legs, 1):
        transbordo = f"~{TIEMPO_TRANSBORDO:.0f} min" if leg["hubo_transbordo"] else ""
        tabla.add_row(
            str(i),
            transbordo,
            f"{PARADEROS[leg['desde']][0]}\n[dim]{leg['desde']}[/dim]",
            f"{PARADEROS[leg['hasta']][0]}\n[dim]{leg['hasta']}[/dim]",
            f"{leg['ruta']}\n[dim]{_nombre_ruta(leg['ruta'])}[/dim]",
            str(leg["paradas"]),
            f"{leg['tiempo']:.1f} min",
        )
    console.print(tabla)

    console.print(
        Panel(
            f"[bold]Tiempo total estimado:[/bold] [green]{resultado['tiempo_total']} min[/green]   ·   "
            f"[bold]Paradas (arcos):[/bold] {resultado['tramos']}   ·   "
            f"[bold]Transbordos:[/bold] {resultado['transbordos']}",
            border_style="green",
        )
    )
    console.print(
        "[dim]Los tiempos son estimaciones del modelo (velocidad comercial "
        f"promedio {VELOCIDAD_COMERCIAL_KMH:.1f} km/h, ~{TIEMPO_ENTRE_PARADEROS:.1f} "
        "min entre paraderos y penalización por transbordo).[/dim]"
    )


def planear_viaje():
    console.rule("[bold blue]Planear un viaje[/bold blue]")
    origen = elegir_paradero("Origen")
    if not origen:
        return
    destino = elegir_paradero("Destino")
    if not destino:
        return
    mostrar_viaje(origen, destino, _correr_busqueda(origen, destino))


def ver_paraderos_interactivo():
    console.rule("[bold blue]Paraderos e IDs[/bold blue]")
    console.print("[dim]Escribe un nombre parcial para filtrar, o deja vacío para ver todos.[/dim]")
    try:
        consulta = Prompt.ask("Filtro", default="", show_default=False).strip()
    except (EOFError, KeyboardInterrupt):
        return
    while True:
        id_paradero = _explorar_paraderos(consulta, "Paraderos SITP")
        if not id_paradero:
            return
        mostrar_detalle_paradero(id_paradero)
        try:
            consulta = Prompt.ask(
                "\nOtra búsqueda (vacío para ver todos; [cyan]q[/cyan] para salir)",
                default="q",
                show_default=False,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return
        if consulta.lower() == "q":
            return


def ver_rutas_interactivo():
    console.rule("[bold blue]Rutas disponibles[/bold blue]")
    try:
        consulta = Prompt.ask("Filtro (id o nombre; vacío para todas)", default="", show_default=False).strip()
    except (EOFError, KeyboardInterrupt):
        return
    while True:
        ids = filtrar_rutas(consulta)
        accion, valor = _paginar(ids, "Rutas SITP", _tabla_rutas)
        if accion == "cancelar":
            return
        if accion == "ok":
            mostrar_detalle_ruta(valor)
        try:
            consulta = Prompt.ask(
                "\nOtro filtro (vacío para todas; [cyan]q[/cyan] para salir)",
                default="q",
                show_default=False,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            return
        if consulta.lower() == "q":
            return


def ver_flota_interactivo():
    console.rule("[bold blue]Flota de buses[/bold blue]")
    console.print("[dim]Vehículo y capacidad promedio asignados por ruta.[/dim]")
    try:
        consulta = Prompt.ask("Filtro de rutas (id o nombre; vacío para todas)", default="", show_default=False).strip()
    except (EOFError, KeyboardInterrupt):
        return
    ids = filtrar_rutas(consulta)
    console.print(_tabla_flota(ids, 0, min(len(ids), MAX_LISTADO), "Flota por ruta"))
    if len(ids) > MAX_LISTADO:
        console.print(f"[dim]Mostrando {MAX_LISTADO} de {len(ids)}. Usa un filtro para acotar.[/dim]")


def _tabla_flota(ids, inicio, fin, titulo):
    tabla = Table(title=titulo, box=box.SIMPLE_HEAVY, header_style="bold cyan", expand=True)
    tabla.add_column("Ruta", style="cyan")
    tabla.add_column("Nombre", overflow="fold")
    tabla.add_column("Vehículo", style="magenta")
    tabla.add_column("Capacidad", justify="right")
    for i in range(inicio, fin):
        r = ids[i]
        info = BUSES.get(r, {})
        tabla.add_row(
            r,
            _nombre_ruta(r),
            info.get("tipo_vehiculo") or "-",
            str(info.get("capacidad_promedio") or "-"),
        )
    return tabla


def ver_estadisticas():
    console.rule("[bold blue]Estadísticas de la red[/bold blue]")
    arcos = sum(len(vecinos) for vecinos in grafo_actual().values())
    console.print(
        Panel.fit(
            f"[bold]Paraderos:[/bold] {len(PARADEROS)}\n"
            f"[bold]Rutas:[/bold] {len(RUTAS)}  "
            f"([cyan]{len(RUTAS_CIRCULARES)}[/cyan] circulares)\n"
            f"[bold]Buses (registros de flota):[/bold] {len(BUSES)}\n"
            f"[bold]Arcos dirigidos:[/bold] {arcos}\n"
            f"[bold]Tiempo entre paraderos:[/bold] {TIEMPO_ENTRE_PARADEROS:.2f} min\n"
            f"[bold]Penalización por transbordo:[/bold] {TIEMPO_TRANSBORDO:.1f} min\n"
            f"[bold]Velocidad comercial:[/bold] {VELOCIDAD_COMERCIAL_KMH:.2f} km/h",
            title="Resumen de la red",
            border_style="blue",
        )
    )

    top_rutas = sorted(RUTAS, key=lambda r: len(RUTAS[r]), reverse=True)[:8]
    tabla = Table(title="Rutas con más paraderos", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    tabla.add_column("Ruta", style="cyan")
    tabla.add_column("Nombre", overflow="fold")
    tabla.add_column("Paradas", justify="right")
    for r in top_rutas:
        tabla.add_row(r, _nombre_ruta(r), str(len(RUTAS[r])))
    console.print(tabla)

    conteo = {}
    for paraderos in INDICE_RUTAS.values():
        for p in paraderos:
            conteo[p] = conteo.get(p, 0) + 1
    top_hubs = sorted(conteo, key=conteo.get, reverse=True)[:8]
    tabla = Table(title="Paraderos con más rutas (intercambiadores)", box=box.SIMPLE_HEAVY, header_style="bold cyan")
    tabla.add_column("ID", style="cyan")
    tabla.add_column("Nombre", overflow="fold")
    tabla.add_column("Rutas", justify="right")
    for p in top_hubs:
        tabla.add_row(p, PARADEROS[p][0], str(conteo[p]))
    console.print(tabla)


def _agrupar_tramos(pasos):
    """Agrupa tramos elementales en recorridos por una sola ruta (legs)."""
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


# ---------------------------------------------------------------------------
# Menú y ayuda
# ---------------------------------------------------------------------------
def _banner():
    console.clear()
    console.print(
        Panel.fit(
            "[bold cyan]SISTEMA DE RUTEO DE TRANSPORTE PÚBLICO — SITP[/bold cyan]\n"
            "[dim]Bogotá · seleccione una opción para continuar[/dim]",
            border_style="blue",
        )
    )


_OPCIONES_MENU = (
    ("1", "Planear un viaje (origen -> destino)", "planear_viaje"),
    ("2", "Buscar / ver paraderos e IDs", "ver_paraderos_interactivo"),
    ("3", "Ver rutas y su detalle", "ver_rutas_interactivo"),
    ("4", "Ver flota de buses", "ver_flota_interactivo"),
    ("5", "Estadísticas de la red", "ver_estadisticas"),
    ("6", "Ayuda", "mostrar_ayuda"),
    ("7", "Salir", None),
)


def menu():
    while True:
        _banner()
        for clave, etiqueta, _ in _OPCIONES_MENU:
            console.print(f"  [bold cyan][{clave}][/bold cyan] {etiqueta}")
        console.print()
        try:
            eleccion = Prompt.ask(
                "[bold]Selecciona una opción[/bold]",
                choices=[clave for clave, _, _ in _OPCIONES_MENU],
                default="7",
                show_choices=False,
            )
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Saliendo.[/dim]")
            return

        if eleccion == "7":
            console.print("[bold red]Hasta luego.[/bold red]")
            return
        for clave, _, nombre_accion in _OPCIONES_MENU:
            if clave == eleccion and nombre_accion:
                try:
                    globals()[nombre_accion]()
                except (EOFError, KeyboardInterrupt):
                    console.print("\n[dim]Acción cancelada.[/dim]")
                except Exception as error:  # noqa: BLE001 - la CLI nunca debe caerse
                    console.print(f"[red]Ocurrió un error inesperado:[/red] {error}")
                _pausa()
                break


def mostrar_ayuda():
    console.print(
        Panel(
            "[bold]Menú interactivo[/bold]\n"
            "  python3 src/main.py\n\n"
            "[bold]Viaje directo[/bold] (id o nombre):\n"
            "  python3 src/main.py <origen> <destino>\n\n"
            "[bold]Subcomandos de consulta[/bold]\n"
            "  paraderos \\[filtro]   Lista paraderos e IDs\n"
            "  rutas \\[filtro]       Lista rutas disponibles\n"
            "  ruta <id>             Detalle y secuencia de una ruta\n"
            "  buses \\[filtro]       Flota asignada por ruta\n"
            "  stats                 Estadísticas de la red\n\n"
            "[dim]En el menú puedes buscar por nombre parcial y elegir por número, "
            "sin necesidad de conocer el ID exacto.[/dim]",
            title="Ayuda",
            border_style="blue",
        )
    )


# ---------------------------------------------------------------------------
# Modo directo y subcomandos (no interactivos)
# ---------------------------------------------------------------------------
def _listar(ids, titulo, constructor):
    if not ids:
        console.print("[yellow]Sin resultados.[/yellow]")
        return
    fin = min(len(ids), MAX_LISTADO)
    console.print(constructor(ids, 0, fin, titulo))
    if len(ids) > MAX_LISTADO:
        console.print(f"[dim]Mostrando {MAX_LISTADO} de {len(ids)}. Usa un filtro para acotar.[/dim]")


def _resolver_unico(texto, rol):
    ids = filtrar_paraderos(texto)
    if len(ids) == 1:
        return ids[0]
    console.print(f"[red]No se pudo resolver el {rol} '{texto}' ({len(ids)} coincidencias).[/red]")
    if ids:
        _listar(ids, f"{rol}: coincidencias", _tabla_paraderos)
    return None


def ejecutar_consulta(texto_origen, texto_destino):
    """Modo directo: resuelve ambos textos y muestra la ruta."""
    origen = _resolver_unico(texto_origen, "origen")
    if origen is None:
        sys.exit(1)
    destino = _resolver_unico(texto_destino, "destino")
    if destino is None:
        sys.exit(1)
    mostrar_viaje(origen, destino, _correr_busqueda(origen, destino))


def main():
    args = sys.argv[1:]
    if not args:
        menu()
        return

    comando = args[0].lower()
    if comando in ("-h", "--help", "help", "ayuda"):
        mostrar_ayuda()
    elif comando == "paraderos":
        _listar(filtrar_paraderos(" ".join(args[1:])), "Paraderos SITP", _tabla_paraderos)
    elif comando == "rutas":
        _listar(filtrar_rutas(" ".join(args[1:])), "Rutas SITP", _tabla_rutas)
    elif comando == "ruta":
        if len(args) < 2:
            console.print("[red]Uso:[/red] python3 src/main.py ruta <id>")
            sys.exit(1)
        coincidencias = filtrar_rutas(args[1])
        if len(coincidencias) != 1:
            console.print(f"[red]'{args[1]}' no corresponde a una única ruta.[/red]")
            _listar(coincidencias, "Rutas: coincidencias", _tabla_rutas)
            sys.exit(1)
        mostrar_detalle_ruta(coincidencias[0])
    elif comando == "buses":
        _listar(filtrar_rutas(" ".join(args[1:])), "Flota por ruta", _tabla_flota)
    elif comando in ("stats", "estadisticas"):
        ver_estadisticas()
    elif len(args) == 2:
        ejecutar_consulta(args[0], args[1])
    else:
        console.print("[red]Argumentos no reconocidos.[/red]\n")
        mostrar_ayuda()
        sys.exit(1)


if __name__ == "__main__":
    main()
