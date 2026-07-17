"""
views/landing_view.py
Pantalla inicial con selección de rol (Trabajador / Administrador).
"""
import streamlit as st


def mostrar():
    """Pantalla inicial con selección de rol."""
    st.markdown("""
    <div class="main-title" style="margin-top:60px;">
        <h1>🚗 Sistema de Registro SOAT</h1>
        <p>Control vehicular empresarial — Selección de acceso</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.markdown("")

    with col2:
        # Tarjeta de trabajador
        st.markdown("""
        <div style="background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
                    border-radius:16px; padding:32px; text-align:center;
                    border:2px solid #a5d6a7; margin-bottom:16px;
                    box-shadow: 0 4px 16px rgba(46,125,50,0.1);">
            <div style="font-size:48px; margin-bottom:8px;">👷</div>
            <h3 style="color:#1b5e20; margin:0 0 8px;">Trabajador</h3>
            <p style="color:#2e7d32; font-size:13px; margin:0;">
                Registro de datos y SOAT
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("👷 Ingresar como Trabajador", use_container_width=True,
                     type="primary"):
            st.session_state["modo"] = "registro"
            st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        # Tarjeta de admin
        st.markdown("""
        <div style="background: linear-gradient(135deg, #e8eaf6, #c5cae9);
                    border-radius:16px; padding:32px; text-align:center;
                    border:2px solid #9fa8da;
                    box-shadow: 0 4px 16px rgba(26,35,126,0.1);">
            <div style="font-size:48px; margin-bottom:8px;">🔐</div>
            <h3 style="color:#1a237e; margin:0 0 8px;">Administrador</h3>
            <p style="color:#283593; font-size:13px; margin:0;">
                Panel de indicadores y gestión
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("🔐 Ingresar como Administrador", use_container_width=True):
            st.session_state["modo"] = "admin"
            st.rerun()

    with col3:
        st.markdown("")
