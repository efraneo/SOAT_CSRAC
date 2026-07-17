"""
views/login_view.py
Pantalla de autenticación del administrador.
"""
import streamlit as st
from config import Config
from utils import mostrar_alerta


def mostrar():
    """Pantalla de login del administrador."""
    col1, col2, col3 = st.columns([1, 1, 1])

    with col2:
        st.markdown("""
        <div class="main-title" style="margin-top:80px;">
            <h1>🔐 Acceso Administrador</h1>
            <p>Ingresa tus credenciales para acceder al panel de gestión</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        with st.form("form_login"):
            email = st.text_input("📧 Correo electrónico", placeholder="admin@empresa.com")
            password = st.text_input("🔑 Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True)

            if submitted:
                if email == Config.ADMIN_EMAIL and password == Config.ADMIN_PASSWORD:
                    st.session_state["admin_autenticado"] = True
                    st.rerun()
                else:
                    mostrar_alerta("danger", "Credenciales incorrectas. Intenta de nuevo.")

        st.markdown("---")
        st.markdown("""
        <div style="text-align:center;">
            <p style="color:#999; font-size:12px;">
                ¿Eres trabajador? <a href="#" onclick="window.location.reload()">
                Regresa al formulario de registro</a>
            </p>
        </div>
        """, unsafe_allow_html=True)
