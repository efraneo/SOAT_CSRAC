"""
database.py
Operaciones de base de datos con Supabase.
Maneja trabajadores, códigos 2FA y almacenamiento de archivos.
"""
import uuid
from datetime import datetime, timezone
from supabase import create_client, Client
from config import Config


class Database:
    """Clase para interactuar con Supabase."""

    def __init__(self):
        self.client: Client = create_client(
            Config.SUPABASE_URL,
            Config.SUPABASE_KEY
        )

    # ═══════════════════════════════════════════════════
    #  OPERACIONES 2FA
    # ═══════════════════════════════════════════════════

    def guardar_codigo_2fa(self, correo: str, codigo: str, expiracion: datetime) -> bool:
        """Guarda un código 2FA en la base de datos."""
        try:
            self.client.table("codigos_2fa").insert({
                "correo": correo,
                "codigo": codigo,
                "expiracion": expiracion.isoformat(),
                "verificado": False
            }).execute()
            return True
        except Exception as e:
            print(f"Error guardando código 2FA: {e}")
            return False

    def verificar_codigo_2fa(self, correo: str, codigo_ingresado: str) -> dict:
        """
        Verifica si el código 2FA es válido.
        Retorna: {"valido": bool, "mensaje": str}
        """
        try:
            ahora = datetime.now(timezone.utc).isoformat()
            response = (
                self.client.table("codigos_2fa")
                .select("*")
                .eq("correo", correo)
                .eq("codigo", codigo_ingresado)
                .eq("verificado", False)
                .gte("expiracion", ahora)
                .order("creado_en", desc=True)
                .limit(1)
                .execute()
            )

            if response.data:
                registro_id = response.data[0]["id"]
                self.client.table("codigos_2fa").update(
                    {"verificado": True}
                ).eq("id", registro_id).execute()
                return {"valido": True, "mensaje": "Código verificado correctamente."}

            # Verificar si expiró
            response_exp = (
                self.client.table("codigos_2fa")
                .select("*")
                .eq("correo", correo)
                .eq("codigo", codigo_ingresado)
                .eq("verificado", False)
                .lt("expiracion", ahora)
                .order("creado_en", desc=True)
                .limit(1)
                .execute()
            )

            if response_exp.data:
                return {"valido": False, "mensaje": "El código ha expirado. Solicita uno nuevo."}

            return {"valido": False, "mensaje": "Código incorrecto."}

        except Exception as e:
            print(f"Error verificando 2FA: {e}")
            return {"valido": False, "mensaje": f"Error de verificación: {e}"}

    def limpiar_codigos_antiguos(self):
        """Elimina códigos 2FA expirados (mantenimiento)."""
        try:
            ahora = datetime.now(timezone.utc).isoformat()
            self.client.table("codigos_2fa").delete().lt("expiracion", ahora).execute()
        except Exception:
            pass

    # ═══════════════════════════════════════════════════
    #  OPERACIONES TRABAJADORES
    # ═══════════════════════════════════════════════════

    def existe_identificacion(self, identificacion: str) -> bool:
        """Verifica si ya existe un trabajador con esa identificación."""
        try:
            response = (
                self.client.table("trabajadores")
                .select("id")
                .eq("identificacion", identificacion)
                .execute()
            )
            return len(response.data) > 0
        except Exception:
            return False

    def existe_correo(self, correo: str) -> bool:
        """Verifica si ya existe un trabajador con ese correo."""
        try:
            response = (
                self.client.table("trabajadores")
                .select("id")
                .eq("correo", correo)
                .execute()
            )
            return len(response.data) > 0
        except Exception:
            return False

    def subir_archivo_soat(self, archivo_bytes: bytes, nombre_archivo: str) -> str:
        """
        Sube el archivo del SOAT a Supabase Storage.
        Retorna la URL pública del archivo.
        """
        try:
            # Generar nombre único para evitar colisiones
            extension = nombre_archivo.rsplit(".", 1)[-1] if "." in nombre_archivo else "jpg"
            nombre_unico = f"{uuid.uuid4().hex}_{nombre_archivo}"

            # CORRECCIÓN: Usar 'path' y 'file' (nueva sintaxis de supabase-py v2)
            self.client.storage.from_(Config.SOAT_STORAGE_BUCKET).upload(
                path=nombre_unico,
                file=archivo_bytes,
                file_options={"content-type": "application/octet-stream"}
            )

            # Obtener URL pública
            url = self.client.storage.from_(Config.SOAT_STORAGE_BUCKET).get_public_url(nombre_unico)
            return url

        except Exception as e:
            print(f"Error subiendo archivo SOAT: {e}")
            raise Exception(f"No se pudo subir el archivo: {e}")

    def registrar_trabajador(self, datos: dict) -> dict:
        """
        Registra un nuevo trabajador en la base de datos.
        Retorna el registro insertado o un error.
        """
        try:
            response = self.client.table("trabajadores").insert(datos).execute()
            if response.data:
                return {"exito": True, "datos": response.data[0]}
            return {"exito": False, "mensaje": "No se recibieron datos del servidor."}
        except Exception as e:
            error_msg = str(e)
            if "duplicate" in error_msg.lower() or "unique" in error_msg.lower():
                return {"exito": False, "mensaje": "Ya existe un registro con esa identificación o correo."}
            return {"exito": False, "mensaje": f"Error al registrar: {error_msg}"}

    def obtener_todos_trabajadores(self) -> list:
        """Obtiene todos los trabajadores ordenados por fecha de registro."""
        try:
            response = (
                self.client.table("trabajadores")
                .select("*")
                .order("fecha_registro", desc=True)
                .execute()
            )
            return response.data if response.data else []
        except Exception as e:
            print(f"Error obteniendo trabajadores: {e}")
            return []

    def obtener_indicadores(self) -> dict:
        """Genera todos los indicadores/KPIs para el panel administrativo."""
        try:
            todos = self.obtener_todos_trabajadores()

            if not todos:
                return {
                    "total": 0, "vigentes": 0, "vencidos": 0,
                    "por_vencer": 0, "no_legibles": 0, "pendientes": 0,
                    "pct_vigentes": 0, "pct_vencidos": 0,
                    "pct_por_vencer": 0, "pct_no_legibles": 0,
                    "por_tipo_vehiculo": {}, "por_cargo": {},
                    "por_mes": {}, "ultimos_registros": [], "alertas": []
                }

            total = len(todos)
            vigentes = [t for t in todos if t["soat_estado"] == "Vigente"]
            vencidos = [t for t in todos if t["soat_estado"] == "Vencido"]
            por_vencer = [t for t in todos if t["soat_estado"] == "Por vencer"]
            no_legibles = [t for t in todos if t["soat_estado"] == "No legible"]
            pendientes = [t for t in todos if t["soat_estado"] == "Pendiente"]

            pct_vigentes = round(len(vigentes) / total * 100, 1) if total else 0
            pct_vencidos = round(len(vencidos) / total * 100, 1) if total else 0
            pct_por_vencer = round(len(por_vencer) / total * 100, 1) if total else 0
            pct_no_legibles = round(len(no_legibles) / total * 100, 1) if total else 0

            por_tipo = {}
            for t in todos:
                tv = t.get("tipo_vehiculo", "Sin dato")
                por_tipo[tv] = por_tipo.get(tv, 0) + 1

            por_cargo = {}
            for t in todos:
                cargo = t.get("cargo", "Sin dato")
                por_cargo[cargo] = por_cargo.get(cargo, 0) + 1

            por_mes = {}
            for t in todos:
                if t.get("fecha_registro"):
                    try:
                        fecha = datetime.fromisoformat(t["fecha_registro"].replace("Z", "+00:00"))
                        clave = fecha.strftime("%Y-%m")
                        por_mes[clave] = por_mes.get(clave, 0) + 1
                    except Exception:
                        pass

            por_mes = dict(sorted(por_mes.items(), reverse=True)[:6])
            ultimos = todos[:10]

            alertas = []
            for t in vencidos:
                alertas.append({"tipo": "danger", "icono": "🚨",
                    "mensaje": f"SOAT VENCIDO - {t['nombres']} ({t['identificacion']}) - Placa: {t['placa']}"})
            for t in por_vencer:
                alertas.append({"tipo": "warning", "icono": "⚠️",
                    "mensaje": f"SOAT POR VENCER - {t['nombres']} ({t['identificacion']}) - Placa: {t['placa']}"})
            for t in no_legibles:
                alertas.append({"tipo": "info", "icono": "📷",
                    "mensaje": f"SOAT NO LEGIBLE - {t['nombres']} ({t['identificacion']}) - Requiere nuevo archivo"})

            return {
                "total": total, "vigentes": len(vigentes), "vencidos": len(vencidos),
                "por_vencer": len(por_vencer), "no_legibles": len(no_legibles),
                "pendientes": len(pendientes), "pct_vigentes": pct_vigentes,
                "pct_vencidos": pct_vencidos, "pct_por_vencer": pct_por_vencer,
                "pct_no_legibles": pct_no_legibles, "por_tipo_vehiculo": por_tipo,
                "por_cargo": por_cargo, "por_mes": por_mes,
                "ultimos_registros": ultimos, "alertas": alertas
            }

        except Exception as e:
            print(f"Error generando indicadores: {e}")
            return {"total": 0, "vigentes": 0, "vencidos": 0, "por_vencer": 0,
                    "no_legibles": 0, "pendientes": 0, "pct_vigentes": 0,
                    "pct_vencidos": 0, "pct_por_vencer": 0, "pct_no_legibles": 0,
                    "por_tipo_vehiculo": {}, "por_cargo": {}, "por_mes": {},
                    "ultimos_registros": [], "alertas": []}

    def eliminar_trabajador(self, trabajador_id: str) -> bool:
        """Elimina un trabajador por su ID."""
        try:
            self.client.table("trabajadores").delete().eq("id", trabajador_id).execute()
            return True
        except Exception as e:
            print(f"Error eliminando trabajador: {e}")
            return False
