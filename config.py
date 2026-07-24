"""
config.py
Carga de configuración desde Streamlit Secrets (nube) o claves_soat.env (local).
"""
import os
import json
from dotenv import load_dotenv

if os.path.exists("claves_soat.env"):
    load_dotenv("claves_soat.env")

def _obtener(clave: str, por_defecto: str = "") -> str:
    try:
        import streamlit as st
        if clave in st.secrets: return st.secrets[clave]
    except Exception: pass
    return os.getenv(clave, por_defecto)

def _obtener_garita_users() -> dict:
    try:
        import streamlit as st
        if "GARITA_USERS" in st.secrets: return dict(st.secrets["GARITA_USERS"])
    except Exception: pass
    garita_str = os.getenv("GARITA_USERS", '{"porteria@empresa.com": "1234", "sst@empresa.com": "1234"}')
    try: return json.loads(garita_str)
    except Exception: return {"porteria@empresa.com": "1234", "sst@empresa.com": "1234"}

class Config:
    SUPABASE_URL: str = _obtener("SUPABASE_URL", "")
    SUPABASE_KEY: str = _obtener("SUPABASE_KEY", "")
    EMAIL_HOST: str = _obtener("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT: int = int(_obtener("EMAIL_PORT", "587"))
    EMAIL_USER: str = _obtener("EMAIL_USER", "")
    EMAIL_PASSWORD: str = _obtener("EMAIL_PASSWORD", "")
    EMAIL_FROM_NAME: str = _obtener("EMAIL_FROM_NAME", "Sistema SOAT")
    ADMIN_EMAIL: str = _obtener("ADMIN_EMAIL", "admin@empresa.com")
    ADMIN_PASSWORD: str = _obtener("ADMIN_PASSWORD", "admin123")
    TWO_FACTOR_EXPIRY_SECONDS: int = int(_obtener("TWO_FACTOR_EXPIRY_SECONDS", "300"))
    OPENAI_API_KEY: str = _obtener("OPENAI_API_KEY", "")

    # ═══ UMBRALES DE CALIDAD (CORREGIDOS PARA NO RECHAZAR VÁLIDOS) ═══
    SOAT_ALERTA_DIAS: int = 30
    MIN_IMAGE_QUALITY_SCORE: float = 15.0  # Bajado de 40 a 15 para no rechazar fotos de celular
    MIN_IMAGE_WIDTH: int = 250               # Bajado de 400 a 250
    MIN_IMAGE_HEIGHT: int = 200              # Bajado de 300 a 200

    SOAT_STORAGE_BUCKET: str = "soat-archivos"
    TIPOS_VEHICULO: list = ["Automovil", "Motocicleta"]
    GARITA_USERS: dict = _obtener_garita_users()

    @classmethod
    def validar(cls) -> bool:
        errores = []
        if not cls.SUPABASE_URL: errores.append("SUPABASE_URL no configurada")
        if not cls.SUPABASE_KEY: errores.append("SUPABASE_KEY no configurada")
        if not cls.EMAIL_USER: errores.append("EMAIL_USER no configurado")
        if not cls.EMAIL_PASSWORD: errores.append("EMAIL_PASSWORD no configurado")
        if errores:
            for e in errores: print(f"⚠️  {e}")
            return False
        return True
