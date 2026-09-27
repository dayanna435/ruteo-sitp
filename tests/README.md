# Pruebas

Pruebas unitarias escritas con `unittest` de la biblioteca estándar, porque el
proyecto no tiene dependencias externas y `pytest` no está instalado.

## Correr todo

Desde la raíz del repositorio:

```bash
python3 -m unittest discover -s tests -v
```

## Correr un solo archivo

```bash
python3 -m unittest discover -s tests -p "test_reglas.py" -v
```

## Cobertura

| Archivo | Qué verifica |
|---|---|
| `test_cargador_datos.py` | Validación del JSON: claves, rangos, paraderos inexistentes, constantes, circulares, variable de entorno `RUTEO_SITP_DATA`. |
| `test_reglas.py` | Reglas 1, 2 y 3: arcos bidireccionales, circular unidireccional con cierre, penalización por transbordo, `regla_meta`, `reconstruir_grafo`. |
| `test_motor_busqueda.py` | A*: resultados conocidos, optimalidad contra un Dijkstra de referencia, continuidad del camino, heurística admisible, `distancia_km`. |
| `test_hechos.py` | Forma de la base de conocimiento y coherencia entre paraderos, rutas y constantes. |

## Nota sobre `sys.path`

Los módulos de `src/` se importan por nombre plano (`from hechos import ...`)
porque `src/` no es un paquete. Cada archivo de prueba inserta `src/` en
`sys.path` al inicio; sin eso los imports fallan.
