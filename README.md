# Laboratorio de enrutamiento adaptativo y Sink Tree

Aplicación educativa en **Python, Streamlit, Plotly y NetworkX** para construir grafos de routers y estudiar cómo cambian las rutas cuando varían las métricas de la red.

## Abrir en línea

https://infra-juan-fx2kntegiq2tgnvskmnk4b.streamlit.app/

## Funciones

- Añadir routers con nombres personalizados (hasta 100), eliminar routers y mover sus posiciones mediante coordenadas.
- Crear, modificar, activar, desactivar o eliminar conexiones.
- Editar **peso manual, retardo (ms), ancho de banda (Mbps), pérdida (%) y jitter (ms)** en cada enlace.
- Elegir origen, destino y el criterio que determina la ruta más óptima.
- Encontrar **hasta tres caminos simples de menor costo**, con NetworkX (algoritmo de Yen).
- Dibujar el **árbol sumidero** con Dijkstra, tomando el destino elegido como raíz.
- Comparar las rutas por costo, saltos, retardo total, ancho de banda mínimo y pérdida extremo a extremo estimada.
- Tres reglas de tráfico simulado: carga baja, carga variable y congestión.
- Actualización automática aproximadamente cada segundo con `st.fragment(run_every="1s")`.
- Bloquear métricas de un enlace para mantenerlas constantes durante la simulación.
- Restaurar la topología original de 15 routers.

## Criterios de optimización

Se pueden elegir por separado: peso manual, saltos, retardo, penalización inversa del ancho de banda, pérdida de paquetes, jitter y **adaptativo**.

El modo adaptativo usa una suma ponderada de componentes normalizados por enlace:

```text
costo = ws·1 + wp·(peso/100) + wr·(retardo/50)
        + wb·(100/ancho_Mbps) + wl·(perdida_%/2)
        + wj·(jitter/10)
```

Los coeficientes se ajustan en la barra lateral. El costo total de una ruta es la suma de los costos de sus enlaces. La opción de ancho de banda minimiza una **penalización inversa aditiva**: no garantiza maximizar estrictamente la capacidad mínima (cuello de botella) de la ruta.

## Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run main.py
```

En Windows, activa el entorno con `.venv\\Scripts\\activate`.

## Consideraciones

- Es una **simulación académica**, no recoge telemetría de routers reales ni configura Cisco.
- Los valores aleatorios de retardo, ancho de banda, jitter y pérdida representan escenarios ilustrativos.
- El grafo es interactivo para hacer zoom, desplazar y examinar enlaces; las posiciones de los routers se editan mediante el panel lateral, no arrastrando los nodos.
- Los cambios se guardan en la sesión del navegador; no se conservan automáticamente entre sesiones.
- El cálculo de las tres rutas se limita a tres soluciones para evitar enumerar todos los caminos simples.
