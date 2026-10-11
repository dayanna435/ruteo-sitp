# Guía de Interfaz CLI: Rich para el Sistema de Transporte Público

Este documento describe la interfaz de línea de comandos (CLI) del sistema de
transporte público implementada en `src/main.py` y las decisiones de diseño
detrás de ella.

---

## 1. ¿Por qué Rich?

La CLI se apoya en **Rich** para la capa visual: colores, paneles, tablas
estructuradas, paginación y prompts guiados. Rich convierte una salida de texto
plano en una aplicación de terminal clara, con jerarquía visual:

*   **Paneles** (`Panel`) para resúmenes: bienvenida, resultado del viaje,
    resumen de la red.
*   **Tablas** (`Table`) para listados: paraderos, rutas, flota, secuencias y
    tramos del trayecto.
*   **Preguntas** (`Prompt`) para entrada de datos validada (`choices`).
*   **Indicador de progreso** (`console.status`) mientras el motor A* calcula
    la ruta (solo en terminal interactiva).

> Nota: aunque la documentación original proponía Typer, se optó por un
> enrutador de comandos ligero en `main.py` para **preservar el contrato
> previo** (`main.py <origen> <destino>`) sin renombrar el ejecutable ni forzar
> subcomandos. Rich es la dependencia que aporta el valor visual.

Colores usados de forma consistente:

| Color     | Significado                            |
| --------- | -------------------------------------- |
| `cyan`    | Identificadores (ids de ruta/paradero) |
| `green`   | Éxito / origen                         |
| `magenta` | Información secundaria (tipo)          |
| `yellow`| Advertencia / transbordo          |
| `red`  | Error                              |

---

## 2. Menú inicial interactivo

Al ejecutar `python3 src/main.py` sin argumentos se abre un menú en bucle:

```
[1] Planear un viaje (origen -> destino)
[2] Buscar / ver paraderos e IDs
[3] Ver rutas y su detalle
[4] Ver flota de buses
[5] Estadísticas de la red
[6] Ayuda
[7] Salir
```

Cada acción está envuelta en manejo de errores: la CLI nunca se cae por una
entrada inválida y `Ctrl-C`/`EOF` cancelan la acción en curso y vuelven al menú.

---

## 3. El problema y la mejora: elegir sin id ni nombre exactos

Antes, si el usuario no conocía el id ni el nombre exacto del paradero, no podía
introducir datos. Ahora el **selector de paraderos** permite:

1.  Buscar por **fragmento de nombre** (insensible a mayúsculas y acentos) o por
    id parcial.
2.  Dejar la búsqueda **vacía para ver todos** los paraderos, paginados de 15 en
    15.
3.  Navegar con `n` (siguiente) y `p` (anterior), reescribir la búsqueda con `b`
    o elegir **escribiendo el número** de fila.
4.  Cancelar con `q`.

Así el usuario puede descubrir el id disponible en la tabla y seleccionarlo por
posición. El mismo patrón se reutiliza para explorar rutas.

El uso del menú `[2]` muestra además, por cada paradero elegido, sus
coordenadas, tipo y la lista de rutas que lo sirven.

---

## 4. Subcomandos de consulta (no interactivos)

Para automatizar o consultar rápido sin menú:

| Comando              | Descripción                                    |
| -------------------- | ---------------------------------------------- |
| `paraderos [filtro]` | Lista paraderos e ids (60 máximo por pantalla) |
| `rutas [filtro]`     | Lista rutas disponibles                        |
| `ruta <id>`          | Detalle y secuencia completa de una ruta       |
| `buses [filtro]`     | Flota (vehículo y capacidad) por ruta          |
| `stats`              | Estadísticas de la red                         |
| `--help`             | Ayuda                                          |
| `<origen> <destino>` | Viaje óptimo (modo directo heredado)           |

---

## 5. Presentación del trayecto

El resultado combina:

*   Un panel indicando si existe **conexión directa** (y en qué rutas) o si se
    calcularon **transbordos**.
*   Una tabla de **tramos de bus**: sube en / baja en (con nombre e id), ruta
    (con nombre largo), número de paradas, tiempo y la espera por transbordo.
*   Un panel de resumen: tiempo total, arcos y transbordos.
*   Una nota con los parámetros del modelo (velocidad comercial, tiempo entre
    paraderos y penalización por transbordo).

---

## 6. Próximos pasos

*   Persistir las últimas búsquedas del usuario para autocompletar.
*   Exportar el trayecto a un archivo (JSON/Markdown) desde un nuevo subcomando.
*   Integrar `rareza`/edición en vivo de parámetros con un panel de configuración.
