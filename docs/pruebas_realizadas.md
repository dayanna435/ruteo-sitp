# Documento de pruebas – Actividad 5 (Aprendizaje supervisado)

Proyecto: Rutero SITP (Bogotá)
Integrantes: [nombres de los 4 integrantes]

## 1. Componentes probados

1. **Modelo de clasificación del tipo de ruta** (`src/modelo_rutas.py`): árbol de decisión (profundidad 4) y Random Forest (200 árboles, para comparar). Clasifica una ruta como Zonal, Alimentador, Troncal u Otros a partir de 10 características calculadas con los datos GTFS.
2. **Buscador de rutas A\*** (`src/motor_busqueda.py`), del proyecto anterior: se probó con pares origen/destino reales.

## 2. Entorno de pruebas

- Python 3 con pandas, numpy, scikit-learn y matplotlib (`requirements.txt`).
- Semilla fija (`random_state=42`) para que los resultados sean reproducibles.
- Comando: `python src/modelo_rutas.py` (desde la raíz del repositorio).
- Salida completa guardada en `docs/pruebas_resultados_rutas.txt`.

## 3. Datos de prueba

- Fuente: GTFS del SITP procesado por `pipeline_gtfs.py` → `data/output/` (1.045 rutas, 8.159 paraderos).
- Dataset del modelo: `data/rutas_caracteristicas.csv` (1.045 filas, 12 columnas).
- Distribución: Zonal 713, Alimentador 175, Troncal 113, Otros 44 (Dual, Complementario, Especial y Cable agrupados).
- División estratificada: 783 rutas para entrenar (75 %) y **262 para probar (25 %)**, que el modelo no vio al entrenar.

## 4. Pruebas del modelo de clasificación

| # | Prueba | Cómo se hizo | Resultado |
|---|---|---|---|
| 1 | Carga y validación de datos | `cargar_datos()` sobre los JSON | Carga sin errores |
| 2 | Construcción del dataset | Una fila por ruta, 10 variables | CSV de 1.045 filas × 12 columnas |
| 3 | Exactitud en datos de prueba | 262 rutas no vistas | Árbol **77,1 %**; Random Forest **91,2 %** |
| 4 | Validación cruzada (5 particiones) | `cross_val_score` | 65,6 %, 83,7 %, 80,9 %, 65,6 %, 78,9 % |
| 5 | Métricas por clase | `classification_report` | Ver sección 4.1 |
| 6 | Matriz de confusión | `confusion_matrix` | Ver sección 4.2 |
| 7 | Importancia de variables | `feature_importances_` | Paraderos únicos 39 %; distancia entre extremos 26 %; longitud del recorrido 21 % |
| 8 | Casos individuales | 8 rutas del conjunto de prueba | Ver sección 4.3 |

### 4.1 Métricas por clase (árbol de decisión)

| Clase | Precisión | Recall | F1 | Rutas de prueba |
|---|---|---|---|---|
| Alimentador | 0,52 | 0,77 | 0,62 | 44 |
| Otros | 0,26 | 0,55 | 0,35 | 11 |
| Troncal | 0,84 | 0,93 | 0,88 | 28 |
| Zonal | 0,96 | 0,76 | 0,85 | 179 |

### 4.2 Matriz de confusión (filas = real, columnas = predicho)

| Real \ Predicho | Alimentador | Otros | Troncal | Zonal |
|---|---|---|---|---|
| Alimentador | 34 | 5 | 1 | 4 |
| Otros | 2 | 6 | 1 | 2 |
| Troncal | 0 | 2 | 26 | 0 |
| Zonal | 30 | 10 | 3 | 136 |

### 4.3 Casos individuales (entrada → salida)

| # | Ruta | Paraderos | Distancia entre extremos (km) | Recorrido (km) | Tipo real | Tipo predicho | ¿Acertó? |
|---|---|---|---|---|---|---|---|
| 1 | 12841 | 19 | 10,57 | 12,42 | Troncal | Troncal | Sí |
| 2 | 10980 | 6 | 2,01 | 2,18 | Alimentador | Alimentador | Sí |
| 3 | 10660 | 127 | 0,01 | 41,36 | Zonal | Zonal | Sí |
| 4 | 13184 | 47 | 0,00 | 41,84 | Otros | Otros | Sí |
| 5 | 13307 | 27 | 19,06 | 20,75 | Troncal | Otros | No |
| 6 | 12806 | 10 | 0,00 | 6,10 | Alimentador | Otros | No |
| 7 | 12964 | 156 | 0,09 | 59,01 | Zonal | Otros | No |
| 8 | 12491 | 129 | 0,00 | 44,92 | Otros | Zonal | No |

## 5. Pruebas del buscador de rutas (origen → destino)

| # | Origen | Destino | Resultado esperado | Resultado obtenido |
|---|---|---|---|---|
| 1 | Estación Calle 72 (`57639`) | Estación Museo Nacional (`57898`) | Ruta encontrada | Encontrada: 35,9 min, 18 tramos, 1 transbordo |
| 2 | Portal Norte T1 (`61235`) | Portal Sur (`52150`) | Ruta encontrada | Encontrada: 112,8 min, 47 tramos, 5 transbordos |
| 3 | Portal 80 T-1A (`73223`) | Estación Museo Nacional (`57898`) | Ruta encontrada | Encontrada: 55,2 min, 15 tramos, 4 transbordos |
| 4 | Paradero inexistente (`99999`) | Cualquiera | Rechazo controlado | La función devuelve `None` (paradero no encontrado) |
| 5 | Un paradero | El mismo paradero | Ruta vacía | La función devuelve ruta con 0 tramos y 0,0 min |

Los casos 1 a 3 se ejecutaron con los datos reales. Los casos 4 y 5 corresponden al comportamiento definido en `buscar_ruta()`; **verifíquenlos ejecutándolos antes de entregar**.

## 6. Análisis de resultados

- **Funciona bien:** las rutas troncales (26 de 28 acertadas, recall 0,93) y la precisión de la clase Zonal (0,96).
- **Errores principales:** 30 rutas zonales se clasificaron como alimentadoras por tener recorridos parecidos; la clase Otros casi no se aprende (precisión 0,26) porque agrupa tipos muy distintos y solo tiene 44 rutas.
- **Rutas circulares:** varias rutas tienen distancia entre extremos cercana a 0 km (casos 3, 4, 6, 7 y 8) porque empiezan y terminan en el mismo lugar. Esa variable no las distingue bien, lo que explica parte de los errores.
- **Estabilidad:** la validación cruzada del árbol varía entre 66 % y 84 %, así que depende de cómo se reparten los datos. El Random Forest (91 %) es más robusto.
- **Interpretabilidad:** el árbol aprendió reglas coherentes con el sistema: las alimentadoras son cortas y las troncales cubren distancias largas.

## 7. Limitaciones y mejoras

- Pocas rutas en las clases minoritarias.
- Las características no incluyen la ubicación de los paraderos ni los transbordos.
- Se podrían probar más variables, otros modelos o reagrupar la clase Otros.

## 8. Evidencias

- `docs/pruebas_resultados_rutas.txt`: salida completa de la ejecución.
- `docs/arbol_decision_rutas.png`: árbol de decisión.
- `data/rutas_caracteristicas.csv`: dataset usado.
