# Simulador de rutas óptimas y Sink Tree

Simulador académico de una red de **15 routers** desarrollado en **Python + Streamlit + Plotly**.

## Funciones

- Selección de origen y destino.
- Cálculo de las **tres rutas simples de menor costo** mediante búsqueda de costo uniforme con cola de prioridad.
- Árbol sumidero hacia el destino utilizando el algoritmo de Dijkstra.
- Visualización de los pesos de cada enlace y edición manual.
- Simulación de enlaces dañados y recuperados.
- Modos de pesos aleatorios (carga baja, variable y congestión).
- Simulación automática que modifica cada segundo los pesos de los enlaces no bloqueados.
- Panel para consultar los pasos del algoritmo.

## Instalación y ejecución

En macOS o Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

En Windows, activa el entorno con `.venv\\Scripts\\activate`.

La aplicación suele abrirse en `http://localhost:8501`.

## Explicación de los algoritmos

La red se modela como un grafo no dirigido, con costo positivo en cada enlace. La **búsqueda de costo uniforme** genera caminos sin repetir nodos y utiliza una cola de prioridad para extraer primero el candidato con menor costo acumulado. Las primeras tres soluciones que llegan al destino son los tres caminos simples más baratos, aunque pueden compartir enlaces.

**Dijkstra** calcula el costo mínimo desde cada nodo hacia el destino elegido. El siguiente salto de cada nodo define el árbol sumidero para los nodos alcanzables.

Los costos aleatorios son **datos simulados**, no mediciones reales de routers Cisco. El programa vuelve a calcular los resultados con cada actualización; no configura equipos físicos.

## Archivos

- `main.py`: interfaz, topología y algoritmos.
- `requirements.txt`: dependencias.

