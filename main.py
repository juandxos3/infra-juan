import heapq
import math
import random

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Simulador Sink Tree", page_icon="🌐", layout="wide")

POS = {
    "A": (1, 8), "B": (5, 9), "C": (9, 8), "D": (3, 6),
    "E": (6, 6), "F": (1, 5), "G": (2, 4), "H": (4, 3),
    "I": (5, 5), "J": (8, 5), "K": (1, 2), "L": (3, 2),
    "M": (5, 1), "N": (9, 3), "O": (10, 1),
}
LINKS = [
    ("A", "B"), ("B", "C"), ("A", "D"), ("A", "F"),
    ("D", "G"), ("D", "H"), ("D", "I"), ("F", "K"),
    ("K", "L"), ("G", "L"), ("L", "M"), ("H", "E"),
    ("E", "J"), ("H", "O"), ("O", "N"), ("N", "J"),
    ("N", "M"), ("I", "J"), ("I", "C"), ("J", "C"),
]
COLORES = ["#e5484d", "#287bd3", "#1f9d6a"]
RANGOS = {"Carga baja": (10, 55), "Carga variable": (35, 140),
          "Congestión": (110, 300)}


def clave(a, b):
    return tuple(sorted((a, b)))


def nueva_red(escenario="Carga variable"):
    minimo, maximo = RANGOS[escenario]
    return {clave(a, b): {"peso": random.randint(minimo, maximo),
                           "activo": True, "fijo": False}
            for a, b in LINKS}


def iniciar():
    s = st.session_state
    if "enlaces" not in s:
        s.enlaces = nueva_red()
    if "activo_sim" not in s:
        s.activo_sim = False
    if "ciclos" not in s:
        s.ciclos = 0
    if "historial" not in s:
        s.historial = []
    if "enlace_ui" not in s:
        s.enlace_ui = "A - B"
    if "peso_ui" not in s:
        s.peso_ui = s.enlaces[clave("A", "B")]["peso"]
    if "fijo_ui" not in s:
        s.fijo_ui = False


def enlace_actual():
    a, b = st.session_state.enlace_ui.split(" - ")
    return clave(a, b)


# Los callbacks modifican widgets ANTES de instanciarlos: evita
# StreamlitWidgetAlreadyInstantiatedError.
def sincronizar_editor():
    dato = st.session_state.enlaces[enlace_actual()]
    st.session_state.peso_ui = dato["peso"]
    st.session_state.fijo_ui = dato["fijo"]


def guardar_peso():
    st.session_state.enlaces[enlace_actual()]["peso"] = int(st.session_state.peso_ui)


def guardar_bloqueo():
    st.session_state.enlaces[enlace_actual()]["fijo"] = bool(st.session_state.fijo_ui)


def cambiar_enlace():
    dato = st.session_state.enlaces[enlace_actual()]
    dato["activo"] = not dato["activo"]


def reiniciar():
    s = st.session_state
    s.enlaces = nueva_red(s.escenario_ui)
    s.ciclos = 0
    s.historial = []
    sincronizar_editor()


def pausar():
    if not st.session_state.activo_sim:
        sincronizar_editor()


def grafo():
    g = {n: [] for n in POS}
    for (a, b), dato in st.session_state.enlaces.items():
        if dato["activo"]:
            g[a].append((b, dato["peso"]))
            g[b].append((a, dato["peso"]))
    for vecinos in g.values():
        vecinos.sort()
    return g


def tres_rutas(g, origen, destino):
    """Búsqueda de costo uniforme: 3 caminos SIMPLES de menor suma de pesos."""
    cola = [(0, (origen,))]
    soluciones, pasos = [], []
    numero = 0
    while cola and len(soluciones) < 3:
        costo, camino = heapq.heappop(cola)
        numero += 1
        if len(pasos) < 180:
            pasos.append({"Paso": numero, "Decisión": "Extraer menor costo",
                          "Camino": " → ".join(camino), "Costo": costo})
        if camino[-1] == destino:
            soluciones.append((costo, camino))
            if len(pasos) < 180:
                pasos.append({"Paso": numero, "Decisión": "Ruta encontrada",
                              "Camino": " → ".join(camino), "Costo": costo})
            continue
        for vecino, peso in g[camino[-1]]:
            if vecino not in camino:
                nuevo = camino + (vecino,)
                heapq.heappush(cola, (costo + peso, nuevo))
                if len(pasos) < 180:
                    pasos.append({"Paso": numero, "Decisión": f"Extender (+{peso})",
                                  "Camino": " → ".join(nuevo), "Costo": costo + peso})
    return soluciones, pasos


def dijkstra(g, destino):
    """Distancias mínimas hacia la raíz y siguiente salto coherente sin bucles."""
    dist = {n: math.inf for n in g}
    siguiente = {}
    dist[destino] = 0
    cola = [(0, destino)]
    while cola:
        d, actual = heapq.heappop(cola)
        if d != dist[actual]:
            continue
        for vecino, peso in g[actual]:
            nuevo = d + peso
            if nuevo < dist[vecino]:
                dist[vecino] = nuevo
                siguiente[vecino] = actual
                heapq.heappush(cola, (nuevo, vecino))
            elif nuevo == dist[vecino] and actual < siguiente.get(vecino, "~"):
                siguiente[vecino] = actual
    return dist, siguiente


def variar_pesos(variacion):
    for dato in st.session_state.enlaces.values():
        if dato["activo"] and not dato["fijo"]:
            dato["peso"] = min(100000, max(1, dato["peso"] +
                                            random.randint(-variacion, variacion)))


def dibujar(rutas, siguientes, vista, origen, destino):
    fig = go.Figure()
    marcado = {}
    if vista == "Árbol sumidero":
        marcado = {clave(a, b): "#9850d8" for a, b in siguientes.items()}
    else:
        opciones = {"Tres rutas": [0, 1, 2], "Primaria": [0],
                    "Secundaria": [1], "Terciaria": [2]}
        for i in reversed(opciones[vista]):
            if i < len(rutas):
                camino = rutas[i][1]
                for a, b in zip(camino, camino[1:]):
                    marcado[clave(a, b)] = COLORES[i]

    for (a, b), dato in sorted(st.session_state.enlaces.items()):
        x1, y1 = POS[a]
        x2, y2 = POS[b]
        destacado = (a, b) in marcado and dato["activo"]
        color = marcado[(a, b)] if destacado else (
            "#cbd5e1" if dato["activo"] else "#94a3b8"
        )
        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line=dict(color=color, width=7 if destacado else 2,
                      dash="solid" if dato["activo"] else "dash"),
            hovertemplate=f"{a}–{b} · Peso: {dato['peso']}<extra></extra>",
            showlegend=False,
        ))
        etiqueta = str(dato["peso"]) if dato["activo"] else "✕"
        if dato["fijo"]:
            etiqueta += " 🔒"
        fig.add_annotation(
            x=(x1+x2)/2, y=(y1+y2)/2, text=f"<b>{etiqueta}</b>",
            showarrow=False, bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#cbd5e1", borderwidth=1, font=dict(size=12),
        )

    for n, (x, y) in POS.items():
        color = "#e8a13b" if n == origen else (
            "#9349c9" if n == destino else "#216bad"
        )
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[n],
            textposition="middle center",
            textfont=dict(color="white", size=14),
            marker=dict(size=36, color=color, line=dict(color="white", width=2)),
            hovertemplate=f"Router {n}<extra></extra>", showlegend=False,
        ))
    fig.update_layout(
        height=610, margin=dict(l=8, r=8, t=8, b=8),
        xaxis=dict(visible=False, range=[0, 11]),
        yaxis=dict(visible=False, range=[0, 10], scaleanchor="x", scaleratio=1),
        plot_bgcolor="white", paper_bgcolor="white",
    )
    return fig


iniciar()
st.title("🌐 Simulador de rutas óptimas y Sink Tree")
st.caption("15 routers · Pesos por enlace · Tres rutas mínimas · Actualización periódica")

with st.sidebar:
    st.header("Configuración")
    origen = st.selectbox("Origen", sorted(POS), index=sorted(POS).index("H"))
    destino = st.selectbox("Destino", sorted(POS), index=sorted(POS).index("B"))
    vista = st.selectbox("Visualización",
                        ["Tres rutas", "Primaria", "Secundaria",
                         "Terciaria", "Árbol sumidero"])
    st.divider()
    st.subheader("Simulación")
    st.selectbox("Escenario inicial", list(RANGOS), index=1, key="escenario_ui")
    variacion = st.slider("Variación máxima por segundo", 1, 100, 15)
    st.toggle("Activar simulación automática", key="activo_sim", on_change=pausar)
    st.button("Generar nuevos pesos", on_click=reiniciar, use_container_width=True)
    st.caption("Son pesos artificiales: no proceden de routers físicos.")
    st.divider()
    st.subheader("Editar enlace")
    st.selectbox("Conexión", [f"{a} - {b}" for a, b in sorted(st.session_state.enlaces)],
                 key="enlace_ui", on_change=sincronizar_editor)
    dato = st.session_state.enlaces[enlace_actual()]
    st.number_input("Peso", min_value=1, max_value=100000, step=1,
                    key="peso_ui", on_change=guardar_peso,
                    disabled=st.session_state.activo_sim)
    st.checkbox("Fijar este peso", key="fijo_ui", on_change=guardar_bloqueo)
    st.button("Reparar enlace" if not dato["activo"] else "Dañar enlace",
              on_click=cambiar_enlace, use_container_width=True)
    st.button("Restablecer red", on_click=reiniciar, use_container_width=True)
    st.caption("Pausa para editar. Un peso fijo no varía en la simulación.")


@st.fragment(run_every="1s")
def panel_en_vivo():
    if st.session_state.activo_sim:
        variar_pesos(variacion)
        st.session_state.ciclos += 1

    g = grafo()
    rutas, pasos = tres_rutas(g, origen, destino)
    distancias, siguientes = dijkstra(g, destino)
    caidos = sum(not x["activo"] for x in st.session_state.enlaces.values())

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Routers", len(POS))
    k2.metric("Enlaces activos", len(st.session_state.enlaces) - caidos)
    k3.metric("Enlaces caídos", caidos)
    k4.metric("Ciclos", st.session_state.ciclos)

    st.success("🟢 Simulación activa: pesos actualizados cada segundo") if (
        st.session_state.activo_sim
    ) else st.info("⏸ Pausado: edita pesos o enlaces en la barra lateral")

    izquierda, derecha = st.columns([3, 1])
    with izquierda:
        st.plotly_chart(dibujar(rutas, siguientes, vista, origen, destino),
                        use_container_width=True)
        st.caption("Rojo: primaria · Azul: secundaria · Verde: terciaria · Morado: árbol")
    with derecha:
        st.subheader("Tres rutas de menor costo")
        for i, nombre in enumerate(["Primaria", "Secundaria", "Terciaria"]):
            if i < len(rutas):
                costo, camino = rutas[i]
                st.markdown(f"**{i+1}. {nombre} · Costo {costo}**")
                st.caption(" → ".join(camino) + f" · {len(camino)-1} saltos")
            else:
                st.write(f"{nombre}: no disponible")
        st.subheader("Pesos actuales")
        st.dataframe([
            {"Enlace": f"{a}–{b}", "Peso": dato["peso"],
             "Activo": dato["activo"], "Fijo": dato["fijo"]}
            for (a, b), dato in sorted(st.session_state.enlaces.items())
        ], hide_index=True, height=295)

    t1, t2 = st.tabs(["🌳 Tabla del Sink Tree", "🧠 Decisiones del algoritmo"])
    with t1:
        st.dataframe([
            {"Router": n,
             "Distancia a " + destino: "∞" if math.isinf(distancias[n]) else int(distancias[n]),
             "Siguiente salto": siguientes.get(n, "—")}
            for n in sorted(POS)
        ], hide_index=True, use_container_width=True)
        st.caption("Dijkstra calcula la distancia mínima desde cada router al destino.")
    with t2:
        st.dataframe(pasos, hide_index=True, height=340)
        st.caption("Búsqueda de costo uniforme: elige primero el camino pendiente más barato.")

    if st.session_state.activo_sim:
        st.session_state.historial.append({
            "Ciclo": st.session_state.ciclos,
            "Costo mínimo": rutas[0][0] if rutas else None
        })
        st.session_state.historial = st.session_state.historial[-120:]

    if len(st.session_state.historial) > 1:
        st.subheader("Evolución del costo de la mejor ruta")
        st.line_chart(st.session_state.historial, x="Ciclo", y="Costo mínimo")


panel_en_vivo()
st.caption("Simulador académico. Los costos son simulados; no es telemetría Cisco real.")
