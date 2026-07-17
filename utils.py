"""
utils.py
Funciones auxiliares compartidas e inicialización de servicios.
"""
import re
import streamlit as st
from datetime import date

from config import Config
from database import Database
from email_service import EmailService
from soat_validator import SOATValidator
from two_factor import TwoFactorAuth

# ═══════════════════════════════════════════════════════════
#  INSTANCIAS GLOBALES DE SERVICIOS
# ═══════════════════════════════════════════════════════════
db = Database()
email_svc = EmailService()
soat_validator = SOATValidator()
tfa = TwoFactorAuth()


# ═══════════════════════════════════════════════════════════
#  VALIDACIONES
# ═══════════════════════════════════════════════════════════

def validar_email(email: str) -> bool:
    """Valida formato de correo electrónico."""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(patron, email))


def validar_placa(placa: str, tipo_vehiculo: str) -> bool:
    """Valida formato de placa según tipo de vehículo (Colombia)."""
    placa = placa.upper().strip()
    if tipo_vehiculo == "Automovil":
        return bool(re.match(r'^[A-Z]{3}\d{3}$', placa))
    elif tipo_vehiculo == "Motocicleta":
        return bool(re.match(r'^[A-Z]{3}\d{2}[A-Z]$', placa))
    return False


def formatear_fecha_iso(fecha: date) -> str:
    """Convierte date a string ISO para Supabase."""
    return fecha.isoformat()


# ═══════════════════════════════════════════════════════════
#  COMPONENTES DE UI
# ═══════════════════════════════════════════════════════════

def mostrar_alerta(tipo: str, mensaje: str):
    """Muestra una alerta estilizada en la interfaz."""
    cls = f"alerta-{tipo}"
    iconos = {"danger": "🚨", "warning": "⚠️", "info": "ℹ️", "success": "✅"}
    icono = iconos.get(tipo, "")
    st.markdown(f'<div class="{cls}">{icono} {mensaje}</div>', unsafe_allow_html=True)


def mostrar_metrica_card(icono: str, valor, etiqueta: str, color: str = "#1a237e"):
    """Muestra una tarjeta métrica individual."""
    html = f'''
    <div class="metric-card" style="text-align:center; border-top: 4px solid {color};">
        <div style="font-size:2rem; margin-bottom:4px;">{icono}</div>
        <div style="font-size:2rem; font-weight:800; color:{color};">{valor}</div>
        <div style="font-size:0.85rem; color:#666; margin-top:2px;">{etiqueta}</div>
    </div>
    '''
    st.markdown(html, unsafe_allow_html=True)
