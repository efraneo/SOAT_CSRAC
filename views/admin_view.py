import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import db, mostrar_alerta, mostrar_metrica_card

def mostrar():
    if st.button("🚪 Cerrar Sesión"): st.session_state["admin_autenticado"] = False; st.rerun()
    st.markdown("""<div class="main-title"><h1>📊 Panel de Administración</h1><p>Sistema de Registro y Control de SOAT</p></div>""", unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    with st.spinner("Cargando..."): ind = db.obtener_indicadores()

    st.markdown("### 📈 Indicadores Generales")
    cols = st.columns(6)
    with cols[0]: mostrar_metrica_card("👥", ind["total"], "Total", "#1a237e")
    with cols[1]: mostrar_metrica_card("✅", ind["vigentes"], "Vigentes", "#2e7d32")
    with cols[2]: mostrar_metrica_card("⚠️", ind["por_vencer"], "Por Vencer", "#f57f17")
    with cols[3]: mostrar_metrica_card("🚨", ind["vencidos"], "Vencidos", "#c62828")
    with cols[4]: mostrar_metrica_card("📷", ind["no_legibles"], "No Legibles", "#6a1b9a")
    with cols[5]: mostrar_metrica_card("⏳", ind["pendientes"], "Pendientes", "#607d8b")

    st.markdown("### 📊 Distribución")
    c1, c2 = st.columns(2)
    with c1: st.markdown(f"**✅ Vigentes:** {ind['vigentes']} ({ind['pct_vigentes']}%)"); st.progress(ind["pct_vigentes"]/100)
    with c2: st.markdown(f"**⚠️ Por Vencer:** {ind['por_vencer']} ({ind['pct_por_vencer']}%)"); st.progress(ind["pct_por_vencer"]/100)
    c3, c4 = st.columns(2)
    with c3: st.markdown(f"**🚨 Vencidos:** {ind['vencidos']} ({ind['pct_vencidos']}%)"); st.progress(ind["pct_vencidos"]/100)
    with c4: st.markdown(f"**📷 No Legibles:** {ind['no_legibles']} ({ind['pct_no_legibles']}%)"); st.progress(ind["pct_no_legibles"]/100)

    if ind["total"] > 0: _mostrar_graficos(ind)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    if ind["alertas"]:
        st.markdown("### 🔔 Alertas Activas")
        with st.expander(f"Ver {len(ind['alertas'])} alerta(s)", expanded=True):
            for a in ind["alertas"]: mostrar_alerta(a["tipo"], a["mensaje"])
        st.markdown("---")

    # ═══ HISTORIAL GARITA (SST) ═══
    st.markdown("### 🛂 Historial de Ingresos por Garita (Hoy)")
    hist = db.obtener_historial_hoy()
    if hist:
        df_h = pd.DataFrame(hist)[["placa", "nombre_trabajador", "cargo", "estado_soat", "fecha_ingreso"]].rename(columns={"placa": "Placa", "nombre_trabajador": "Nombre", "cargo": "Cargo", "estado_soat": "Estado SOAT", "fecha_ingreso": "Hora"})
        df_h["Hora"] = df_h["Hora"].apply(lambda x: str(x).split("T")[1][:8] if "T" in str(x) else str(x)[:8])
        st.dataframe(df_h.style.map(lambda v: "background-color: #c8e6c9; color: #1b5e20; font-weight: 600" if v == "Vigente" else "background-color: #ffcdd2; color: #b71c1c; font-weight: 700", subset=["Estado SOAT"]), use_container_width=True, height=300, hide_index=True)
        rechazados = len([h for h in hist if h.get("estado_soat") != "Vigente"])
        if rechazados > 0: mostrar_alerta("warning", f"⚠️ Atención: Hoy {rechazados} vehículo(s) ingresaron sin SOAT vigente. Se les envió correo automático.")
    else: st.info("📭 Sin ingresos registrados hoy.")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### 📋 Todos los Registros")
    _mostrar_tabla()

def _mostrar_graficos(ind):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 🚘 Por Tipo de Vehículo")
        if ind["por_tipo_vehiculo"]:
            df = pd.DataFrame([{"Tipo": k, "Cantidad": v} for k, v in ind["por_tipo_vehiculo"].items()])
            fig = px.pie(df, values="Cantidad", names="Tipo", hole=0.5, color_discrete_sequence=["#1a237e", "#f57f17"])
            fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.markdown("#### 💼 Por Cargo")
        if ind["por_cargo"]:
            df = pd.DataFrame([{"Cargo": k, "Cantidad": v} for k, v in ind["por_cargo"].items()]).sort_values("Cantidad")
            fig = px.bar(df, x="Cantidad", y="Cargo", orientation="h", color="Cantidad", color_continuous_scale="Blues")
            fig.update_layout(margin=dict(t=10, b=10, l=120, r=10), height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    st.markdown("#### 📅 Registros por Mes")
    if ind["por_mes"]:
        df = pd.DataFrame([{"Mes": k, "Registros": v} for k, v in ind["por_mes"].items()]).sort_values("Mes")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df["Mes"], y=df["Registros"], mode="lines+markers+text", text=df["Registros"], textposition="top center", line=dict(color="#1a237e", width=3), fill="tozeroy", fillcolor="rgba(26,35,126,0.08)"))
        fig.update_layout(margin=dict(t=20, b=40, l=40, r=20), height=300)
        st.plotly_chart(fig, use_container_width=True)

def _mostrar_tabla():
    todos = db.obtener_todos_trabajadores()
    if not todos: st.info("📭 No hay registros."); return
    df = pd.DataFrame(todos)[["identificacion", "nombres", "cargo", "correo", "tipo_vehiculo", "placa", "soat_estado", "soat_vigencia", "calidad_imagen_ok", "fecha_registro"]].rename(columns={"identificacion": "ID", "nombres": "Nombres", "cargo": "Cargo", "correo": "Correo", "tipo_vehiculo": "Tipo", "placa": "Placa", "soat_estado": "Estado SOAT", "soat_vigencia": "Vencimiento", "calidad_imagen_ok": "Imagen OK", "fecha_registro": "Fecha"})
    for c in ["Vencimiento", "Fecha"]: df[c] = df[c].apply(lambda x: str(x)[:10] if pd.notna(x) else "N/A")
    if "Imagen OK" in df.columns: df["Imagen OK"] = df["Imagen OK"].apply(lambda x: "✅ Sí" if x else "❌ No")
    st.dataframe(df.style.map(lambda v: "background-color: #c8e6c9; color: #1b5e20; font-weight: 600" if v=="Vigente" else ("background-color: #fff9c4; color: #f57f17; font-weight: 600" if v=="Por vencer" else ("background-color: #ffcdd2; color: #c62828; font-weight: 600" if v=="Vencido" else "background-color: #e1bee7; color: #6a1b9a; font-weight: 600")), subset=["Estado SOAT"]), use_container_width=True, height=400, hide_index=True)
    with st.expander("🗑️ Eliminar Registro"):
        st.warning("⚠️ Acción irreversible.")
        id_del = st.text_input("ID a eliminar")
        if st.button("Eliminar", type="primary"):
            if id_del.strip():
                if db.eliminar_trabajador(id_del.strip()): st.success("Eliminado."); st.rerun()
                else: st.error("No se pudo eliminar.")
