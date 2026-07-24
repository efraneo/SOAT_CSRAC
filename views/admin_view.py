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

    # ═══ KPIs ═══
    st.markdown("### 📈 Indicadores Generales")
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

    # ═══ HISTORIAL GARITA ═══
    st.markdown("### 🛂 Garita (Hoy)")
    hist = db.obtener_historial_hoy()
    if hist:
        df_h = pd.DataFrame(hist)[["placa", "nombre_trabajador", "estado_soat", "fecha_ingreso"]].rename(
            columns={"placa": "Placa", "nombre_trabajador": "Nombre", "estado_soat": "Estado", "fecha_ingreso": "Hora"}
        )
        df_h["Hora"] = df_h["Hora"].apply(lambda x: str(x).split("T")[1][:8] if "T" in str(x) else str(x)[:8])
        st.dataframe(
            df_h.style.map(
                lambda v: "background-color: #c8e6c9; color: #1b5e20; font-weight: 600" if v == "Vigente" else "background-color: #ffcdd2; color: #b71c1c; font-weight: 700",
                subset=["Estado"]
            ),
            use_container_width=True, height=200, hide_index=True
        )
    else:
        st.info("📭 Sin ingresos hoy.")
    
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════
    #  GESTIÓN COMPLETA DEL TRABAJADOR (4 PESTAÑAS)
    # ═══════════════════════════════════════════════════════════
    st.markdown("### ✏️ Gestión de Registros por ID")
    id_buscar = st.text_input("🔑 Digite el ID del trabajador:", placeholder="Péguelo aquí el ID de la tabla de abajo...", key="id_gestion")

    if id_buscar:
        current = db.obtener_trabajador_por_id(id_buscar)
        if not current:
            mostrar_alerta("danger", "ID no encontrado en la base de datos.")
        else:
            mostrar_alerta("success", f"Registro encontrado: **{current.get('nombres')}** — Placa: **{current.get('placa')}** (Estado actual: **{current.get('soat_estado')}**)")

            tab1, tab2, tab3, tab4 = st.tabs([
                "📝 Info Básica", 
                "🔄 Estado SOAT", 
                "👁 Ver/Reemplazar Soporte", 
                "🗑️ Eliminar"
            ])

            # ── PESTAÑA 1: Editar Datos Básicos ──
            with tab1:
                with st.form("form_editar_info"):
                    c1, c2 = st.columns(2)
                    with c1:
                        new_nom = st.text_input("👤 Nombre", value=current.get("nombres", ""))
                        new_car = st.text_input("💼 Cargo", value=current.get("cargo", ""))
                    with c2:
                        new_placa = st.text_input("🚘 Placa", value=current.get("placa", ""))
                        new_tv = st.selectbox(
                            "🏷️ Tipo Vehículo", 
                            ["Automovil", "Motocicleta"], 
                            index=0 if current.get("tipo_vehiculo") == "Automovil" else 1
                        )
                    
                    if st.form_submit_button("💾 Guardar Datos", use_container_width=True):
                        datos = {
                            "nombres": new_nom, 
                            "cargo": new_car, 
                            "placa": new_placa.upper(), 
                            "tipo_vehiculo": new_tv
                        }
                        res = db.actualizar_trabajador(id_buscar, datos)
                        if res["exito"]:
                            st.success("✅ Datos básicos actualizados correctamente.")
                            st.rerun()
                        else:
                            st.error(f"Error: {res['mensaje']}")

            # ── PESTAÑA 2: Cambiar Estado SOAT (SIN subir archivos) ──
            with tab2:
                st.markdown("Si un trabajador te entregó el PDF físico y está vigente, puedes actualizar su estado aquí rápidamente sin subir archivo nuevo.")
                
                with st.form("form_cambiar_estado"):
                    # Mostrar estado actual grande
                    estado_actual = current.get("soat_estado", "Pendiente")
                    color_estado = {
                        "Vigente": "#2e7d32",
                        "Por vencer": "#f57f17",
                        "Vencido": "#c62828",
                        "No legible": "#6a1b9a",
                        "Pendiente": "#607d8b"
                    }
                    st.markdown(f"Estado Actual: <span style='color:{color_estado.get(estado_actual, '#333')}; font-weight:700; font-size: 20px;'>{estado_actual.upper()}</span>", unsafe_allow_html=True)
                    
                    nuevo_estado = st.selectbox(
                        "Nuevo Estado SOAT",
                        ["Vigente", "Por vencer", "Vencido", "No legible", "Pendiente"],
                        index=0 if estado_actual == "Vigente" else (
                            1 if estado_actual == "Por vencer" else (
                                2 if estado_actual == "Vencido" else (
                                    3 if estado_actual == "No legible" else 4
                                )
                            )
                        )
                    )
                    
                    if st.form_submit_button("🔄 Cambiar Estado", use_container_width=True, type="primary"):
                        res = db.actualizar_trabajador(id_buscar, {"soat_estado": nuevo_estado})
                        if res["exito"]:
                            st.success(f"✅ Estado actualizado a: **{nuevo_estado}**")
                            st.rerun()
                        else:
                            st.error(f"Error: {res['mensaje']}")

            # ── PESTAÑA 3: Ver y Reemplazar Soporte (PDF/Imagen) ──
            with tab3:
                st.markdown("Aquí puedes ver el soporte actual del trabajador y subir el PDF/Imagen nueva si te lo entregaron actualizado.")
                
                # 1. Ver imagen actual
                url_actual = current.get("soat_url", "")
                if url_actual:
                    st.markdown("#### 📄 Soporte Actual")
                    try:
                        if ".pdf" in url_actual:
                            st.markdown(f"📎 Es un archivo PDF. [Ver en navegador]({url_actual})")
                        else:
                            st.image(url_actual, caption="Soporte actual", width=400)
                    except Exception:
                        st.markdown("No se pudo cargar la imagen desde la URL.")
                
                st.markdown("---")
                st.markdown("#### 📤 Subir Nuevo Soporte (Opcional)")
                new_img = st.file_uploader(
                    "📎 Adjuntar nuevo soporte (Img o PDF)", 
                    type=["jpg", "jpeg", "png", "pdf"], 
                    key="img_edit"
                )
                if new_img:
                    st.markdown("**Vista previa del archivo que vas a subir:**")
                    if new_img.type != "application/pdf":
                        st.image(new_img, caption="Nuevo archivo", width=400)
                    else:
                        mostrar_alerta("success", f"📄 PDF '{new_img.name}' seleccionado. Se procesará al presionar el botón de abajo.")
                        
                    if st.button("🔄 Subir y Actualizar Soporte", use_container_width=True, type="primary"):
                        with st.spinner("🔄 Subiendo y re-analizando con IA..."):
                            bytes_img = new_img.read()
                            # Se pasa archivo vacío para que solo actualice la imagen y el estado
                            res = db.actualizar_trabajor(id_buscar, {}, bytes_img, new_img.name)
                            if res["exito"]:
                                st.success("✅ Soporte reemplazado y re-analizado correctamente.")
                                st.rerun()
                            else:
                                st.error(f"Error: {res['mensaje']}")

            # ── PESTAÑA 4: Eliminar ──
            with tab4:
                st.warning("Esta acción no tiene vuelta. Se eliminará el trabajador y su archivo.")
                if st.button("⚠️ Eliminar Registro", type="primary"):
                    if db.eliminar_trabajador(id_buscar):
                        st.success("Registro eliminado permanentemente.")
                        st.rerun()
                    else:
                        st.error("No se pudo eliminar.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### 📋 Base de Datos Completa")
    _mostrar_tabla()

# ═══ GRÁFICOS ═══
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
        fig.add_trace(go.Scatter(
            x=df["Mes"], y=df["Registros"], mode="lines+markers+text", 
            text=df["Registros"], textposition="top center", 
            line=dict(color="#1a237e", width=3), 
            fill="tozeroy", fillcolor="rgba(26,35,126,0.08)"
        ))
        fig.update_layout(margin=dict(t=20, b=40, l=40, r=20), height=250)
        st.plotly_chart(fig, use_container_width=True)

# ═══ TABLA DE DATOS ═══
def _mostrar_tabla():
    todos = db.obtener_todos_trabajadores()
    if not todos:
        st.info("📭 Base de datos vacía.")
        return

    df = pd.DataFrame(todos)[
        ["identificacion", "nombres", "cargo", "tipo_vehiculo", "placa", "soat_estado", "soat_vigencia", "fecha_registro"]
    ].rename(columns={
        "identificacion": "ID", "nombres": "Nombre", "cargo": "cargo", 
        "tipo_vehiculo": "Tipo", "placa": "Placa", 
        "soat_estado": "Estado SOAT", "soat_vigencia": "Vencimiento", 
        "fecha_registro": "Fecha Registro"
    })
    
    for c in ["Vencimiento", "Fecha Registro"]:
        df[c] = df[c].apply(lambda x: str(x)[:10] if pd.notna(x) else "N/A")
    
    st.dataframe(
        df.style.map(
            lambda v: (
                "background-color: #c8e6c9; color: #1b5e20; font-weight: 600" if v == "Vigente" else
                ("background-color: #fff9c4; color: #f57f17; font-weight: 600" if v == "Por vencer" else
                ("background-color: #ffcdd2; color: #c62828; font-weight: 600" if v == "Vencido" else
                ("background-color: #e1bee7; color: #6a1b9a; font-weight: 600" if v == "No legible" else
                "background-color: #e0e0e0; color: #616161; font-weight: 600"))
            ),
            subset=["Estado SOAT"],
            use_container_width=True, height=400, hide_index=True
        )
