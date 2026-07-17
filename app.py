import subprocess
import sys
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
#  AHORA SÍ, LAS IMPORTACIONES NORMALES
# ═══════════════════════════════════════════════════════════
"""
app.py
Aplicación principal Streamlit - Sistema de Registro SOAT
"""
import streamlit as st
import re
from datetime import date, datetime
from config import Config
from database import Database
from email_service import EmailService
from soat_validator import SOATValidator
from two_factor import TwoFactorAuth

# ═══════════════════════════════════════════════════════════
#  CONFIGURACIÓN DE PÁGINA
# ═══════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Sistema de Registro SOAT",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ═══════════════════════════════════════════════════════════
#  ESTILOS CSS PERSONALIZADOS
# ═══════════════════════════════════════════════════════════
estilos_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif !important;
    }

    /* Ocultar elementos por defecto de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Tarjetas métricas */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        border: 1px solid rgba(0,0,0,0.05);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }

    /* Alertas */
    .alerta-danger {
        background: #ffebee;
        border-left: 4px solid #c62828;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
        font-size: 13px;
        color: #b71c1c;
    }
    .alerta-warning {
        background: #fff8e1;
        border-left: 4px solid #f57f17;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
        font-size: 13px;
        color: #e65100;
    }
    .alerta-info {
        background: #e8eaf6;
        border-left: 4px solid #283593;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
        font-size: 13px;
        color: #1a237e;
    }
    .alerta-success {
        background: #e8f5e9;
        border-left: 4px solid #2e7d32;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 8px 0;
        font-size: 13px;
        color: #1b5e20;
    }

    /* Botón principal mejorado */
    div.stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a237e, #283593) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px 32px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        transition: all 0.3s !important;
        box-shadow: 0 4px 16px rgba(26,35,126,0.3) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0d1557, #1a237e) !important;
        box-shadow: 0 6px 24px rgba(26,35,126,0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* Input fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div {
        border-radius: 8px !important;
        border: 1px solid #ddd !important;
    }

    /* Título principal */
    .main-title {
        text-align: center;
        margin-bottom: 8px;
    }
    .main-title h1 {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #1a237e, #283593, #3949ab);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
    }
    .main-title p {
        color: #666;
        font-size: 1rem;
        margin-top: 4px;
    }

    /* Separador */
    .divider {
        height: 2px;
        background: linear-gradient(90deg, transparent, #1a237e, transparent);
        margin: 24px 0;
        border-radius: 2px;
    }

    /* Tabla estilizada */
    .dataframe th {
        background-color: #1a237e !important;
        color: white !important;
        font-weight: 600 !important;
        text-align: left !important;
    }
    .dataframe td {
        padding: 10px 12px !important;
        font-size: 13px !important;
    }
    .dataframe tr:nth-child(even) {
        background-color: #f8f9ff !important;
    }
    .dataframe tr:hover {
        background-color: #e8eaf6 !important;
    }

    /* Steps/Progress */
    .step-indicator {
        display: flex;
        justify-content: center;
        gap: 8px;
        margin: 20px 0;
    }
    .step-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #ddd;
        transition: all 0.3s;
    }
    .step-dot.active {
        background: #1a237e;
        box-shadow: 0 0 8px rgba(26,35,126,0.4);
    }
    .step-dot.completed {
        background: #2e7d32;
    }
</style>
"""
st.markdown(estilos_css, unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  INICIALIZAR SERVICIOS
# ═══════════════════════════════════════════════════════════
db = Database()
email_svc = EmailService()
soat_validator = SOATValidator()
tfa = TwoFactorAuth()

# ═══════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
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


# ═══════════════════════════════════════════════════════════
#  PANTALLA DE LOGIN ADMINISTRADOR
# ═══════════════════════════════════════════════════════════

def pantalla_login():
    """Pantalla de autenticación del administrador."""
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


# ═══════════════════════════════════════════════════════════
#  PANTALLA DE REGISTRO (PÚBLICA)
# ═══════════════════════════════════════════════════════════

def pantalla_registro():
    """Flujo completo de registro de trabajador."""

    # Inicializar estado del paso
    if "paso_registro" not in st.session_state:
        st.session_state["paso_registro"] = 1
    if "correo_verificado" not in st.session_state:
        st.session_state["correo_verificado"] = False
    if "codigo_enviado" not in st.session_state:
        st.session_state["codigo_enviado"] = False

    paso = st.session_state["paso_registro"]

    # ── Header ──
    st.markdown("""
    <div class="main-title">
        <h1>🚗 Registro de SOAT</h1>
        <p>Sistema de control vehicular — Todos los campos son obligatorios</p>
    </div>
    """, unsafe_allow_html=True)

    # Indicador de pasos
    pasos_html = '<div class="step-indicator">'
    for i in range(1, 5):
        cls = "completed" if i < paso else ("active" if i == paso else "")
        pasos_html += f'<div class="step-dot {cls}"></div>'
    pasos_html += '</div>'
    st.markdown(pasos_html, unsafe_allow_html=True)

    etiquetas_pasos = {
        1: "Paso 1 de 4 — Verificación de Correo",
        2: "Paso 2 de 4 — Datos Personales",
        3: "Paso 3 de 4 — Datos del Vehículo y SOAT",
        4: "Paso 4 de 4 — Confirmación y Envío"
    }
    st.markdown(f'<p style="text-align:center;color:#1a237e;font-weight:600;'
                f'font-size:14px;margin-bottom:24px;">{etiquetas_pasos[paso]}</p>',
                unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════
    #  PASO 1: VERIFICACIÓN DE CORREO (2FA)
    # ═══════════════════════════════════════════════════════
    if paso == 1:
        col1, col2, col3 = st.columns([1, 1.2, 1])

        with col2:
            st.markdown("### 📧 Verifica tu correo electrónico")
            st.markdown("Ingresa tu correo corporativo o personal. Te enviaremos un código de verificación.")

            correo_input = st.text_input(
                "Correo electrónico",
                placeholder="tucorreo@ejemplo.com",
                key="correo_paso1"
            )

            if not st.session_state.get("codigo_enviado"):
                if st.button("📩 Enviar código de verificación", use_container_width=True,
                             disabled=not correo_input):
                    if not validar_email(correo_input):
                        mostrar_alerta("danger", "Formato de correo no válido.")
                    elif db.existe_correo(correo_input):
                        mostrar_alerta("warning", "Este correo ya está registrado en el sistema.")
                    else:
                        resultado = tfa.solicitar_codigo(correo_input)
                        if resultado["exito"]:
                            st.session_state["codigo_enviado"] = True
                            st.session_state["correo_temporal"] = correo_input
                            st.success(resultado["mensaje"])
                            st.rerun()
                        else:
                            mostrar_alerta("danger", resultado["mensaje"])
            else:
                mostrar_alerta("info", f"Código enviado a {st.session_state.get('correo_temporal', '')}")

                codigo_input = st.text_input(
                    "Ingresa el código de 6 dígitos",
                    placeholder="123456",
                    max_chars=6,
                    key="codigo_2fa_input"
                )

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("✅ Verificar código", use_container_width=True,
                                 disabled=not codigo_input):
                        resultado = tfa.verificar_codigo(
                            st.session_state["correo_temporal"],
                            codigo_input
                        )
                        if resultado["valido"]:
                            st.session_state["correo_verificado"] = True
                            st.session_state["paso_registro"] = 2
                            st.session_state["correo_confirmado"] = st.session_state["correo_temporal"]
                            st.success(resultado["mensaje"])
                            st.rerun()
                        else:
                            mostrar_alerta("danger", resultado["mensaje"])

                with col_btn2:
                    if st.button("🔄 Reenviar código", use_container_width=True):
                        st.session_state["codigo_enviado"] = False
                        st.rerun()

    # ═══════════════════════════════════════════════════════
    #  PASO 2: DATOS PERSONALES
    # ═══════════════════════════════════════════════════════
    elif paso == 2:
        col1, col2, col3 = st.columns([1, 1.5, 1])

        with col2:
            st.markdown("### 👤 Datos Personales")
            mostrar_alerta("info", f"Correo verificado: **{st.session_state.get('correo_confirmado', '')}**")

            with st.form("form_datos_personales"):
                cedula = st.text_input(
                    "🪪 Número de Identificación (Cédula)",
                    placeholder="Ej: 1234567890",
                    key="cedula_input"
                )
                nombres = st.text_input(
                    "👤 Nombres Completos",
                    placeholder="Ej: Juan Pablo García López",
                    key="nombres_input"
                )
                cargo = st.text_input(
                    "💼 Cargo en la Empresa",
                    placeholder="Ej: Conductor, Mensajero, Supervisor...",
                    key="cargo_input"
                )
                fecha_nac = st.date_input(
                    "📅 Fecha de Nacimiento",
                    min_value=date(1950, 1, 1),
                    max_value=date.today(),
                    key="fecha_nac_input"
                )

                submitted = st.form_submit_button("Siguiente →", use_container_width=True)

                if submitted:
                    errores = []
                    if not cedula.strip():
                        errores.append("La identificación es obligatoria.")
                    elif not cedula.strip().isdigit() or len(cedula.strip()) < 6:
                        errores.append("La identificación debe ser numérica con al menos 6 dígitos.")
                    elif db.existe_identificacion(cedula.strip()):
                        errores.append("Esta identificación ya está registrada en el sistema.")

                    if not nombres.strip():
                        errores.append("Los nombres son obligatorios.")
                    elif len(nombres.strip()) < 5:
                        errores.append("Los nombres deben tener al menos 5 caracteres.")

                    if not cargo.strip():
                        errores.append("El cargo es obligatorio.")

                    if not fecha_nac:
                        errores.append("La fecha de nacimiento es obligatoria.")
                    elif (date.today() - fecha_nac).days < 6570:  # ~18 años
                        errores.append("Debes ser mayor de edad (18+ años).")

                    if errores:
                        for e in errores:
                            mostrar_alerta("danger", e)
                    else:
                        # Guardar en sesión
                        st.session_state["datos_personales"] = {
                            "identificacion": cedula.strip(),
                            "nombres": nombres.strip(),
                            "cargo": cargo.strip(),
                            "correo": st.session_state["correo_confirmado"],
                            "fecha_nacimiento": formatear_fecha_iso(fecha_nac)
                        }
                        st.session_state["paso_registro"] = 3
                        st.rerun()

            if st.button("← Atrás", use_container_width=True):
                st.session_state["paso_registro"] = 1
                st.session_state["codigo_enviado"] = False
                st.rerun()

    # ═══════════════════════════════════════════════════════
    #  PASO 3: VEHÍCULO Y SOAT
    # ═══════════════════════════════════════════════════════
    elif paso == 3:
        col1, col2, col3 = st.columns([1, 1.5, 1])

        with col2:
            st.markdown("### 🚗 Datos del Vehículo y SOAT")

            with st.form("form_vehiculo_soat"):
                tipo_vehiculo = st.selectbox(
                    "🚘 Tipo de Vehículo",
                    options=["Selecciona...", "Automovil", "Motocicleta"],
                    key="tipo_vehiculo_input"
                )
                placa = st.text_input(
                    "🔢 Placa del Vehículo",
                    placeholder="Ej: ABC123 o ABC12D",
                    key="placa_input"
                )
                archivo_soat = st.file_uploader(
                    "📄 Adjuntar SOAT (imagen)",
                    type=["jpg", "jpeg", "png", "bmp", "tiff", "webp"],
                    help="Sube una foto clara y nítida del SOAT vigente. "
                         "Formatos: JPG, PNG, BMP, TIFF, WEBP. "
                         "Resolución mínima: 400x300 px."
                )

                # Vista previa de la imagen
                if archivo_soat:
                    st.image(archivo_soat, caption="Vista previa del SOAT", width=400)

                submitted = st.form_submit_button("Siguiente →", use_container_width=True)

                if submitted:
                    errores = []
                    if tipo_vehiculo == "Selecciona...":
                        errores.append("Selecciona el tipo de vehículo.")
                    if not placa.strip():
                        errores.append("La placa es obligatoria.")
                    elif not validar_placa(placa, tipo_vehiculo):
                        if tipo_vehiculo == "Automovil":
                            errores.append("Formato de placa inválido para automóvil. Ejemplo: ABC123")
                        else:
                            errores.append("Formato de placa inválido para motocicleta. Ejemplo: ABC12D")
                    if archivo_soat is None:
                        errores.append("Debes adjuntar la imagen del SOAT.")

                    if errores:
                        for e in errores:
                            mostrar_alerta("danger", e)
                    else:
                        # Validar SOAT
                        with st.spinner("🔍 Analizando imagen del SOAT..."):
                            archivo_bytes = archivo_soat.read()
                            resultado_soat = soat_validator.validar_archivo(
                                archivo_bytes,
                                archivo_soat.name
                            )

                        st.session_state["resultado_soat"] = resultado_soat
                        st.session_state["archivo_soat_bytes"] = archivo_bytes
                        st.session_state["archivo_soat_nombre"] = archivo_soat.name

                        st.session_state["datos_vehiculo"] = {
                            "tipo_vehiculo": tipo_vehiculo,
                            "placa": placa.strip().upper()
                        }

                        st.session_state["paso_registro"] = 4
                        st.rerun()

            if st.button("← Atrás", use_container_width=True):
                st.session_state["paso_registro"] = 2
                st.rerun()

    # ═══════════════════════════════════════════════════════
    #  PASO 4: CONFIRMACIÓN Y ENVÍO
    # ═══════════════════════════════════════════════════════
    elif paso == 4:
        col1, col2, col3 = st.columns([1, 1.8, 1])

        with col2:
            st.markdown("### 📋 Resumen del Registro")
            st.markdown("Verifica que toda la información sea correcta antes de enviar.")

            dp = st.session_state.get("datos_personales", {})
            dv = st.session_state.get("datos_vehiculo", {})
            rs = st.session_state.get("resultado_soat", {})

            # Resumen de datos
            st.markdown("---")
            st.markdown("**👤 Datos Personales:**")
            st.markdown(f"- **Identificación:** {dp.get('identificacion', 'N/A')}")
            st.markdown(f"- **Nombres:** {dp.get('nombres', 'N/A')}")
            st.markdown(f"- **Cargo:** {dp.get('cargo', 'N/A')}")
            st.markdown(f"- **Correo:** {dp.get('correo', 'N/A')}")
            st.markdown(f"- **Fecha de Nacimiento:** {dp.get('fecha_nacimiento', 'N/A')}")

            st.markdown("---")
            st.markdown("**🚗 Datos del Vehículo:**")
            st.markdown(f"- **Tipo:** {dv.get('tipo_vehiculo', 'N/A')}")
            st.markdown(f"- **Placa:** {dv.get('placa', 'N/A')}")

            st.markdown("---")
            st.markdown("**📄 Estado del SOAT:**")

            # Mostrar resultado de validación
            if rs.get("calidad_ok"):
                mostrar_alerta("success", rs.get("calidad_mensaje", "Calidad OK"))
            else:
                mostrar_alerta("danger", rs.get("calidad_mensaje", "Imagen no válida"))

            estado = rs.get("estado", "No legible")
            colores = {
                "Vigente": "success",
                "Por vencer": "warning",
                "Vencido": "danger",
                "No legible": "info"
            }
            mostrar_alerta(colores.get(estado, "info"), rs.get("mensaje_general", estado))

            st.markdown("---")

            # Botones de acción
            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                if st.button("← Corregir", use_container_width=True):
                    st.session_state["paso_registro"] = 3
                    st.rerun()

            with col_btn2:
                if st.button("✅ Enviar Registro", use_container_width=True,
                             type="primary"):
                    with st.spinner("📤 Enviando registro... Por favor espera."):
                        # Subir archivo a Supabase Storage
                        try:
                            soat_url = db.subir_archivo_soat(
                                st.session_state["archivo_soat_bytes"],
                                st.session_state["archivo_soat_nombre"]
                            )
                        except Exception as e:
                            mostrar_alerta("danger", f"Error al subir archivo: {e}")
                            st.stop()

                        # Preparar fecha de vencimiento
                        fecha_venc_iso = None
                        if rs.get("fecha_vencimiento"):
                            fecha_venc_iso = formatear_fecha_iso(rs["fecha_vencimiento"])

                        # Armar datos para insertar
                        datos_completos = {
                            "identificacion": dp["identificacion"],
                            "nombres": dp["nombres"],
                            "cargo": dp["cargo"],
                            "correo": dp["correo"],
                            "fecha_nacimiento": dp["fecha_nacimiento"],
                            "tipo_vehiculo": dv["tipo_vehiculo"],
                            "placa": dv["placa"],
                            "soat_url": soat_url,
                            "soat_nombre_archivo": st.session_state["archivo_soat_nombre"],
                            "soat_vigencia": fecha_venc_iso,
                            "soat_estado": rs.get("estado", "No legible"),
                            "soat_calidad_imagen": rs.get("calidad_score", 0),
                            "calidad_imagen_ok": rs.get("calidad_ok", False)
                        }

                        # Insertar en BD
                        resultado_bd = db.registrar_trabajador(datos_completos)

                        if resultado_bd["exito"]:
                            # Enviar correo de confirmación con adjunto
                            email_enviado = email_svc.enviar_confirmacion_registro(
                                destinatario=dp["correo"],
                                datos=datos_completos,
                                adjunto_bytes=st.session_state["archivo_soat_bytes"],
                                adjunto_nombre=st.session_state["archivo_soat_nombre"]
                            )

                            # Si la imagen no es legible, enviar notificación adicional
                            if not rs.get("calidad_ok") or rs.get("estado") == "No legible":
                                email_svc.enviar_notificacion_imagen(
                                    destinatario=dp["correo"],
                                    motivo=rs.get("calidad_mensaje", "No se pudo leer el SOAT.")
                                )

                            # Limpiar sesión y mostrar éxito
                            for key in list(st.session_state.keys()):
                                del st.session_state[key]

                            st.session_state["registro_exitoso"] = True
                            st.session_state["email_enviado"] = email_enviado
                            st.rerun()
                        else:
                            mostrar_alerta("danger", resultado_bd["mensaje"])

    # ═══════════════════════════════════════════════════════
    #  REGISTRO EXITOSO
    # ═══════════════════════════════════════════════════════
    if st.session_state.get("registro_exitoso"):
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("""
            <div style="text-align:center; padding:48px 24px;">
                <div style="font-size:64px; margin-bottom:16px;">🎉</div>
                <h2 style="color:#2e7d32; margin-bottom:8px;">¡Registro Exitoso!</h2>
                <p style="color:#555; font-size:15px; line-height:1.6;">
                    Tu información ha sido almacenada correctamente.
                </p>
            """, unsafe_allow_html=True)

            if st.session_state.get("email_enviado"):
                mostrar_alerta("success",
                    "Se envió un correo de confirmación con tu comprobante y el SOAT adjunto.")
            else:
                mostrar_alerta("warning",
                    "El registro se guardó, pero hubo un error al enviar el correo de confirmación.")

            if st.button("📝 Registrar otro trabajador", use_container_width=True,
                         type="primary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()


# ═══════════════════════════════════════════════════════════
#  PANTALLA DE ADMINISTRADOR
# ═══════════════════════════════════════════════════════════

def pantalla_admin():
    """Panel de administración con indicadores y gestión de registros."""

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

    # Cargar indicadores
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
        total = max(ind["total"], 1)
        st.markdown(f"**✅ Vigentes:** {ind['vigentes']} ({ind['pct_vigentes']}%)")
        st.progress(ind["pct_vigentes"] / 100, text=None)
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
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go

        col_graf1, col_graf2 = st.columns(2)

        # Gráfico de tipo de vehículo (Pie)
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
                    height=300,
                    showlegend=True,
                    legend=dict(font=dict(size=12))
                )
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Sin datos aún.")

        # Gráfico por cargo (Barras horizontales)
        with col_graf2:
            st.markdown("#### 💼 Distribución por Cargo")
            if ind["por_cargo"]:
                df_cargo = pd.DataFrame([
                    {"Cargo": k, "Cantidad": v}
                    for k, v in ind["por_cargo"].items()
                ]).sort_values("Cantidad", ascending=True)

                fig_bar = px.bar(
                    df_cargo, x="Cantidad", y="Cargo",
                    orientation="h",
                    color="Cantidad",
                    color_continuous_scale="Blues"
                )
                fig_bar.update_layout(
                    margin=dict(t=10, b=10, l=120, r=10),
                    height=300,
                    showlegend=False,
                    yaxis=dict(tickfont=dict(size=11))
                )
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Sin datos aún.")

        # Gráfico de registros por mes
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
                text=df_mes["Registros"],
                textposition="top center",
                line=dict(color="#1a237e", width=3),
                marker=dict(size=10, color="#1a237e"),
                fill="tozeroy",
                fillcolor="rgba(26,35,126,0.08)"
            ))
            fig_line.update_layout(
                margin=dict(t=20, b=40, l=40, r=20),
                height=300,
                xaxis=dict(tickfont=dict(size=11)),
                yaxis=dict(tickfont=dict(size=11))
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Sin datos de meses aún.")

    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

    # ── Alertas ──
    if ind["alertas"]:
        st.markdown("### 🔔 Alertas Activas")
        with st.expander(f"Ver {len(ind['alertas'])} alerta(s)", expanded=True):
            for alerta in ind["alertas"]:
                mostrar_alerta(alerta["tipo"], alerta["mensaje"])
        st.markdown("---")

    # ── Tabla de Registros ──
    st.markdown("### 📋 Todos los Registros")

    todos = db.obtener_todos_trabajadores()

    if todos:
        import pandas as pd

        df = pd.DataFrame(todos)

        # Formatear columnas para mostrar
        columnas_mostrar = [
            "identificacion", "nombres", "cargo", "correo",
            "tipo_vehiculo", "placa", "soat_estado",
            "soat_vigencia", "calidad_imagen_ok", "fecha_registro"
        ]

        # Solo mostrar columnas que existan
        columnas_existentes = [c for c in columnas_mostrar if c in df.columns]
        df_mostrar = df[columnas_existentes].copy()

        # Renombrar columnas
        renombres = {
            "identificacion": "Identificación",
            "nombres": "Nombres",
            "cargo": "Cargo",
            "correo": "Correo",
            "tipo_vehiculo": "Tipo Vehículo",
            "placa": "Placa",
            "soat_estado": "Estado SOAT",
            "soat_vigencia": "Vencimiento SOAT",
            "calidad_imagen_ok": "Imagen OK",
            "fecha_registro": "Fecha Registro"
        }
        df_mostrar = df_mostrar.rename(columns=renombres)

        # Formatear fechas
        for col_fecha in ["Vencimiento SOAT", "Fecha Registro"]:
            if col_fecha in df_mostrar.columns:
                df_mostrar[col_fecha] = df_mostrar[col_fecha].apply(
                    lambda x: str(x)[:10] if pd.notna(x) else "N/A"
                )

        # Formatear booleano
        if "Imagen OK" in df_mostrar.columns:
            df_mostrar["Imagen OK"] = df_mostrar["Imagen OK"].apply(
                lambda x: "✅ Sí" if x else "❌ No"
            )

        # Color de estado
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
                use_container_width=True,
                height=400,
                hide_index=True
            )
        else:
            st.dataframe(df_mostrar, use_container_width=True, height=400, hide_index=True)

        # Opción de eliminar registros
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
    else:
        st.info("📭 No hay registros aún. Los registros aparecerán cuando los trabajadores se registren.")


# ═══════════════════════════════════════════════════════════
#  PANTALLA DE SELECCIÓN (LANDING)
# ═══════════════════════════════════════════════════════════

def pantalla_seleccion():
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
        st.markdown("")  # Espaciador

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
        st.markdown("")  # Espaciador


# ═══════════════════════════════════════════════════════════
#  FLUJO PRINCIPAL
# ═══════════════════════════════════════════════════════════

def main():
    """Punto de entrada de la aplicación."""

    # Verificar configuración
    if not Config.validar():
        st.error("""
        ## ⚠️ Configuración Incompleta

        Falta configurar las variables de entorno en el archivo `.env`:

        ```
        SUPABASE_URL=tu_url
        SUPABASE_KEY=tu_key
        EMAIL_USER=tu_correo
        EMAIL_PASSWORD=tu_password
        ```

        Revisa el archivo `config.py` para más detalles.
        """)
        st.stop()

    # Enrutamiento según estado de sesión
    if st.session_state.get("admin_autenticado"):
        pantalla_admin()
    elif st.session_state.get("modo") == "admin":
        pantalla_login()
    elif st.session_state.get("modo") == "registro":
        pantalla_registro()
    else:
        pantalla_seleccion()


# ═══════════════════════════════════════════════════════════
#  EJECUTAR
# ═══════════════════════════════════════════════════════════
if __name__ == "__main__":
    main()
