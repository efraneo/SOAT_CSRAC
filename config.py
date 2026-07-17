"""
config.py
Carga de configuración desde Streamlit Secrets (nube) o .env (local).
"""
import os
from dotenv import load_dotenv

# Cargar .env SOLO si estamos en local (no en Streamlit Cloud)
if os.path.exists("claves_soat.env"):
    load_dotenv("claves_soat.env")


def _obtener(clave: str, por_defecto: str = "") -> str:
    """
    Busca una variable en este orden:
    1. st.secrets (Streamlit Cloud)
    2. Variable de entorno del sistema
    3. Valor por defecto
    """
    try:
        import streamlit as st
        if clave in st.secrets:
            return st.secrets[clave]
    except Exception:
        pass

    valor = os.getenv(clave, por_defecto)
    return valor


class Config:
    """Configuración centralizada — funciona en local y en la nube."""

    # ── Supabase ──
    SUPABASE_URL: str = _obtener("SUPABASE_URL", "")
    SUPABASE_KEY: str = _obtener("SUPABASE_KEY", "")

    # ── SMTP / Correo ──
    EMAIL_HOST: str = _obtener("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(_obtener("EMAIL_PORT", "587"))
    EMAIL_USER: str = _obtener("EMAIL_USER", "")
    EMAIL_PASSWORD: str = _obtener("EMAIL_PASSWORD", "")
    EMAIL_FROM_NAME: str = _obtener("EMAIL_FROM_NAME", "Sistema SOAT")

    # ── Administrador ──
    ADMIN_EMAIL: str = _obtener("ADMIN_EMAIL", "admin@empresa.com")
    ADMIN_PASSWORD: str = _obtener("ADMIN_PASSWORD", "admin123")

    # ── 2FA ──
    TWO_FACTOR_EXPIRY_SECONDS: int = int(_obtener("TWO_FACTOR_EXPIRY_SECONDS", "300"))

    # ── Validación SOAT ──
    SOAT_ALERTA_DIAS: int = 30
    MIN_IMAGE_QUALITY_SCORE: float = 40.0
    MIN_IMAGE_WIDTH: int = 400
    MIN_IMAGE_HEIGHT: int = 300

    # ── Storage ──
    SOAT_STORAGE_BUCKET: str = "soat-archivos"

    # ── Tipos de vehículo ──
    TIPOS_VEHICULO: list = ["Automovil", "Motocicleta"]

    # ── Tesseract ──
    TESSERACT_CMD: str = _obtener("TESSERACT_CMD", "")

    @classmethod
    def validar(cls) -> bool:
        """Verifica que las credenciales esenciales estén configuradas."""
        errores = []
        if not cls.SUPABASE_URL:
            errores.append("SUPABASE_URL no configurada")
        if not cls.SUPABASE_KEY:
            errores.append("SUPABASE_KEY no configurada")
        if not cls.EMAIL_USER:
            errores.append("EMAIL_USER no configurado")
        if not cls.EMAIL_PASSWORD:
            errores.append("EMAIL_PASSWORD no configurado")
        if errores:
            for e in errores:
                print(f"⚠️  {e}")
            return False
        return True
