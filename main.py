"""Laboratorio interactivo de enrutamiento adaptativo y árboles sumidero."""
import itertools
import math
import random
import string

import networkx as nx
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Laboratorio Sink Tree", page_icon="🌐", layout="wide")

POS_INICIAL = {
    "A": (1, 8), "B": (5, 9), "C": (9, 8), "D": (3, 6),
    "E": (6, 6), "F": (1, 5), "G": (2, 4), "H": (4, 3),
    "I": (5, 5), "J": (8, 5), "K": (1, 2), "L": (3, 2),
    "M": (5, 1), "N": (9, 3), "O": (10, 1),
}
ENLACES_INICIALES = [
    ("A", "B"), ("B", "C"), ("A", "D"), ("A", "F"),
    ("D", "G"), ("D", "H"), ("D", "I"), ("F", "K"),
    ("K", "L"), ("G", "L"), ("L", "M"), ("H", "E"),
    ("E", "J"), ("H", "O"), ("O", "N"), ("N", "J"),
    ("N", "M"), ("I", "J"), ("I", "C"), ("J", "C"),
]
ESCENARIOS = {
    "Carga baja": {"peso": (5, 40), "retardo": (2, 18),
                   "ancho": (150, 1000), "perdida": (0.0, 0.3), "jitter": (0.2, 3)},
    "Carga variable": {"peso": (20, 150), "retardo": (10, 85),
                       "ancho": (30, 450), "perdida": (0.0, 2.5), "jitter": (1, 20)},
    "Congestión": {"peso": (100, 300), "retardo": (65, 250),
                   "ancho": (2, 80), "perdida": (1, 12), "jitter": (10, 65)},
}
MODOS = ["Adaptativo", "Peso manual", "Saltos", "Retardo", "Ancho de banda",
         "Pérdida de paquetes", "Jitter"]
COLORES = ["#e5484d", "#287bd3", "#1f9d6a"]
MAX_NODOS = 100


def clave(a, b):
    return tuple(sorted((a, b)))


def metricas_aleatorias(escenario):
    r = ESCENARIOS[escenario]
    return {
        "peso": random.randint(*r["peso"]),
        "retardo": round(random.uniform(*r["retardo"]), 2),
        "ancho": round(random.uniform(*r["ancho"]), 2),
        "perdida": round(random.uniform(*r["perdida"]), 2),
        "jitter": round(random.uniform(*r["jitter"]), 2),
        "activo": True,
        "fijo": False,
    }


def iniciar():
    s = st.session_state
    if "posiciones" not in s:
        s.posiciones = dict(POS_INICIAL)
    if "enlaces" not in s:
        s.enlaces = {clave(a, b): metricas_aleatorias("Carga variable")
                     for a, b in ENLACES_INICIALES}
    if "origen" not in s:
        s.origen = "H"
    if "destino" not in s:
        s.destino = "B"
    if "en_vivo" not in s:
        s.en_vivo = False
    if "ciclos" not in s:
        s.ciclos = 0
    if "historial" not in s:
        s.historial = []


def nuevo_nombre():
    usados = st.session_state.posiciones
    for longitud in range(1, 4):
        for letras in itertools.product(string.ascii_uppercase, repeat=longitud):
            nombre = "".join(letras)
            if nombre not in usados:
                return nombre
    raise ValueError("No hay nombres disponibles")


def nueva_posicion():
    posiciones = st.session_state.posiciones
    n = len(posiciones) - len(POS_INICIAL)
    angulo = n * 2.399963229728653
    radio = 6.5 + 1.2 * math.sqrt(max(0, n))
    return (round(5 + radio * math.cos(angulo), 2),
            round(5 + radio * math.sin(angulo), 2))


def eliminar_nodo_confirmado():
    s = st.session_state
    if not s.get("confirmar_eliminar_ui", False):
        return
    quitar = s.get("quitar_ui")
    if quitar not in s.posiciones or len(s.posiciones) <= 2:
        return
    del s.posiciones[quitar]
    s.enlaces = {k: d for k, d in s.enlaces.items() if quitar not in k}
    restantes = sorted(s.posiciones)
    if s.origen == quitar:
        s.origen = restantes[0]
    if s.destino == quitar:
        s.destino = restantes[-1]


def reiniciar():
    s = st.session_state
    s.posiciones = dict(POS_INICIAL)
    s.enlaces = {clave(a, b): metricas_aleatorias(s.escenario)
                 for a, b in ENLACES_INICIALES}
    s.origen, s.destino = "H", "B"
    s.ciclos = 0
    s.historial = []


def peso_efectivo(d, modo, coef):
    """Costo positivo aditivo para Dijkstra y las tres rutas."""
    if modo == "Peso manual":
        return float(d["peso"])
    if modo == "Saltos":
        return 1.0
    if modo == "Retardo":
        return float(d["retardo"])
    if modo == "Ancho de banda":
        return 100.0 / max(0.1, float(d["ancho"]))
    if modo == "Pérdida de paquetes":
        return 1.0 + float(d["perdida"])
    if modo == "Jitter":
        return 1.0 + float(d["jitter"])
    return (
        coef["Saltos"] * 1.0
        + coef["Peso"] * d["peso"] / 100.0
        + coef["Retardo"] * d["retardo"] / 50.0
        + coef["Ancho"] * 100.0 / max(0.1, d["ancho"])
        + coef["Pérdida"] * d["perdida"] / 2.0
        + coef["Jitter"] * d["jitter"] / 10.0
    )


def construir_grafo(modo, coef):
    g = nx.Graph()
    g.add_nodes_from(st.session_state.posiciones)
    for (a, b), d in st.session_state.enlaces.items():
        if d["activo"] and a in g and b in g:
            g.add_edge(a, b, weight=peso_efectivo(d, modo, coef))
    return g


def calcular_rutas(g, origen, destino):
    if origen == destino:
        return [(0.0, [origen])]
    if not nx.has_path(g, origen, destino):
        return []
    # Yen (NetworkX): genera caminos simples en orden de costo; solo pedimos tres.
    generador = nx.shortest_simple_paths(g, origen, destino, weight="weight")
    resultado = []
    for camino in itertools.islice(generador, 3):
        costo = sum(g[a][b]["weight"] for a, b in zip(camino, camino[1:]))
        resultado.append((costo, camino))
    return resultado


def arbol_sumidero(g, destino):
    # Dijkstra desde el destino en grafo no dirigido.
    dist, caminos = nx.single_source_dijkstra(g, destino, weight="weight")
    siguiente = {n: camino[-2] for n, camino in caminos.items() if len(camino) > 1}
    return dist, siguiente


def actualizar_escenario(escenario, intensidad):
    """Perturba retardo, capacidad, pérdida, jitter y peso de cada enlace."""
    for d in st.session_state.enlaces.values():
        if not d["activo"] or d["fijo"]:
            continue
        base = metricas_aleatorias(escenario)
        factor = intensidad / 100.0
        for campo in ("peso", "retardo", "ancho", "perdida", "jitter"):
            anterior = float(d[campo])
            objetivo = float(base[campo])
            nuevo = anterior * (1 - factor) + objetivo * factor
            if campo == "peso":
                d[campo] = max(1, round(nuevo))
            elif campo == "ancho":
                d[campo] = round(max(0.1, nuevo), 2)
            elif campo == "perdida":
                d[campo] = round(min(100, max(0, nuevo)), 2)
            else:
                d[campo] = round(max(0.01, nuevo), 2)


def figura(g, rutas, siguiente, vista, origen, destino):
    posiciones = st.session_state.posiciones
    fig = go.Figure()
    marcados = {}
    if vista == "Árbol sumidero":
        marcados = {clave(a, b): "#9650d6" for a, b in siguiente.items()}
    else:
        opciones = {"Tres rutas": [0, 1, 2], "Primaria": [0],
                    "Secundaria": [1], "Terciaria": [2]}
        for i in reversed(opciones[vista]):
            if i < len(rutas):
                for a, b in zip(rutas[i][1], rutas[i][1][1:]):
                    marcados[clave(a, b)] = COLORES[i]

    for (a, b), d in sorted(st.session_state.enlaces.items()):
        if a not in posiciones or b not in posiciones:
            continue
        x1, y1 = posiciones[a]
        x2, y2 = posiciones[b]
        activo = d["activo"]
        resaltado = activo and clave(a, b) in marcados
        color = marcados[clave(a, b)] if resaltado else (
            "#c5cedb" if activo else "#a6acb7")
        costo = peso_efectivo(d, st.session_state.modo, st.session_state.coef)
        detalle = (f"{a}–{b}<br>Peso: {d['peso']}<br>"
                   f"Retardo: {d['retardo']} ms<br>Ancho: {d['ancho']} Mbps<br>"
                   f"Pérdida: {d['perdida']}%<br>Jitter: {d['jitter']} ms<br>"
                   f"Costo según criterio: {costo:.2f}")
        fig.add_trace(go.Scatter(
            x=[x1, x2], y=[y1, y2], mode="lines",
            line=dict(color=color, width=7 if resaltado else 2,
                      dash="solid" if activo else "dash"),
            hovertemplate=detalle + "<extra></extra>", showlegend=False))
        etiqueta = (f"P:{d['peso']}" if st.session_state.modo == "Peso manual"
                    else f"P:{d['peso']} · C:{costo:.1f}") if activo else "✕"
        fig.add_annotation(
            x=(x1+x2)/2, y=(y1+y2)/2, text=f"<b>{etiqueta}</b>",
            showarrow=False, bgcolor="rgba(255,255,255,0.92)",
            font=dict(color="#172a40", size=11), bordercolor="#cbd5e1",
            borderwidth=1, borderpad=2)

    for n, (x, y) in posiciones.items():
        color = "#e69d38" if n == origen else (
            "#9350cc" if n == destino else "#206bab")
        fig.add_trace(go.Scatter(
            x=[x], y=[y], mode="markers+text", text=[n],
            textposition="middle center", textfont=dict(color="white", size=11),
            marker=dict(size=32, color=color, line=dict(color="white", width=2)),
            hovertemplate=f"Router {n}<extra></extra>", showlegend=False))
    xs = [p[0] for p in posiciones.values()]
    ys = [p[1] for p in posiciones.values()]
    fig.update_layout(
        height=650, margin=dict(l=5, r=5, t=5, b=5),
        xaxis=dict(visible=False, range=[min(xs)-1.5, max(xs)+1.5]),
        yaxis=dict(visible=False, range=[min(ys)-1.5, max(ys)+1.5],
                   scaleanchor="x", scaleratio=1),
        plot_bgcolor="white", paper_bgcolor="white", uirevision="red")
    return fig


iniciar()
s = st.session_state
st.title("🌐 Laboratorio de enrutamiento adaptativo y Sink Tree")
st.caption("Grafo editable · Tres rutas de costo mínimo · Dijkstra · Simulación de tráfico")

with st.sidebar:
    st.header("1. Origen y destino")
    nodos = sorted(s.posiciones)
    if s.origen not in nodos:
        s.origen = nodos[0]
    if s.destino not in nodos:
        s.destino = nodos[-1]
    st.selectbox("Origen", nodos, key="origen")
    st.selectbox("Destino (raíz del Sink Tree)", nodos, key="destino")
    vista = st.selectbox("Visualización", ["Tres rutas", "Primaria",
                                          "Secundaria", "Terciaria", "Árbol sumidero"])
    st.divider()

    st.header("2. Criterio de enrutamiento")
    modo = st.selectbox("Optimizar según", MODOS, key="modo")
    coef = {"Saltos": 1.0, "Peso": 1.0, "Retardo": 1.0,
            "Ancho": 1.0, "Pérdida": 1.0, "Jitter": 1.0}
    if modo == "Adaptativo":
        with st.expander("⚖️ Importancia de cada variable", expanded=False):
            for k in coef:
                coef[k] = st.slider(k, 0.0, 5.0, 1.0, 0.25, key=f"coef_{k}")
    s.coef = coef
    st.caption("P = peso manual; C = costo efectivo según el criterio elegido.")
    st.divider()

    st.header("3. Simulación en tiempo real")
    st.selectbox("Regla de tráfico", list(ESCENARIOS), index=1, key="escenario")
    intensidad = st.slider("Intensidad del cambio (%)", 5, 100, 35)
    st.toggle("▶ Activar simulación", key="en_vivo")
    if st.button("🎲 Generar valores nuevos", use_container_width=True):
        for d in s.enlaces.values():
            if not d["fijo"]:
                activo = d["activo"]
                d.update(metricas_aleatorias(s.escenario))
                d["activo"] = activo
        st.rerun()
    st.caption("Cada segundo varían las métricas de enlaces no bloqueados. "
               "Los datos son simulados, no telemetría real.")
    st.divider()

    st.header("4. Construir y modificar el grafo")
    st.caption(f"{len(s.posiciones)} routers · {len(s.enlaces)} enlaces · máximo {MAX_NODOS} routers")

    with st.expander("➕ Añadir router", expanded=True):
        with st.form("form_nodo", clear_on_submit=False):
            nombre_sugerido = nuevo_nombre()
            nombre = st.text_input("Nombre del nuevo router", value=nombre_sugerido,
                                   max_chars=16, key=f"nombre_nuevo_{len(nodos)}")
            conectar = st.selectbox("Conectarlo inicialmente con", nodos)
            peso_nuevo = st.number_input("Peso del enlace inicial", 1, 100000, 40)
            crear_nodo = st.form_submit_button("Añadir router", use_container_width=True)
        if crear_nodo:
            nombre = nombre.strip().upper()
            if not nombre or any(c.isspace() for c in nombre):
                st.error("El nombre no puede estar vacío ni contener espacios.")
            elif nombre in s.posiciones:
                st.error("Ese router ya existe.")
            elif len(s.posiciones) >= MAX_NODOS:
                st.error("Se alcanzó el máximo de routers.")
            else:
                s.posiciones[nombre] = nueva_posicion()
                d = metricas_aleatorias(s.escenario)
                d["peso"] = int(peso_nuevo)
                s.enlaces[clave(nombre, conectar)] = d
                st.rerun()

    with st.expander("🔗 Añadir o cambiar conexión"):
        with st.form("form_conexion"):
            a = st.selectbox("Primer router", nodos)
            b = st.selectbox("Segundo router", nodos, index=min(1, len(nodos)-1))
            peso = st.number_input("Peso inicial", 1, 100000, 50)
            crear_conexion = st.form_submit_button("Guardar conexión", use_container_width=True)
        if crear_conexion:
            if a == b:
                st.error("Selecciona dos routers diferentes.")
            else:
                d = s.enlaces.get(clave(a, b), metricas_aleatorias(s.escenario))
                d["peso"] = int(peso)
                d["activo"] = True
                s.enlaces[clave(a, b)] = d
                st.rerun()

    with st.expander("🧭 Mover un router"):
        nodo_mover = st.selectbox("Router a mover", nodos)
        with st.form(f"form_posicion_{nodo_mover}"):
            px, py = s.posiciones[nodo_mover]
            x = st.number_input("Coordenada X", value=float(px), step=0.5)
            y = st.number_input("Coordenada Y", value=float(py), step=0.5)
            mover = st.form_submit_button("Actualizar posición", use_container_width=True)
        if mover:
            s.posiciones[nodo_mover] = (float(x), float(y))
            st.rerun()

    with st.expander("🗑 Eliminar router"):
        with st.form("form_eliminar_nodo"):
            st.selectbox("Router", nodos, key="quitar_ui")
            st.checkbox("Confirmo que deseo eliminarlo", key="confirmar_eliminar_ui")
            st.form_submit_button("Eliminar router", use_container_width=True,
                                  on_click=eliminar_nodo_confirmado)

    st.divider()
    st.header("5. Editar métricas de cada enlace")
    st.caption("Pausa la simulación para editar. Puedes fijar enlaces para que no cambien.")
    opciones = sorted(s.enlaces)
    if opciones:
        elegido = st.selectbox("Enlace", opciones,
                              format_func=lambda e: f"{e[0]} – {e[1]}")
        d = s.enlaces[elegido]
        with st.form(f"form_metricas_{elegido[0]}_{elegido[1]}_{s.ciclos}"):
            peso = st.number_input("Peso manual", 1, 100000, int(d["peso"]))
            retardo = st.number_input("Retardo (ms)", 0.01, 10000.0,
                                      float(d["retardo"]), step=1.0)
            ancho = st.number_input("Ancho de banda (Mbps)", 0.1, 100000.0,
                                    float(d["ancho"]), step=10.0)
            perdida = st.number_input("Pérdida (%)", 0.0, 100.0,
                                      float(d["perdida"]), step=0.1)
            jitter = st.number_input("Jitter (ms)", 0.01, 10000.0,
                                     float(d["jitter"]), step=1.0)
            activo = st.checkbox("Enlace activo", value=bool(d["activo"]))
            fijo = st.checkbox("Bloquear métricas", value=bool(d["fijo"]))
            guardar = st.form_submit_button("💾 Aplicar cambios",
                                             disabled=s.en_vivo, use_container_width=True)
        if guardar:
            d.update({"peso": int(peso), "retardo": float(retardo),
                      "ancho": float(ancho), "perdida": float(perdida),
                      "jitter": float(jitter), "activo": activo, "fijo": fijo})
            st.rerun()
        if st.button("Eliminar este enlace", use_container_width=True):
            del s.enlaces[elegido]
            st.rerun()
    else:
        st.warning("No hay enlaces. Crea uno en la sección 4.")
    st.button("↩ Restablecer topología inicial", on_click=reiniciar,
              use_container_width=True)


@st.fragment(run_every="1s")
def panel():
    if s.en_vivo:
        actualizar_escenario(s.escenario, intensidad)
        s.ciclos += 1
    g = construir_grafo(s.modo, s.coef)
    rutas = calcular_rutas(g, s.origen, s.destino)
    dist, siguiente = arbol_sumidero(g, s.destino)
    caidos = sum(not d["activo"] for d in s.enlaces.values())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Routers", len(s.posiciones))
    m2.metric("Enlaces activos", len(s.enlaces)-caidos)
    m3.metric("Enlaces caídos", caidos)
    m4.metric("Ciclos", s.ciclos)
    if s.en_vivo:
        st.success("🟢 EN VIVO: métricas y rutas se recalculan cada segundo")
    else:
        st.info("⏸ PAUSADO: puedes editar la red y sus métricas")

    izquierda, derecha = st.columns([3, 1])
    with izquierda:
        st.plotly_chart(figura(g, rutas, siguiente, vista, s.origen, s.destino),
                        use_container_width=True,
                        config={"scrollZoom": True, "displaylogo": False})
        st.caption("Rojo: primaria · Azul: secundaria · Verde: terciaria · Morado: Sink Tree")
    with derecha:
        st.subheader("3 rutas óptimas")
        if not rutas:
            st.warning("No existe una ruta activa entre origen y destino.")
        for i, (costo, camino) in enumerate(rutas):
            st.markdown(f"**{i+1}. {['Primaria','Secundaria','Terciaria'][i]} · {costo:.2f}**")
            st.caption(" → ".join(camino) + f" · {len(camino)-1} saltos")
        st.caption("El costo corresponde a la métrica seleccionada, no necesariamente a milisegundos.")
        st.subheader("Estado de enlaces")
        st.dataframe([
            {"Enlace": f"{a}–{b}", "Peso": d["peso"],
             "Retardo ms": d["retardo"], "Mbps": d["ancho"],
             "Pérdida %": d["perdida"], "Jitter ms": d["jitter"],
             "Activo": d["activo"], "Fijo": d["fijo"]}
            for (a, b), d in sorted(s.enlaces.items())
        ], hide_index=True, height=300)

    t1, t2, t3 = st.tabs(["🌳 Árbol sumidero", "📐 Comparación de rutas",
                           "🧠 Teoría y cálculo"])
    with t1:
        st.write(f"**Raíz del árbol: {s.destino}.** Cada router alcanzable tiene "
                 "un siguiente salto hacia ese destino, calculado con Dijkstra.")
        st.dataframe([
            {"Router": n, "Costo hasta destino": round(dist[n], 2) if n in dist else "∞",
             "Siguiente salto": siguiente.get(n, "—")}
            for n in sorted(s.posiciones)
        ], hide_index=True, use_container_width=True)
    with t2:
        tabla = []
        for i, (costo, camino) in enumerate(rutas):
            aristas = [s.enlaces[clave(a, b)] for a, b in zip(camino, camino[1:])]
            tabla.append({
                "Ruta": i+1, "Camino": " → ".join(camino),
                "Costo": round(costo, 2), "Saltos": len(camino)-1,
                "Retardo total (ms)": round(sum(d["retardo"] for d in aristas), 2),
                "Ancho mínimo (Mbps)": round(min((d["ancho"] for d in aristas), default=0), 2),
                "Pérdida extremo a extremo (%)": round(
                    100*(1-math.prod(1-d["perdida"]/100 for d in aristas)), 2)
            })
        st.dataframe(tabla, hide_index=True, use_container_width=True)
    with t3:
        st.markdown(
            "**Modelo:** grafo no dirigido con enlaces de costo positivo. "
            "Las tres rutas simples más económicas se generan con el método de Yen "
            "de NetworkX. Dijkstra construye el árbol de caminos mínimos hacia "
            "el destino seleccionado.\n\n"
            "**Costo adaptativo por enlace:**\n\n"
            "`w_s·1 + w_p·(peso/100) + w_r·(retardo/50) "
            "+ w_b·(100/ancho_Mbps) + w_l·(pérdida_%/2) "
            "+ w_j·(jitter/10)`\n\n"
            "Los coeficientes se ajustan en la barra lateral. "
            "En el modo ancho de banda se minimiza la suma de penalizaciones "
            "inversas; **no** equivale a maximizar estrictamente el ancho de "
            "banda mínimo de la ruta. Los valores aleatorios representan "
            "escenarios educativos, no mediciones reales de una red."
        )

    if s.en_vivo:
        s.historial.append({"Ciclo": s.ciclos,
                            "Costo mínimo": rutas[0][0] if rutas else None})
        s.historial = s.historial[-120:]
    if len(s.historial) > 1:
        st.subheader("📈 Evolución del costo óptimo")
        st.line_chart(s.historial, x="Ciclo", y="Costo mínimo")


panel()
st.caption("Proyecto académico de teoría de grafos y enrutamiento adaptativo · Python + Streamlit")
