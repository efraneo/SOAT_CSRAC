"""
two_factor.py
Generación y gestión de códigos de verificación en dos factores (2FA).
"""
import random
import string
from datetime import datetime, timezone, timedelta
from database import Database
from email_service import EmailService
from config import Config


class TwoFactorAuth:
    """Gestión de autenticación en dos factores."""

    def __init__(self):
        self.db = Database()
        self.email = EmailService()
        self.expiry_seconds = Config.TWO_FACTOR_EXPIRY_SECONDS

    def generar_codigo(self, longitud: int = 6) -> str:
        """Genera un código numérico aleatorio."""
        return "".join(random.choices(string.digits, k=longitud))

    def solicitar_codigo(self, correo: str) -> dict:
        """
        Genera un código 2FA, lo guarda en la BD y lo envía por correo.
        Retorna: {"exito": bool, "mensaje": str}
        """
        # Limpiar códigos antiguos
        self.db.limpiar_codigos_antiguos()

        # Verificar si ya se envió un código recientemente (anti-spam: 60 seg)
        try:
            hace_60_seg = (datetime.now(timezone.utc) - timedelta(seconds=60)).isoformat()
            from supabase import create_client
            client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
            reciente = (
                client.table("codigos_2fa")
                .select("id")
                .eq("correo", correo)
                .gte("creado_en", hace_60_seg)
                .execute()
            )
            if reciente.data:
                return {
                    "exito": False,
                    "mensaje": "Espera al menos 1 minuto antes de solicitar otro código."
                }
        except Exception:
            pass

        # Generar código
        codigo = self.generar_codigo(6)
        expiracion = datetime.now(timezone.utc) + timedelta(seconds=self.expiry_seconds)

        # Guardar en BD
        guardado = self.db.guardar_codigo_2fa(correo, codigo, expiracion)
        if not guardado:
            return {
                "exito": False,
                "mensaje": "Error al generar el código. Intenta de nuevo."
            }

        # Enviar por correo
        enviado = self.email.enviar_codigo_2fa(correo, codigo)
        if not enviado:
            return {
                "exito": False,
                "mensaje": "Error al enviar el código por correo. Verifica la configuración SMTP."
            }

        return {
            "exito": True,
            "mensaje": f"Código enviado a {correo}. Revisa tu bandeja de entrada (y spam)."
        }

    def verificar_codigo(self, correo: str, codigo: str) -> dict:
        """Verifica el código 2FA ingresado."""
        return self.db.verificar_codigo_2fa(correo, codigo.strip())
