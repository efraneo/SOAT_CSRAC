import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import db, mostrar_alerta, mostrar_metrica_card

def mostrar():
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🏠 Inicio", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    with c2:
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state["admin_autenticado"] = False
            st.rerun()

    st.markdown("""<div class="main-title"><h1>📊 Panel Admin</h1></div>""", unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    with st.spinner("Cargando..."):
        ind = db.obtener_indicadores()

    st.markdown("### 📈 Indicadores")
    cols = st.columns(6)
    with cols[0]: mostrar_metrica_card("👥", ind["total"], "Total", "#1a237e")
    with cols[1]: mostrar_metrica_card("✅", ind["vigentes"], "Vigentes", "#2e7d32")
    with cols[2]: mostrar_metrica_card("⚠️", ind["por_vencer"], "P. Vencer", "#f57f17")
    with cols[3]: mostrar_metrica_card("🚨", ind["vencidos"], "Vencidos", "#c62828")
    with cols[4]: mostrar_metrica_card("📷", ind["no_legibles"], "No Leg.", "#6a1b9a")
    with cols[5]: mostrar_metrica_card("⏳", ind["pendientes"], "Pend.", "#607d8b")

    if ind["total"] > 0:
        _mostrar_graficos(ind)

    if ind["alertas"]:
        with st.expander(f"🔔 Alertas ({len(ind['alertas'])})", expanded=True):
            for a in ind["alertas"]:
                mostrar_alerta(a["tipo"], a["mensaje"])

    st.markdown("### 🛂 Garita (Hoy)")
    hist = db.obtener_historial_hoy()
    if hist:
        df_h = pd.DataFrame(hist)[["placa", "nombre_trabajador", "estado_soat", "fecha_ingreso"]].rename(columns={"placa": "Placa", "nombre_trabajador": "Nombre", "estado_soat": "Estado", "fecha_ingreso": "Hora"})
        df_h["Hora"] = df_h["Hora"].apply(lambda x: str(x).split("T")[1][:8] if "T" in str(x) else str(x)[:8])
        st.dataframe(df_h.style.map(lambda v: "background-color: #c8e6c9; color: #1b5e20; font-weight: 600" if v == "Vigente" else "background-color: #ffcdd2; color: #b71c1c; font-weight: 700", subset=["Estado"]), use_container_width=True, height=200, hide_index=True)
    else:
        st.info("📭 Sin ingresos hoy.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### ✏️ Gestión por ID")
    id_buscar = st.text_input("🔑 Digite el ID:", placeholder="Pégalo de la tabla de abajo...", key="id_gestion")

    if id_buscar:
        current = db.obtener_trabajador_por_id(id_buscar)
        if not current:
            mostrar_alerta("danger", "ID no encontrado.")
        else:
            mostrar_alerta("success", f"Encontrado: {current.get('nombres')} - {current.get('placa')} ({current.get('soat_estado')})")
            tab1, tab2, tab3, tab4 = st.tabs(["📝 Info", "🔄 Estado", "📄 Soporte", "🗑️ Eliminar"])

            with tab1:
                with st.form("f_info"):
                    c1, c2 = st.columns(2)
                    with c1:
                        new_nom = st.text_input("👤 Nombre", value=current.get("nombres", ""))
                        new_car = st.text_input("💼 Cargo", value=current.get("cargo", ""))
                    with c2:
                        new_placa = st.text_input("🚘 Placa", value=current.get("placa", ""))
                        new_tv = st.selectbox("🏷️ Tipo", ["Automovil", "Motocicleta"], index=0 if current.get("tipo_vehiculo") == "Automovil" else 1)
                    if st.form_submit_button("💾 Guardar", use_container_width=True):
                        datos = {"nombres": new_nom, "cargo": new_car, "placa": new_placa.upper(), "tipo_vehiculo": new_tv}
                        res = db.actualizar_trabajador(id_buscar, datos)
                        if res["exito"]:
                            st.success("✅ Actualizado.")
                            st.rerun()
                        else:
                            st.error(f"Error: {res['mensaje']}")

            with tab2:
                st.markdown(f"Estado actual: **{current.get('soat_estado', 'Pendiente')}**")
                with st.form("f_estado"):
                    nuevo_estado = st.selectbox("Nuevo Estado:", ["Vigente", "Por vencer", "Vencido", "No legible", "Pendiente"], key="nuevo_estado")
                    if st.form_submit_button("🔄 Actualizar Estado", use_container_width=True, type="primary"):
                        res = db.actualizar_trabajador(id_buscar, {"soat_estado": nuevo_estado})
                        if res["exito"]:
                            st.success(f"✅ Estado actualizado a: {nuevo_estado}")
                            st.rerun()
                        else:
                            st.error(f"Error: {res['mensaje']}")

            with tab3:
                st.markdown("#### 📄 Soporte Actual")
                url_actual = current.get("soat_url", "")
                if url_actual:
                    if ".pdf" in url_actual:
                        st.markdown(f"📎 [Ver PDF]({url_actual})")
                    else:
                        st.image(url_actual, caption="Soporte actual", width=400)
                st.markdown("---")
                nuevo_img = st.file_uploader("📎 Nuevo Soporte (Img/PDF)", type=["jpg", "jpeg", "png", "pdf"], key="img_edit")
                if nuevo_img:
                    if nuevo_img.type != "application/pdf":
                        st.image(nuevo_img, caption="Nuevo archivo", width=400)
                    else:
                        mostrar_alerta("success", f"PDF '{nuevo_img.name}' seleccionado.")
                    if st.button("🔄 Subir y Analizar", use_container_width=True, type="primary"):
                        with st.spinner("🔄 Procesando con IA..."):
                            bytes_img = nuevo_img.read()
                            res = db.actualizar_trabajador(id_buscar, {}, bytes_img, nuevo_img.name)
                            if res["exito"]:
                                st.success("✅ Soporte actualizado.")
                                st.rerun()
                            else:
                                st.error(f"Error: {res['mensaje']}")

            with tab4:
                st.warning("Acción irreversible.")
                if st.button("⚠️ Eliminar", type="primary"):
                    if db.eliminar_trabajador(id_buscar):
                        st.success("Eliminado.")
                        st.rerun()
                    else:
                        st.error("Error al eliminar.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### 📋 Base de Datos")
    _mostrar_tabla()

def _mostrar_graficos(ind):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🚘 Tipo Vehículo")
        if ind["por_tipo_vehiculo"]:
            df = pd.DataFrame([{"Tipo": k, "Cantidad": v} for k, v in ind["por_tipo_vehiculo"].items()])
            fig = px.pie(df, values="Cantidad", names="Tipo", hole=0.5, color_discrete_sequence=["#1a237e", "#f57f17"])
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=250)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("#### 💼 Cargos")
        if ind["por_cargo"]:
            df = pd.DataFrame([{"Cargo": k, "Cantidad": v} for k, v in ind["por_cargo"].items()]).sort_values("Cantidad")
            fig = px.bar(df, x="Cantidad", y="Cargo", orientation="h", color="Cantidad", color_continuous_scale="Blues")
            fig.update_layout(margin=dict(t=10, b=10, l=100, r=10), height=250, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 📅 Registros/Mes")
    if ind["por_mes"]:
        df = pd.DataFrame([{"Mes": k, "Registros": v} for k, v in ind["por_mes"].items()]).sort_values("Mes")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Mes"], y=df["Registros"], mode="lines+markers+text", text=df["Registros"], textposition="top center", line=dict(color="#1a237e", width=3), fill="tozeroy", fillcolor="rgba(26,35,126,0.08)"))
        fig.update_layout(margin=dict(t=20, b=40, l=40, r=20), height=250)
        st.plotly_chart(fig, use_container_width=True)

def _color_estado(val):
    """Función auxiliar para pintar las celdas del estado del SOAT en la tabla."""
    if val == "Vigente":
        return "background-color: #c8e6c9; color: #1b5e20; font-weight:600"
    elif val == "Por vencer":
        return "background-color: #fff9c4; color: #f57f17; font-weight: 600"
    elif val == "Vencido":
        return "background-color: #ffcdd2; color: #c62828; font-weight: 600"
    elif val == "No legible":
        return "background-color: #e1bee7; color: #6a1b9a; font-weight: 600"
    return "background-color: #e0e0e0; color: #616161; font-weight: 600"

def _mostrar_tabla():
    todos = db.obtener_todos_trabajadores()
    if not todos:
        st.info("📭 Base de datos vacía.")
        return

    df = pd.DataFrame(todos)[
        ["identificacion", "nombres", "cargo", "tipo_vehiculo", "placa", "soat_estado", "soat_vigencia", "fecha_registro"]
    ].rename(columns={
        "identificacion": "ID", "nombres": "Nombre", "cargo": "Cargo",
        "tipo_vehiculo": "Tipo", "placa": "Placa",
        "soat_estado": "Estado SOAT", "soat_vigencia": "Vencimiento",
        "fecha_registro": "Fecha Registro"
    })
    for c in ["Vencimiento", "Fecha Registro"]:
        df[c] = df[c].apply(lambda x: str(x)[:10] if pd.notna(x) else "N/A")
    
    st.dataframe(
        df.style.map(_color_estado, subset=["Estado SOAT"]),
        use_container_width=True, 
        height=400, 
        hide_index=True
    )
