# Guía de Pipeline y Procesamiento GTFS

Este documento describe cómo se transforman los archivos estáticos GTFS oficiales de TransMilenio en los JSON estructurados que consume el proyecto.

## 1. Origen de los Datos
* **Fuente:** Portal de Datos Abiertos de TransMilenio (GTFS Estáticos).
* **Versión actual utilizada:** `2026-09-29`
* **Ubicación de archivos fuente:** `data/gtfs/`

## 2. Archivos GTFS Involucrados en la Extracción
* `routes.txt`: Extrae los identificadores y nombres de las rutas.
* `trips.txt` y `calendar.txt`: Cruzan las rutas con los días de la semana y calendarios de operación válidos.
* `stops.txt`: Extrae las coordenadas geográficas (`stop_lat`, `stop_lon`) y nombres de los paraderos.
* `stop_times.txt` / `frequencies.txt`: Procesan los tiempos de recorrido y frecuencias horarias.

## 3. Proceso de Limpieza y Conversión

El procesamiento lo realiza `src/pipeline_gtfs.py`:

```sh
python3 src/pipeline_gtfs.py [--entrada data/gtfs] [--salida data/output]
```

1. **Lectura relacional:** se relacionan `route_id`, `trip_id` y `stop_id` de
   `routes.txt`, `trips.txt` y `stop_times.txt`.
2. **Selección del trazado:** para cada ruta se elige el viaje con más paraderos
   como secuencia representativa (las rutas se recorren en ambos sentidos en
   `reglas.py`, salvo las circulares). Se descartan estaciones (`location_type`
   1) que no son puntos de abordaje.
3. **Estimación de parámetros:** `tiempo_entre_paraderos` y la velocidad
   comercial promedio se estiman de los tiempos reales de `stop_times.txt`;
   `tiempo_transbordo` se fija por defecto.
4. **Serialización:** se exportan los datos limpios hacia `data/output/`
   (`paraderos.json`, `rutas.json`, `constantes.json`, `buses.json`) listos para
   ser consumidos por `cargador_datos.py`.

El esquema exacto de cada archivo está en `docs/data_scheme.md`.
