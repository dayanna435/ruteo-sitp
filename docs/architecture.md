# Arquitectura del Sistema - Ruteo SITP

Este documento describe la arquitectura de software y el flujo de procesamiento del sistema inteligente de ruteo para el SITP de Bogotá.

## 1. Diagrama de Flujo General

```text
[ Datos GTFS (Entrada .txt) ] 
       │
       ▼
[ Pipeline de Procesamiento / Normalización ] 
       │
       ▼
[ Archivos JSON Optimizados (data/output/) ]
       │
       ▼
[ Cargador de Datos (cargador_datos.py) ] ──> Valida esquemas y reglas de negocio
       │
       ▼
[ Motor de Búsqueda & Inferencia (A* y Reglas) ] ──> Calcula rutas óptimas y transbordos
       │
       ▼
[ Interfaz de Línea de Comandos (CLI - main.py) ] ──> Interacción con el Usuario
```
## 2. Componentes Principales (src/)
- `pipeline_gtfs.py:` Aplana el feed GTFS de `data/gtfs/` en los JSON optimizados de `data/output/` (`paraderos`, `rutas`, `constantes`, `buses`), estimando tiempos y velocidad comercial de los `stop_times` reales.
- `cargador_datos.py:` Encargado de leer, validar e inyectar en memoria los datos procesados desde la carpeta `data/output/`. Realiza validaciones de integridad (coordenadas válidas, existencia de paraderos, tipos de datos).
- `hechos.py`: Define la representación de la red de transporte (paraderos, nodos, arcos y conexiones directas de las rutas zonales y troncales).
- `reglas.py`: Contiene las reglas lógicas del dominio:
    - Reglas de circulación directa entre paraderos consecutivos.
    - Reglas de penalización y gestión de transbordos (activadas cuando no existe una conexión directa).
- `motor_busqueda.py`: Implementa el algoritmo de búsqueda heurística A*. Utiliza una función de costo basada en tiempos estimados de viaje y una heurística admisible (distancia geográfica en línea recta dividida por la velocidad comercial promedio) para garantizar el camino más rápido.
- `main.py`: Punto de entrada de la aplicación que gestiona la Interfaz de Línea de Comandos (CLI), permitiendo tanto modo interactivo como consultas directas por parámetros.

---
