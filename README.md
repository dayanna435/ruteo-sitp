<div align="center">

  # Sistema Inteligente de Ruteo en el SITP (Bogotá)

  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./docs/images/sir-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="./docs/images/sir-light.png">
    <img src="./docs/image/sir-light.png" alt="banner">
  </picture>
  <br>
  <p>
    <a href="https://github.com/dayanna435/ruteo-sitp/issues">
      <img src="https://img.shields.io/github/issues/dayanna435/ruteo-sitp" alt="Issues">
    </a>
    <a href="https://github.com/dayanna435/ruteo-sitp/stargazers">
      <img src="https://img.shields.io/github/stars/dayanna435/ruteo-sitp" alt="Stars">
    </a>
  </p>
</div>

## Sobre el proyecto:
**Proyecto AcademicoAplicación de línea de comandos (CLI) basada en inteligencia artificial y procesamiento de datos para calcular la ruta óptima de transporte entre paraderos del Sistema Integrado de Transporte Público (SITP) de Bogotá, incluyendo sugerencias automáticas de transbordos cuando no existe una ruta directa.

<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=git,github,githubactions,python" />
  </a>
</p>

## Estructura del proyecto

```plaintext
ruteo-sitp/
├── data/
│   ├── gtfs/                 # Archivos GTFS estáticos oficiales (2026-09-29)
│   │   ├── agency.txt
│   │   ├── calendar_dates.txt
│   │   ├── calendar.txt
│   │   ├── fare_attributes.txt
│   │   ├── feed_info.txt
│   │   ├── frequencies.txt
│   │   ├── routes.txt
│   │   ├── shapes.txt
│   │   ├── stops.txt
│   │   ├── stop_times.txt
│   │   └── trips.txt
│   └── output/               # Datos procesados listos para el motor
│       ├── buses.json
│       ├── constantes.json
│       ├── paraderos.json
│       └── rutas.json
├── docs/
├── src/                      # Lógica principal del sistema y CLI
├── tests/                    # Pruebas unitarias del sistema
├── README.md
└── requirements.txt
```

## Fuentes de Datos (GTFS)

El sistema utiliza los Datos Abiertos GTFS Estáticos de TransMilenio (versión del 29 de septiembre de 2026), ubicados en la carpeta data/gtfs/.

Mediante `src/pipeline_gtfs.py`, estos archivos planos se transforman y normalizan en los archivos optimizados de la carpeta data/output/:

```sh
python3 src/pipeline_gtfs.py
```

- buses.json: Información detallada de la flota y asignaciones.
- constantes.json: Parámetros de configuración del sistema de ruteo.
- paraderos.json: Catálogo completo de paraderos y estaciones con sus coordenadas y códigos únicos.
- rutas.json: Trazados, días de disponibilidad y horarios de las rutas zonales y troncales.

## Requisitos

- Python 3.8 o superior.
- Dependencias descritas en requirements.txt.

## Ejecución (Interfaz de Línea de Comandos - CLI)

Todos los comandos deben ejecutarse **desde la raíz del repositorio**.

**1. Modo interactivo:**

El sistema despliega una interfaz de apoyo donde el usuario puede consultar paraderos y seleccionar su punto de partida y destino de forma guiada:

```sh
python3 src/main.py
```

**2. Modo directo:**

Para consultas rápidas indicando el origen y el destino. Cada argumento puede ser el id del paradero o un fragmento único de su nombre:

```sh
python3 src/main.py <origen> <destino>
```

Ejemplos de uso:

```sh
python3 src/main.py 49841 61235
python3 src/main.py "Portal Norte" "Museo Nacional"
```

**3. Subcomandos de consulta:**

No hace falta conocer el id exacto: se puede buscar por fragmento de nombre y ver los ids disponibles.

```sh
python3 src/main.py paraderos [filtro]   # catálogo de paraderos e ids
python3 src/main.py rutas [filtro]       # rutas disponibles y su detalle
python3 src/main.py ruta <id>            # secuencia completa de una ruta
python3 src/main.py buses [filtro]       # flota asignada por ruta
python3 src/main.py stats                # estadísticas de la red
python3 src/main.py --help               # ayuda
```

En el **menú interactivo** el usuario puede buscar por nombre parcial, navegar
los resultados paginados y elegir un paradero **por número**, por lo que nunca
necesita escribir el id o el nombre exactos. El menú además permite ver
paraderos e ids, rutas y su detalle, la flota de buses y estadísticas de la red.

## ¿Cómo funciona el Sistema?

1. **Procesamiento de Datos:** Ingiere y valida el formato GTFS normalizado, estructurándolo en JSON eficientes para su consulta rápida en memoria.

2. **Asesoría de Rutas:** Analiza la red de transporte disponible evaluando tiempos, frecuencias y días de operación válidos.

3. **Optimización y Transbordos:** Calcula el trayecto óptimo. Si no existe una ruta directa que conecte el origen con el destino, el sistema procesa automáticamente las combinaciones posibles y sugiere las opciones de transbordo más eficientes para completar el viaje.

---
