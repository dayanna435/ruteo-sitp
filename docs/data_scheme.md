# Diccionario de Datos (`data/output/`)

Los archivos crudos del estándar GTFS (`data/gtfs/`) se procesan con
`src/pipeline_gtfs.py` para generar cuatro archivos JSON **optimizados** (todos
son listas de objetos) que alimentan el motor de inferencia y búsqueda a través
de `cargador_datos.py`.

Ejecución del pipeline:

```sh
python3 src/pipeline_gtfs.py [--entrada data/gtfs] [--salida data/output]
```

## 1. `paraderos.json`

Catálogo de puntos de abordaje (estaciones y paraderos) de la ciudad.

```json
[
  {
    "id_paradero": "52601",
    "nombre": "IED Paraíso Mirador",
    "latitud": 4.553264,
    "longitud": -74.158793,
    "tipo": "zonal"
  }
]
```

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `id_paradero` | texto | sí | Identificador único (`stop_id`). |
| `nombre` | texto | sí | Nombre del paradero (`stop_name`). |
| `latitud` | número | sí | Latitud en grados decimales, en `[-90, 90]`. |
| `longitud` | número | sí | Longitud en grados decimales, en `[-180, 180]`. |
| `tipo` | texto | no | `"troncal"` o `"zonal"`. |

## 2. `rutas.json`

Información de las rutas, incluyendo la secuencia de paraderos de su trazado
(el viaje representativo de más paraderos; ver `pipeline_gtfs.py`).

```json
[
  {
    "id_ruta": "10039",
    "nombre_largo": "Museo Nacional",
    "tipo": "Troncal",
    "dias_operacion": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"],
    "horario_inicio": "04:00",
    "horario_fin": "04:41",
    "secuencia_paraderos": ["73512", "61752", "61740"],
    "es_circular": false
  }
]
```

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `id_ruta` | texto | sí | Identificador único (`route_id`). |
| `secuencia_paraderos` | lista | sí | ≥ 2 ids de paraderos, sin repetidos consecutivos. |
| `nombre_largo` | texto | no | Nombre descriptivo de la ruta. |
| `tipo` | texto | no | `Troncal`, `Zonal`, `Alimentador`, `Complementario`, `Especial`, `Dual` o `Cable`. |
| `dias_operacion` | lista | no | Días en que opera, en español. |
| `horario_inicio` / `horario_fin` | texto | no | Horario del viaje representativo (`HH:MM`). |
| `es_circular` | booleano | no | `true` si el trazado solo se recorre en un sentido. Por defecto `false`. |

> Las rutas **no circulares** se tratan como bidireccionales en `reglas.py`; las
> circulares solo en el sentido de la secuencia.

## 3. `buses.json`

Flota de referencia asignada a cada ruta. **Opcional** (si no existe, no hay
datos de flota).

```json
[
  {
    "id_ruta": "10039",
    "tipo_vehiculo": "Bus",
    "capacidad_promedio": 80
  }
]
```

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `id_ruta` | texto | sí | Debe existir en `rutas.json`. |
| `tipo_vehiculo` | texto | no | `Bus`, `Teleférico`, `Tranvía`, `Metro` o `Tren`. |
| `capacidad_promedio` | número | no | Capacidad estimada de referencia. |

## 4. `constantes.json`

Parámetros globales del sistema y penalizaciones del algoritmo de búsqueda. Es
una lista con un único objeto.

```json
[
  {
    "tiempo_entre_paraderos": 1.549,
    "tiempo_transbordo": 8.0,
    "velocidad_comercial_promedio_kmh": 15.58
  }
]
```

| Campo | Tipo | Obligatorio | Descripción |
| --- | --- | --- | --- |
| `tiempo_entre_paraderos` | número > 0 | sí | Minutos por tramo (mediana estimada del feed). |
| `tiempo_transbordo` | número > 0 | sí | Minutos de penalización por cambio de ruta. |
| `velocidad_comercial_promedio_kmh` | número > 0 | sí | Velocidad comercial promedio (km/h). El cargador la normaliza a km/min para la heurística de A*. |

## Validación

`cargador_datos.validar()` normaliza estas listas a las estructuras en memoria
que consume el sistema y verifica la integridad referencial (rutas que apuntan a
paraderos existentes, buses de rutas existentes) con mensajes de error que
señalan el elemento exacto que falla.
