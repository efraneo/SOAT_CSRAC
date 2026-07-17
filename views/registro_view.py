"""
views/registro_view.py
Flujo completo de registro de trabajador (4 pasos + éxito).
"""
import streamlit as st
from datetime import date

from utils import (
    db, email_svc, soat_validator, tfa,
    validar_email, validar_placa, formatear_fecha_iso, mostrar_alerta
)


def mostrar():
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

    # ═══════════════════════════════════════════════════
    if paso == 1:
        _paso_1_verificacion_correo()
    elif paso == 2:
        _paso_2_datos_personales()
    elif paso == 3:
        _paso_3_vehiculo_soat()
    elif paso == 4:
        _paso_4_confirmacion_envio()

    # ═══════════════════════════════════════════════════
    if st.session_state.get("registro_exitoso"):
        _pantalla_exito()


# ───────────────────────────────────────────────────────
#  PASO 1: VERIFICACIÓN DE CORREO (2FA)
# ───────────────────────────────────────────────────────
def _paso_1_verificacion_correo():
    col1, col2, col3 = st.columns([1, 1.2, 1])

    with col2:
        st.markdown("### 📧 Verifica tu correo electrónico")
        st.markdown("Ingresa tu correo. Te enviaremos un código de verificación.")

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


# ───────────────────────────────────────────────────────
#  PASO 2: DATOS PERSONALES
# ───────────────────────────────────────────────────────
def _paso_2_datos_personales():
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
                elif (date.today() - fecha_nac).days < 6570:
                    errores.append("Debes ser mayor de edad (18+ años).")

                if errores:
                    for e in errores:
                        mostrar_alerta("danger", e)
                else:
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


# ───────────────────────────────────────────────────────
#  PASO 3: VEHÍCULO Y SOAT
# ───────────────────────────────────────────────────────
def _paso_3_vehiculo_soat():
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


# ───────────────────────────────────────────────────────
#  PASO 4: CONFIRMACIÓN Y ENVÍO
# ───────────────────────────────────────────────────────
def _paso_4_confirmacion_envio():
    col1, col2, col3 = st.columns([1, 1.8, 1])

    with col2:
        st.markdown("### 📋 Resumen del Registro")
        st.markdown("Verifica que toda la información sea correcta antes de enviar.")

        dp = st.session_state.get("datos_personales", {})
        dv = st.session_state.get("datos_vehiculo", {})
        rs = st.session_state.get("resultado_soat", {})

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

        if rs.get("calidad_ok"):
            mostrar_alerta("success", rs.get("calidad_mensaje", "Calidad OK"))
        else:
            mostrar_alerta("danger", rs.get("calidad_mensaje", "Imagen no válida"))

        estado = rs.get("estado", "No legible")
        colores = {
            "Vigente": "success", "Por vencer": "warning",
            "Vencido": "danger", "No legible": "info"
        }
        mostrar_alerta(colores.get(estado, "info"), rs.get("mensaje_general", estado))

        st.markdown("---")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("← Corregir", use_container_width=True):
                st.session_state["paso_registro"] = 3
                st.rerun()

        with col_btn2:
            if st.button("✅ Enviar Registro", use_container_width=True, type="primary"):
                with st.spinner("📤 Enviando registro... Por favor espera."):
                    try:
                        soat_url = db.subir_archivo_soat(
                            st.session_state["archivo_soat_bytes"],
                            st.session_state["archivo_soat_nombre"]
                        )
                    except Exception as e:
                        mostrar_alerta("danger", f"Error al subir archivo: {e}")
                        st.stop()

                    fecha_venc_iso = None
                    if rs.get("fecha_vencimiento"):
                        fecha_venc_iso = formatear_fecha_iso(rs["fecha_vencimiento"])

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

                    resultado_bd = db.registrar_trabajador(datos_completos)

                    if resultado_bd["exito"]:
                        email_enviado = email_svc.enviar_confirmacion_registro(
                            destinatario=dp["correo"],
                            datos=datos_completos,
                            adjunto_bytes=st.session_state["archivo_soat_bytes"],
                            adjunto_nombre=st.session_state["archivo_soat_nombre"]
                        )

                        if not rs.get("calidad_ok") or rs.get("estado") == "No legible":
                            email_svc.enviar_notificacion_imagen(
                                destinatario=dp["correo"],
                                motivo=rs.get("calidad_mensaje", "No se pudo leer el SOAT.")
                            )

                        for key in list(st.session_state.keys()):
                            del st.session_state[key]

                        st.session_state["registro_exitoso"] = True
                        st.session_state["email_enviado"] = email_enviado
                        st.rerun()
                    else:
                        mostrar_alerta("danger", resultado_bd["mensaje"])


# ───────────────────────────────────────────────────────
#  REGISTRO EXITOSO
# ───────────────────────────────────────────────────────
def _pantalla_exito():
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

        if st.button("📝 Registrar otro trabajador", use_container_width=True, type="primary"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
