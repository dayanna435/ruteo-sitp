# Sistema Inteligente de Ruteo en el SITP (Bogotá)

Sistema basado en conocimiento (reglas lógicas) + búsqueda heurística (A*)
para calcular la ruta de menor tiempo entre dos paraderos del Sistema
Integrado de Transporte Público (SITP) de Bogotá, componente zonal (buses
urbanos, alimentadores y complementarios).

## Estructura del proyecto

```
ruta_transmilenio/
├── hechos.py          # Base de conocimiento: paraderos, rutas SITP, hechos "circula"
├── reglas.py          # Reglas lógicas: genera conexiones y calcula transbordos
├── motor_busqueda.py  # Algoritmo A* (búsqueda heurística) sobre el grafo lógico
├── main.py            # Interfaz de línea de comandos
└── README.md
```

## Datos utilizados

Los códigos y trazados de las rutas **Urbana 14**, **C11** y **Complementaria
18-8** corresponden a rutas reales del SITP, divulgadas públicamente por la
Alcaldía de Bogotá / Secretaría Distrital de Movilidad. Las coordenadas de
los paraderos son **aproximadas** (ubicación general del barrio o cruce, no
el poste exacto).

Para reemplazarlas por coordenadas oficiales exactas, el equipo puede usar
los datasets abiertos de TransMilenio S.A.:
- Rutas Zonales SITP: https://datosabiertos-transmilenio.hub.arcgis.com/datasets/rutas-zonales-sitp
- Paraderos Zonales del SITP: https://datosabiertos-transmilenio.hub.arcgis.com/datasets/paraderos-zonales-del-sitp
- Paraderos SITP (datos.gov.co): https://www.datos.gov.co/d/etwh-dt2e

## Requisitos

- Python 3.8 o superior (no requiere librerías externas).

## Ejecución

**Modo interactivo** (muestra la lista de paraderos y pide origen/destino):
```bash
python3 main.py
```

**Modo directo** (para pruebas rápidas o para el video):
```bash
python3 main.py <id_origen> <id_destino>
```

Ejemplo:
```bash
python3 main.py chapinero_central portal_americas
```

## Cómo funciona (resumen para el video)

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
   (dividida entre la velocidad comercial promedio del sistema), lo que
   garantiza una heurística admisible.

## Adaptar a datos reales completos

Este proyecto incluye solo 3 rutas como muestra representativa (el SITP
tiene cientos). Para ampliar la cobertura, reemplacen o completen
`PARADEROS` y `RUTAS` en `hechos.py` con los datos oficiales de los
datasets mencionados arriba (por ejemplo, cargándolos desde un archivo
GeoJSON/CSV en lugar de escribirlos a mano).

## Instrucciones para el repositorio Git (entrega)

1. Inicializar el repositorio y subirlo a GitHub/GitLab:
   ```bash
   git init
   git add .
   git commit -m "Estructura inicial del sistema de ruteo"
   git branch -M main
   git remote add origin <URL_DEL_REPOSITORIO>
   git push -u origin main
   ```
2. **Cada integrante debe realizar sus propios commits** desde su cuenta
   (por ejemplo: uno trabaja `hechos.py`, otro `reglas.py`, otro
   `motor_busqueda.py`, otro las pruebas y el README) para que el log del
   repositorio evidencie el aporte individual.
3. Agregar al tutor del curso como **colaborador** del repositorio
   (Settings → Collaborators en GitHub, o Members en GitLab).
4. Subir también el documento PDF de pruebas y el enlace del video en la
   entrega final.
