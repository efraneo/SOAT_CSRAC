import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import db, mostrar_alerta, mostrar_metrica_card, soat_validator

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

    with st.spinner("Cargando datos..."):
        ind = db.obtener_indicadores()
        todos_trab = db.obtener_todos_trabajadores()

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
    
    # ═══════════════════════════════════════════════════
    # SECCIÓN DE GESTIÓN COMPLETA (NUEVA)
    # ═══════════════════════════════════════════════════
    st.markdown("### ✏️ Gestión de Trabajadores")
    
    if not todos_trab:
        st.info("No hay trabajadores registrados todavía.")
    else:
        # Crear opciones para el selectbox: "Cedula - Nombre (Placa)" -> id (UUID)
        opciones = {f"{t.get('identificacion', 'N/A')} - {t.get('nombres', 'N/A')} ({t.get('placa', 'N/A')})": t["id"] for t in todos_trab}
        
        c1, c2 = st.columns([3, 2])
        with c1:
            seleccion = st.selectbox("🔎 Selecciona un trabajador de la lista:", list(opciones.keys()))
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            manual_id = st.text_input("O escribe el ID/Cédula manualmente:", placeholder="Opcional...")

        id_a_buscar = manual_id if manual_id else opciones.get(seleccion)
        
        if id_a_buscar:
            current = db.obtener_trabajador_por_id(id_a_buscar)
            
            # Si no encuentra por UUID, intentar buscar por Cédula por si el admin la escribió
            if not current:
                encontrados = [t for t in todos_trab if t.get('identificacion') == id_a_buscar]
                if encontrados:
                    current = db.obtener_trabajador_por_id(encontrados[0]["id"])

            if not current:
                mostrar_alerta("danger", "Trabajador no encontrado. Verifica el ID o Cédula.")
            else:
                mostrar_alerta("success", f"Gestionando a: {current.get('nombres')} - Placa: {current.get('placa')}")
                tab1, tab2, tab3, tab4 = st.tabs(["📝 Editar Info", "🔄 Estado SOAT", "📄 Soporte y Validación IA", "🗑️ Eliminar"])

                # ─── Pestaña 1: Editar Info ───
                with tab1:
                    with st.form("f_info"):
                        c1, c2 = st.columns(2)
                        with c1:
                            new_nom = st.text_input("👤 Nombre", value=current.get("nombres", ""))
                            new_car = st.text_input("💼 Cargo", value=current.get("cargo", ""))
                        with c2:
                            new_placa = st.text_input("🚘 Placa", value=current.get("placa", "")).upper()
                            new_tv = st.selectbox("🏷️ Tipo Vehículo", ["Automovil", "Motocicleta"], index=0 if current.get("tipo_vehiculo") == "Automovil" else 1)
                        
                        if st.form_submit_button("💾 Guardar Cambios", use_container_width=True, type="primary"):
                            datos = {"nombres": new_nom, "cargo": new_car, "placa": new_placa, "tipo_vehiculo": new_tv}
                            res = db.actualizar_trabajador(current["id"], datos)
                            if res["exito"]:
                                st.success("✅ Datos actualizados correctamente.")
                                st.rerun()
                            else:
                                st.error(f"Error: {res['mensaje']}")

                # ─── Pestaña 2: Estado SOAT y Mensajes ───
                with tab2:
                    st.markdown("#### 📊 Estado Actual")
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1:
                        estado_actual = current.get("soat_estado", "Pendiente")
                        st.metric("Estado SOAT", estado_actual)
                    with col_e2:
                        vigencia = current.get("soat_vigencia")
                        vig_str = str(vigencia)[:10] if vigencia else "Sin fecha"
                        st.metric("Vencimiento", vig_str)
                    with col_e3:
                        calidad = current.get("soat_calidad_imagen", 0)
                        st.metric("Calidad Imagen (Score)", round(calidad, 2))

                    st.markdown("---")
                    st.markdown("#### ⚙️ Forzar Estado Manual")
                    st.caption("Usa esto si la IA falló o si necesitas corregir un error de validación en la base de datos.")
                    
                    with st.form("f_estado"):
                        opciones_estado = ["Vigente", "Por vencer", "Vencido", "No legible", "Pendiente"]
                        index_est = opciones_estado.index(estado_actual) if estado_actual in opciones_estado else 4
                        nuevo_estado = st.selectbox("Forzar Nuevo Estado:", opciones_estado, index=index_est)
                        
                        if st.form_submit_button("🔄 Actualizar Estado", use_container_width=True, type="primary"):
                            res = db.actualizar_trabajador(current["id"], {"soat_estado": nuevo_estado})
                            if res["exito"]:
                                st.success(f"✅ Estado forzado a: {nuevo_estado}")
                                st.rerun()
                            else:
                                st.error(f"Error: {res['mensaje']}")

                # ─── Pestaña 3: Soporte y Re-Validación IA ───
                with tab3:
                    st.markdown("#### 📄 Soporte Actual")
                    url_actual = current.get("soat_url", "")
                    if url_actual:
                        if ".pdf" in url_actual:
                            st.markdown(f"📎 [Ver PDF Actual]({url_actual})")
                        else:
                            st.image(url_actual, caption="Soporte actual", width=400)
                    else:
                        st.warning("No hay soporte cargado actualmente.")
                        
                    st.markdown("---")
                    st.markdown("#### ⬆️ Subir Nuevo Soporte (Re-Validación con IA)")
                    nuevo_img = st.file_uploader("Adjunta una nueva imagen o PDF del SOAT", type=["jpg", "jpeg", "png", "pdf"], key="img_edit_admin")
                    
                    if nuevo_img:
                        if nuevo_img.type != "application/pdf":
                            st.image(nuevo_img, caption="Nuevo archivo a procesar", width=400)
                        else:
                            mostrar_alerta("info", f"PDF '{nuevo_img.name}' seleccionado. Listo para analizar.")
                            
                        if st.button("🤖 Subir, Analizar con IA y Actualizar", use_container_width=True, type="primary"):
                            with st.spinner("Analizando el documento con OpenAI Vision..."):
                                bytes_img = nuevo_img.read()
                                
                                # 1. Validamos con la IA localmente para obtener el mensaje
                                res_soat = soat_validator.validar_archivo(bytes_img, nuevo_img.name)
                                
                                # 2. Subimos y actualizamos en Supabase
                                res_db = db.actualizar_trabajador(current["id"], {}, bytes_img, nuevo_img.name)
                                
                                if res_db["exito"]:
                                    st.success("✅ Soporte actualizado y guardado en la base de datos.")
                                    # Mostramos el mensaje que devolvió la IA
                                    if res_soat["calidad_ok"]:
                                        tipo_alerta = "success" if res_soat["estado"] == "Vigente" else "warning"
                                        mostrar_alerta(tipo_alerta, f"Resultado IA: {res_soat['mensaje_general']}")
                                        if res_soat["fecha_vencimiento"]:
                                            st.info(f"Nueva fecha detectada: {res_soat['fecha_vencimiento'].strftime('%d/%m/%Y')}")
                                    else:
                                        mostrar_alerta("danger", f"Error de calidad: {res_soat['mensaje_general']}")
                                    st.rerun()
                                else:
                                    st.error(f"Error al actualizar en DB: {res_db['mensaje']}")

                # ─── Pestaña 4: Eliminar ───
                with tab4:
                    st.warning("⚠️ Acción irreversible.")
                    st.markdown(f"Estás a punto de eliminar a **{current.get('nombres')}** con cédula **{current.get('identificacion')}**.")
                    if st.button("🗑️ Confirmar Eliminación", use_container_width=True, type="primary"):
                        if db.eliminar_trabajador(current["id"]):
                            st.success("✅ Trabajador eliminado correctamente.")
                            st.rerun()
                        else:
                            st.error("Error al eliminar.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
    st.markdown("### 📋 Base de Datos Completa")
    _mostrar_tabla(todos_trab)

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
    if val == "Vigente":
        return "background-color: #c8e6c9; color: #1b5e20; font-weight:600"
    elif val == "Por vencer":
        return "background-color: #fff9c4; color: #f57f17; font-weight: 600"
    elif val == "Vencido":
        return "background-color: #ffcdd2; color: #c62828; font-weight: 600"
    elif val == "No legible":
        return "background-color: #e1bee7; color: #6a1b9a; font-weight: 600"
    return "background-color: #e0e0e0; color: #616161; font-weight: 600"

def _mostrar_tabla(todos):
    if not todos:
        st.info("📭 Base de datos vacía.")
        return

    df = pd.DataFrame(todos)[
        ["identificacion", "nombres", "cargo", "tipo_vehiculo", "placa", "soat_estado", "soat_vigencia", "fecha_registro"]
    ].rename(columns={
        "identificacion": "ID/Cédula", "nombres": "Nombre", "cargo": "Cargo",
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
