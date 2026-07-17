"""
app.py
Punto de entrada de la aplicación — Orquestador de pantallas.
"""
import subprocess
import os

# ═══════════════════════════════════════════════════════════
#  INSTALAR TESSERACT EN STREAMLIT CLOUD (solo si no existe)
# ═══════════════════════════════════════════════════════════
_tesseract_path = "/usr/bin/tesseract"
if not os.path.exists(_tesseract_path):
    print("🔧 Instalando Tesseract OCR en el servidor...")
    try:
        subprocess.run(["apt-get", "update"], capture_output=True, check=True)
        subprocess.run(
            ["apt-get", "install", "-y", "tesseract-ocr", "tesseract-ocr-spa"],
            capture_output=True, check=True
        )
        print("✅ Tesseract instalado correctamente.")
    except Exception as e:
        print(f"⚠️ No se pudo instalar Tesseract: {e}")

# ═══════════════════════════════════════════════════════════
#  IMPORTACIONES Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════
import streamlit as st
from config import Config
from styles import cargar_estilos
from views.landing_view import mostrar as pantalla_seleccion
from views.login_view import mostrar as pantalla_login
from views.registro_view import mostrar as pantalla_registro
from views.admin_view import mostrar as pantalla_admin

st.set_page_config(
    page_title="Sistema de Registro SOAT",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

cargar_estilos()

# ═══════════════════════════════════════════════════════════
#  FLUJO PRINCIPAL
# ═══════════════════════════════════════════════════════════
def main():
    if not Config.validar():
        st.error("""
        ## ⚠️ Configuración Incompleta
        Falta configurar variables en Streamlit Secrets (nube) o `claves_soat.env` (local):
        ```
        SUPABASE_URL=tu_url
        SUPABASE_KEY=tu_key
        EMAIL_USER=tu_correo
        EMAIL_PASSWORD=tu_password
        ```
        """)
        st.stop()

    if st.session_state.get("admin_autenticado"):
        pantalla_admin()
    elif st.session_state.get("modo") == "admin":
        pantalla_login()
    elif st.session_state.get("modo") == "registro":
        pantalla_registro()
    else:
        pantalla_seleccion()

if __name__ == "__main__":
    main()
