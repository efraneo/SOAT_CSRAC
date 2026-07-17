"""
views/admin_view.py
Panel de administración con indicadores y gestión de registros.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils import db, mostrar_alerta, mostrar_metrica_card


def mostrar():
    """Panel de administración completo."""

    # Botón cerrar sesión
    if st.button("🚪 Cerrar Sesión", key="btn_cerrar_sesion"):
        st.session_state["admin_autenticado"] = False
        st.rerun()

    st.markdown("""
    <div class="main-title">
        <h1>📊 Panel de Administración</h1>
        <p>Sistema de Registro y Control de SOAT</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    with st.spinner("Cargando indicadores..."):
        ind = db.obtener_indicadores()

    # ── KPIs Principales ──
    st.markdown("### 📈 Indicadores Generales")
    cols_kpi = st.columns(6)
    with cols_kpi[0]:
        mostrar_metrica_card("👥", ind["total"], "Total Registros", "#1a237e")
    with cols_kpi[1]:
        mostrar_metrica_card("✅", ind["vigentes"], "SOAT Vigentes", "#2e7d32")
    with cols_kpi[2]:
        mostrar_metrica_card("⚠️", ind["por_vencer"], "Por Vencer", "#f57f17")
    with cols_kpi[3]:
        mostrar_metrica_card("🚨", ind["vencidos"], "Vencidos", "#c62828")
    with cols_kpi[4]:
        mostrar_metrica_card("📷", ind["no_legibles"], "No Legibles", "#6a1b9a")
    with cols_kpi[5]:
        mostrar_metrica_card("⏳", ind["pendientes"], "Pendientes", "#607d8b")

    # ── Barras de progreso ──
    st.markdown("### 📊 Distribución de Estados")
    col_bar1, col_bar2 = st.columns(2)
    with col_bar1:
        st.markdown(f"**✅ Vigentes:** {ind['vigentes']} ({ind['pct_vigentes']}%)")
        st.progress(ind["pct_vigentes"] / 100)
    with col_bar2:
        st.markdown(f"**⚠️ Por Vencer:** {ind['por_vencer']} ({ind['pct_por_vencer']}%)")
        st.progress(ind["pct_por_vencer"] / 100)

    col_bar3, col_bar4 = st.columns(2)
    with col_bar3:
        st.markdown(f"**🚨 Vencidos:** {ind['vencidos']} ({ind['pct_vencidos']}%)")
        st.progress(ind["pct_vencidos"] / 100)
    with col_bar4:
        st.markdown(f"**📷 No Legibles:** {ind['no_legibles']} ({ind['pct_no_legibles']}%)")
        st.progress(ind["pct_no_legibles"] / 100)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Gráficos ──
    if ind["total"] > 0:
        _mostrar_graficos(ind)

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Alertas ──
    if ind["alertas"]:
        st.markdown("### 🔔 Alertas Activas")
        with st.expander(f"Ver {len(ind['alertas'])} alerta(s)", expanded=True):
            for alerta in ind["alertas"]:
                mostrar_alerta(alerta["tipo"], alerta["mensaje"])
        st.markdown("---")

    # ── Tabla de Registros ──
    _mostrar_tabla_registros()


# ───────────────────────────────────────────────────────
#  GRÁFICOS
# ───────────────────────────────────────────────────────
def _mostrar_graficos(ind):
    col_graf1, col_graf2 = st.columns(2)

    # Pie: Tipo de vehículo
    with col_graf1:
        st.markdown("#### 🚘 Distribución por Tipo de Vehículo")
        if ind["por_tipo_vehiculo"]:
            df_tipo = pd.DataFrame([
                {"Tipo": k, "Cantidad": v}
                for k, v in ind["por_tipo_vehiculo"].items()
            ])
            fig_pie = px.pie(
                df_tipo, values="Cantidad", names="Tipo",
                color_discrete_sequence=["#1a237e", "#f57f17", "#2e7d32", "#c62828"],
                hole=0.5
            )
            fig_pie.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                height=300, showlegend=True,
                legend=dict(font=dict(size=12))
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("Sin datos aún.")

    # Barras: Por cargo
    with col_graf2:
        st.markdown("#### 💼 Distribución por Cargo")
        if ind["por_cargo"]:
            df_cargo = pd.DataFrame([
                {"Cargo": k, "Cantidad": v}
                for k, v in ind["por_cargo"].items()
            ]).sort_values("Cantidad", ascending=True)

            fig_bar = px.bar(
                df_cargo, x="Cantidad", y="Cargo",
                orientation="h", color="Cantidad",
                color_continuous_scale="Blues"
            )
            fig_bar.update_layout(
                margin=dict(t=10, b=10, l=120, r=10),
                height=300, showlegend=False,
                yaxis=dict(tickfont=dict(size=11))
            )
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("Sin datos aún.")

    # Línea: Registros por mes
    st.markdown("#### 📅 Registros por Mes")
    if ind["por_mes"]:
        df_mes = pd.DataFrame([
            {"Mes": k, "Registros": v}
            for k, v in ind["por_mes"].items()
        ]).sort_values("Mes")

        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=df_mes["Mes"], y=df_mes["Registros"],
            mode="lines+markers+text",
            text=df_mes["Registros"], textposition="top center",
            line=dict(color="#1a237e", width=3),
            marker=dict(size=10, color="#1a237e"),
            fill="tozeroy", fillcolor="rgba(26,35,126,0.08)"
        ))
        fig_line.update_layout(
            margin=dict(t=20, b=40, l=40, r=20), height=300,
            xaxis=dict(tickfont=dict(size=11)),
            yaxis=dict(tickfont=dict(size=11))
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Sin datos de meses aún.")


# ───────────────────────────────────────────────────────
#  TABLA DE REGISTROS
# ───────────────────────────────────────────────────────
def _mostrar_tabla_registros():
    st.markdown("### 📋 Todos los Registros")
    todos = db.obtener_todos_trabajadores()

    if not todos:
        st.info("📭 No hay registros aún. Aparecerán cuando los trabajadores se registren.")
        return

    df = pd.DataFrame(todos)

    columnas_mostrar = [
        "identificacion", "nombres", "cargo", "correo",
        "tipo_vehiculo", "placa", "soat_estado",
        "soat_vigencia", "calidad_imagen_ok", "fecha_registro"
    ]
    columnas_existentes = [c for c in columnas_mostrar if c in df.columns]
    df_mostrar = df[columnas_existentes].copy()

    renombres = {
        "identificacion": "Identificación", "nombres": "Nombres",
        "cargo": "Cargo", "correo": "Correo",
        "tipo_vehiculo": "Tipo Vehículo", "placa": "Placa",
        "soat_estado": "Estado SOAT", "soat_vigencia": "Vencimiento SOAT",
        "calidad_imagen_ok": "Imagen OK", "fecha_registro": "Fecha Registro"
    }
    df_mostrar = df_mostrar.rename(columns=renombres)

    for col_fecha in ["Vencimiento SOAT", "Fecha Registro"]:
        if col_fecha in df_mostrar.columns:
            df_mostrar[col_fecha] = df_mostrar[col_fecha].apply(
                lambda x: str(x)[:10] if pd.notna(x) else "N/A"
            )

    if "Imagen OK" in df_mostrar.columns:
        df_mostrar["Imagen OK"] = df_mostrar["Imagen OK"].apply(
            lambda x: "✅ Sí" if x else "❌ No"
        )

    def colorear_estado(estado):
        colores = {
            "Vigente": "background-color: #c8e6c9; color: #1b5e20; font-weight: 600",
            "Por vencer": "background-color: #fff9c4; color: #f57f17; font-weight: 600",
            "Vencido": "background-color: #ffcdd2; color: #c62828; font-weight: 600",
            "No legible": "background-color: #e1bee7; color: #6a1b9a; font-weight: 600",
            "Pendiente": "background-color: #e0e0e0; color: #616161; font-weight: 600"
        }
        return colores.get(estado, "")

    if "Estado SOAT" in df_mostrar.columns:
        st.dataframe(
            df_mostrar.style.map(colorear_estado, subset=["Estado SOAT"]),
            use_container_width=True, height=400, hide_index=True
        )
    else:
        st.dataframe(df_mostrar, use_container_width=True, height=400, hide_index=True)

    # Eliminar registros
    st.markdown("---")
    with st.expander("🗑️ Eliminar Registro"):
        st.warning("⚠️ Esta acción es irreversible.")
        id_eliminar = st.text_input("ID del registro a eliminar", placeholder="UUID...")
        if st.button("Eliminar permanentemente", type="primary"):
            if id_eliminar.strip():
                if db.eliminar_trabajador(id_eliminar.strip()):
                    st.success("Registro eliminado correctamente.")
                    st.rerun()
                else:
                    st.error("No se pudo eliminar. Verifica el ID.")
            else:
                st.error("Ingresa un ID válido.")
