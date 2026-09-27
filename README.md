# Sistema Inteligente de Ruteo en el SITP (Bogotá)

Sistema basado en conocimiento (reglas lógicas) + búsqueda heurística (A*)
para calcular la ruta de menor tiempo entre dos paraderos del Sistema
Integrado de Transporte Público (SITP) de Bogotá, componente zonal (buses
urbanos, alimentadores y complementarios).

## Estructura del proyecto

```
ruteo-sitp/
├── data
│   └── data.json
├── docs
├── README.md
├── requirements.txt
├── src
│   ├── cargador_datos.py
│   ├── hechos.py
│   ├── main.py
│   ├── motor_busqueda.py
│   ├── __pycache__
│   │   ├── cargador_datos.cpython-314.pyc
│   │   ├── hechos.cpython-314.pyc
│   │   ├── main.cpython-314.pyc
│   │   ├── motor_busqueda.cpython-314.pyc
│   │   └── reglas.cpython-314.pyc
│   └── reglas.py
└── tests
    ├── __pycache__
    │   ├── test_cargador_datos.cpython-314.pyc
    │   ├── test_hechos.cpython-314.pyc
    │   ├── test_motor_busqueda.cpython-314.pyc
    │   └── test_reglas.cpython-314.pyc
    ├── README.md
    ├── test_cargador_datos.py
    ├── test_hechos.py
    ├── test_motor_busqueda.py
    └── test_reglas.py
```

La base de conocimiento se lee de `data/data.json`, que es el único lugar donde hay que editar o ampliar paraderos,rutas y constantes. Al arrancar, `cargador_datos.py` valida el archivo (claves obligatorias, rangos de coordenadas, paraderos referenciados que existan, constantes positivas) y falla con un mensaje claro si algo no cuadra.

## Datos utilizados

Los códigos y trazados de las rutas **Urbana 14**, **C11** y **Complementaria 18-8** corresponden a rutas reales del SITP, divulgadas públicamente por la Alcaldía de Bogotá / Secretaría Distrital de Movilidad. Las coordenadas de los paraderos son **aproximadas** (ubicación general del barrio o cruce, no el poste exacto).

Para reemplazarlas por coordenadas oficiales exactas, se puede usar los datasets abiertos de TransMilenio S.A.:
- Rutas Zonales SITP: https://datosabiertos-transmilenio.hub.arcgis.com/datasets/rutas-zonales-sitp
- Paraderos Zonales del SITP: https://datosabiertos-transmilenio.hub.arcgis.com/datasets/paraderos-zonales-del-sitp
- Paraderos SITP (datos.gov.co): https://www.datos.gov.co/d/etwh-dt2e

## Requisitos

- Python 3.8 o superior (no requiere librerías externas).

## Ejecución

Todos los comandos se ejecutan **desde la raíz del repositorio**.

**Modo interactivo** (muestra la lista de paraderos y pide origen/destino):
```bash
python3 src/main.py
```

**Modo directo** (para pruebas rápidas o para el video):
```bash
python3 src/main.py <id_origen> <id_destino>
```

Ejemplo:
```bash
python3 src/main.py chapinero_central portal_americas
```

## Cómo funciona? (resumen del video)

1. **Base de conocimiento** (`hechos.py`): declara los paraderos (id, nombre,
   coordenadas) y las rutas SITP como secuencias de paraderos. Esto equivale
   al predicado lógico `circula(ParaderoA, ParaderoB, Ruta, Tiempo)`.
2. **Reglas** (`reglas.py`):
   - Regla de circulación directa: genera automáticamente todas las
     conexiones entre paraderos consecutivos de una misma ruta (bidireccional,
     salvo las rutas circulares como la 18-8, que solo van en un sentido).
   - Regla de transbordo: si el siguiente tramo usa una ruta distinta a la
     actual, se penaliza el costo con un tiempo adicional (bajarse y esperar
     el siguiente bus).
   - Regla de meta: determina cuándo se llegó al destino.
3. **Motor de búsqueda** (`motor_busqueda.py`): aplica A*, usando como
   heurística la distancia geográfica en línea recta hasta el destino
   (dividida entre la velocidad comercial promedio del sistema), acotada por
   el costo del tramo más barato. Ese acotamiento hace que la heurística sea
   **admisible** (nunca sobreestima el tiempo restante), que es la condición
   para que A* devuelva siempre la ruta más rápida.

## Adaptar a datos reales completos

Este proyecto incluye solo 3 rutas como muestra representativa (el SITP tiene cientos). Para ampliar la cobertura, modificar `data/data.json` (el formato está documentado al inicio de `src/cargador_datos.py`) y, si se prefiere, generen ese archivo desde los datasets oficiales en lugar de escribirlo a mano: `cargador_datos.py` es el único módulo que abre archivos, así que también puede leer el GeoJSON/CSV original y convertirlo a las mismas estructuras sin tocar `hechos.py`, `reglas.py` ni `motor_busqueda.py`.
