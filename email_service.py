"""
email_service.py
Servicio de envío de correos electrónicos.
- Envío de código 2FA
- Envío de confirmación de registro al trabajador
- Envío de notificación de imagen no legible
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.utils import formataddr, formatdate
from datetime import datetime
from config import Config


class EmailService:
    """Servicio de correo electrónico."""

    def __init__(self):
        self.host = Config.EMAIL_HOST
        self.port = Config.EMAIL_PORT
        self.user = Config.EMAIL_USER
        self.password = Config.EMAIL_PASSWORD
        self.from_name = Config.EMAIL_FROM_NAME

    def _conectar(self) -> smtplib.SMTP:
        """Establece conexión SMTP."""
        server = smtplib.SMTP(self.host, self.port, timeout=30)
        server.starttls()
        server.login(self.user, self.password)
        return server

    def _enviar(self, destinatario: str, asunto: str, html_body: str,
                adjunto_bytes: bytes = None, adjunto_nombre: str = None) -> bool:
        """Envía un correo con soporte HTML y opcionalmente un archivo adjunto."""
        try:
            msg = MIMEMultipart("related")
            msg["From"] = formataddr((self.from_name, self.user))
            msg["To"] = destinatario
            msg["Subject"] = asunto
            msg["Date"] = formatdate(localtime=True)

            # Versión alternativa (texto plano + HTML)
            msg_alternativo = MIMEMultipart("alternative")
            texto_plano = self._html_a_texto(html_body)
            msg_alternativo.attach(MIMEText(texto_plano, "plain", "utf-8"))
            msg_alternativo.attach(MIMEText(html_body, "html", "utf-8"))
            msg.attach(msg_alternativo)

            # Adjunto
            if adjunto_bytes and adjunto_nombre:
                parte_adjunto = MIMEApplication(adjunto_bytes, Name=adjunto_nombre)
                parte_adjunto["Content-Disposition"] = (
                    f'attachment; filename="{adjunto_nombre}"'
                )
                msg.attach(parte_adjunto)

            # Enviar
            server = self._conectar()
            server.sendmail(self.user, [destinatario], msg.as_string())
            server.quit()
            return True

        except smtplib.SMTPAuthenticationError:
            print("❌ Error de autenticación SMTP. Verifica usuario y contraseña.")
            return False
        except Exception as e:
            print(f"❌ Error enviando correo: {e}")
            return False

    @staticmethod
    def _html_a_texto(html: str) -> str:
        """Convierte HTML básico a texto plano."""
        import re
        texto = re.sub(r'<br\s*/?>', '\n', html)
        texto = re.sub(r'<[^>]+>', '', texto)
        texto = texto.replace("&nbsp;", " ").replace("&amp;", "&")
        texto = texto.replace("&lt;", "<").replace("&gt;", ">")
        return texto.strip()

    # ═══════════════════════════════════════════════════
    #  PLANTILLAS DE CORREO
    # ═══════════════════════════════════════════════════

    def enviar_codigo_2fa(self, destinatario: str, codigo: str) -> bool:
        """Envía el código de verificación 2FA."""
        asunto = "🔐 Tu código de verificación - Registro SOAT"

        html = f"""
        <div style="max-width:600px; margin:0 auto; font-family:'Segoe UI',Arial,sans-serif;
                     background:#f8f9fa; border-radius:12px; overflow:hidden;
                     box-shadow:0 4px 24px rgba(0,0,0,0.08);">
            <div style="background:linear-gradient(135deg,#1a237e,#283593); padding:32px;
                        text-align:center;">
                <h1 style="color:#fff; margin:0; font-size:24px; font-weight:700;">
                    🔐 Verificación de Correo
                </h1>
                <p style="color:rgba(255,255,255,0.8); margin:8px 0 0; font-size:14px;">
                    Sistema de Registro SOAT
                </p>
            </div>
            <div style="padding:32px; background:#fff;">
                <p style="color:#333; font-size:16px; line-height:1.6;">
                    Hola, tienes un código de verificación para continuar con tu registro:
                </p>
                <div style="background:#f0f4ff; border:2px dashed #1a237e; border-radius:12px;
                            padding:24px; text-align:center; margin:24px 0;">
                    <span style="font-size:42px; font-weight:800; color:#1a237e;
                                 letter-spacing:8px; font-family:'Courier New',monospace;">
                        {codigo}
                    </span>
                </div>
                <p style="color:#666; font-size:13px; text-align:center;">
                    ⏱️ Este código expira en <strong>5 minutos</strong>.<br>
                    Si no solicitaste este código, ignora este mensaje.
                </p>
            </div>
            <div style="background:#f8f9fa; padding:16px 32px; text-align:center;
                        border-top:1px solid #eee;">
                <p style="color:#999; font-size:11px; margin:0;">
                    Este es un mensaje automático. No respondas a este correo.
                </p>
            </div>
        </div>
        """
        return self._enviar(destinatario, asunto, html)

    def enviar_confirmacion_registro(self, destinatario: str, datos: dict,
                                     adjunto_bytes: bytes = None,
                                     adjunto_nombre: str = None) -> bool:
        """Envía correo de confirmación con los datos del registro."""
        asunto = "✅ Registro Exitoso - Comprobante SOAT"

        # Determinar color del estado
        colores_estado = {
            "Vigente": "#2e7d32",
            "Por vencer": "#f57f17",
            "Vencido": "#c62828",
            "No legible": "#6a1b9a"
        }
        color = colores_estado.get(datos.get("soat_estado", ""), "#333")

        fecha_venc_str = "No detectada"
        if datos.get("soat_vigencia"):
            try:
                fv = datos["soat_vigencia"]
                if isinstance(fv, str):
                    fv = datetime.fromisoformat(fv.replace("Z", "+00:00")).date()
                fecha_venc_str = fv.strftime("%d/%m/%Y")
            except Exception:
                fecha_venc_str = str(datos["soat_vigencia"])

        fecha_nac_str = datos.get("fecha_nacimiento", "No registrada")
        if isinstance(fecha_nac_str, str) and "T" in fecha_nac_str:
            try:
                fn = datetime.fromisoformat(fecha_nac_str.replace("Z", "+00:00")).date()
                fecha_nac_str = fn.strftime("%d/%m/%Y")
            except Exception:
                pass

        fecha_reg_str = "N/A"
        if datos.get("fecha_registro"):
            try:
                fr = datetime.fromisoformat(
                    datos["fecha_registro"].replace("Z", "+00:00")
                )
                fecha_reg_str = fr.strftime("%d/%m/%Y %H:%M")
            except Exception:
                fecha_reg_str = str(datos["fecha_registro"])

        html = f"""
        <div style="max-width:650px; margin:0 auto; font-family:'Segoe UI',Arial,sans-serif;
                     background:#f8f9fa; border-radius:12px; overflow:hidden;
                     box-shadow:0 4px 24px rgba(0,0,0,0.08);">
            <!-- Header -->
            <div style="background:linear-gradient(135deg,#1b5e20,#2e7d32); padding:36px;
                        text-align:center;">
                <h1 style="color:#fff; margin:0; font-size:26px; font-weight:700;">
                    ✅ Registro Completado
                </h1>
                <p style="color:rgba(255,255,255,0.85); margin:8px 0 0; font-size:15px;">
                    Comprobante de Registro de SOAT
                </p>
            </div>

            <!-- Contenido -->
            <div style="padding:32px; background:#fff;">
                <p style="color:#555; font-size:15px; margin:0 0 24px;">
                    A continuación encontrarás el resumen de tu registro:
                </p>

                <!-- Tabla de datos -->
                <table style="width:100%; border-collapse:collapse; font-size:14px;">
                    <tr style="background:#f0f7f0;">
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0; width:40%;">
                            Identificación
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {datos.get('identificacion', 'N/A')}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Nombres Completos
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {datos.get('nombres', 'N/A')}
                        </td>
                    </tr>
                    <tr style="background:#f0f7f0;">
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Cargo
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {datos.get('cargo', 'N/A')}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Correo Electrónico
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {datos.get('correo', 'N/A')}
                        </td>
                    </tr>
                    <tr style="background:#f0f7f0;">
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Fecha de Nacimiento
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {fecha_nac_str}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Tipo de Vehículo
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {datos.get('tipo_vehiculo', 'N/A')}
                        </td>
                    </tr>
                    <tr style="background:#f0f7f0;">
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Placa
                        </td>
                        <td style="padding:12px 16px; color:#333; font-weight:700;
                                   border-bottom:1px solid #e0e0e0; font-size:16px;">
                            {datos.get('placa', 'N/A').upper()}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Estado del SOAT
                        </td>
                        <td style="padding:12px 16px; font-weight:700; color:{color};
                                   border-bottom:1px solid #e0e0e0; font-size:15px;">
                            {datos.get('soat_estado', 'N/A')}
                        </td>
                    </tr>
                    <tr style="background:#f0f7f0;">
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Fecha Vencimiento SOAT
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {fecha_venc_str}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:12px 16px; font-weight:700; color:#1b5e20;
                                   border-bottom:1px solid #e0e0e0;">
                            Fecha de Registro
                        </td>
                        <td style="padding:12px 16px; color:#333;
                                   border-bottom:1px solid #e0e0e0;">
                            {fecha_reg_str}
                        </td>
                    </tr>
                </table>

                <div style="margin-top:24px; padding:16px; background:#fff8e1;
                            border-left:4px solid #f57f17; border-radius:4px;">
                    <p style="margin:0; color:#e65100; font-size:13px;">
                        📌 <strong>Nota:</strong> El soporte del SOAT se adjunta a este
                        correo. Guárdalo como comprobante.
                    </p>
                </div>
            </div>

            <!-- Footer -->
            <div style="background:#f8f9fa; padding:20px 32px; text-align:center;
                        border-top:1px solid #eee;">
                <p style="color:#999; font-size:11px; margin:0 0 4px;">
                    Mensaje generado automáticamente por el Sistema de Registro SOAT
                </p>
                <p style="color:#bbb; font-size:10px; margin:0;">
                    {datetime.now().strftime("%d/%m/%Y %H:%M")} | No responder este correo
                </p>
            </div>
        </div>
        """
        return self._enviar(destinatario, asunto, html,
                            adjunto_bytes, adjunto_nombre)

    def enviar_notificacion_imagen(self, destinatario: str, motivo: str) -> bool:
        """Notifica al trabajador que su imagen del SOAT no es legible."""
        asunto = "📷 Acción Requerida - SOAT No Legible"

        html = f"""
        <div style="max-width:600px; margin:0 auto; font-family:'Segoe UI',Arial,sans-serif;
                     background:#f8f9fa; border-radius:12px; overflow:hidden;
                     box-shadow:0 4px 24px rgba(0,0,0,0.08);">
            <div style="background:linear-gradient(135deg,#6a1b9a,#8e24aa); padding:32px;
                        text-align:center;">
                <h1 style="color:#fff; margin:0; font-size:24px; font-weight:700;">
                    📷 Acción Requerida
                </h1>
                <p style="color:rgba(255,255,255,0.85); margin:8px 0 0; font-size:14px;">
                    Imagen del SOAT no procesable
                </p>
            </div>
            <div style="padding:32px; background:#fff;">
                <p style="color:#333; font-size:15px; line-height:1.6;">
                    Hola, la imagen del SOAT que adjuntaste no pudo ser procesada correctamente
                    por el siguiente motivo:
                </p>
                <div style="background:#fce4ec; border-left:4px solid #c62828;
                            padding:16px 20px; margin:20px 0; border-radius:4px;">
                    <p style="margin:0; color:#b71c1c; font-size:14px;">
                        <strong>Motivo:</strong> {motivo}
                    </p>
                </div>
                <p style="color:#333; font-size:14px; line-height:1.6;">
                    Por favor, vuelve a ingresar al sistema y registra nuevamente tu SOAT
                    con una imagen que cumpla con los siguientes requisitos:
                </p>
                <ul style="color:#555; font-size:13px; line-height:2; padding-left:20px;">
                    <li>📸 Foto nítida, sin desenfoque ni pixelación</li>
                    <li>💡 Buena iluminación, sin sombras</li>
                    <li>📐 Documento completo visible (no cortado)</li>
                    <li>📝 La fecha de vencimiento debe ser legible</li>
                    <li>📁 Formato: JPG, PNG, BMP o WEBP</li>
                    <li>📐 Resolución mínima: 400x300 píxeles</li>
                </ul>
            </div>
            <div style="background:#f8f9fa; padding:16px 32px; text-align:center;
                        border-top:1px solid #eee;">
                <p style="color:#999; font-size:11px; margin:0;">
                    Mensaje automático del Sistema de Registro SOAT. No responder.
                </p>
            </div>
        </div>
        """
        return self._enviar(destinatario, asunto, html)
