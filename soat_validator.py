"""
soat_validator.py
Validación de SOAT usando IA avanzada (OpenAI GPT-4o-mini).
Ignora logos, lee fechas borrosas y entiende el formato FOSFEC colombiano.
"""
import re
import io
import base64
import numpy as np
from PIL import Image
from datetime import date
from config import Config

class SOATValidator:
    def __init__(self):
        self.min_quality = Config.MIN_IMAGE_QUALITY_SCORE
        self.min_width = Config.MIN_IMAGE_WIDTH
        self.min_height = Config.MIN_IMAGE_HEIGHT
        self.dias_alerta = Config.SOAT_ALERTA_DIAS

    def validar_archivo(self, archivo_bytes: bytes, nombre_archivo: str) -> dict:
        resultado = {
            "calidad_ok": False, "calidad_score": 0.0, "calidad_mensaje": "",
            "texto_extraido": "", "fecha_vencimiento": None, 
            "estado": "No legible", "mensaje_general": ""
        }
        
        ext = nombre_archivo.lower().rsplit(".", 1)[-1] if "." in nombre_archivo else ""
        
        # 1. Convertir PDF a Imagen si es necesario
        if ext == "pdf":
            try:
                import fitz
                doc = fitz.open(stream=archivo_bytes, filetype="pdf")
                if len(doc) > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap(dpi=250) # Alta resolución para la IA
                    archivo_bytes = pix.tobytes("png")
                    nombre_archivo = "soat_convertido.png"
                doc.close()
            except Exception as e:
                resultado["calidad_mensaje"] = f"Error al leer el PDF: {e}"
                resultado["mensaje_general"] = resultado["calidad_mensaje"]
                return resultado
        else:
            if f".{ext}" not in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}:
                resultado["calidad_mensaje"] = "Formato no válido. Use JPG, PNG o PDF."
                resultado["mensaje_general"] = resultado["calidad_mensaje"]
                return resultado

        # 2. Abrir imagen
        try:
            imagen_pil = Image.open(io.BytesIO(archivo_bytes))
            if imagen_pil.mode != 'RGB': imagen_pil = imagen_pil.convert('RGB')
        except Exception as e:
            resultado["calidad_mensaje"] = f"Error al leer: {e}"
            resultado["mensaje_general"] = resultado["calidad_mensaje"]
            return resultado

        # 3. Evaluar calidad básica (para rechazar fotos completamente negras/blancas)
        calidad = self._evaluar_calidad(imagen_pil)
        resultado["calidad_score"] = calidad["score"]
        resultado["calidad_ok"] = calidad["ok"]
        resultado["calidad_mensaje"] = calidad["mensaje"]
        
        if not calidad["ok"]:
            resultado["estado"] = "No legible"
            resultado["mensaje_general"] = f"❌ Imagen no apta: {calidad['mensaje']}."
            return resultado

        # 4. Usar IA (GPT-4o-mini) para leer el SOAT
        fecha_venc = self._leer_fecha_con_ia(archivo_bytes)
        resultado["fecha_vencimiento"] = fecha_venc
        
        if not fecha_venc:
            resultado["estado"] = "Pendiente"
            resultado["mensaje_general"] = "⚠️ La IA no pudo identificar la fecha en el soporte. Tu registro ha quedado guardado y un administrador lo validará manualmente."
            return resultado

        # 5. Determinar estado
        estado = self._determinar_estado(fecha_venc)
        resultado["estado"] = estado
        fecha_str = fecha_venc.strftime("%d/%m/%Y")
        
        if estado == "Vigente":
            resultado["mensaje_general"] = f"✅ SOAT VIGENTE. Vence: {fecha_str}."
        elif estado == "Por vencer":
            resultado["mensaje_general"] = f"⚠️ POR VENCER. Vence el {fecha_str} ({(fecha_venc - date.today()).days} días)."
        else:
            resultado["mensaje_general"] = f"🚨 SOAT VENCIDO. Venció el {fecha_str}."
        
        return resultado

    def _evaluar_calidad(self, imagen_pil: Image.Image) -> dict:
        """Revisa que la imagen no sea un archivo vacío o completamente negro/blanco."""
        resultados = {"score": 0.0, "ok": False, "mensaje": ""}
        w, h = imagen_pil.size
        if w < self.min_width or h < self.min_height:
            resultados["mensaje"] = f"Resolución muy baja ({w}x{h})."
            return resultados
        
        gris_np = np.array(imagen_pil.convert('L'), dtype=np.float64)
        laplacian = (
            gris_np[:-2, 1:-1] + gris_np[2:, 1:-1] + 
            gris_np[1:-1, :-2] + gris_np[1:-1, 2:] - 
            4 * gris_np[1:-1, 1:-1]
        )
        varianza = np.var(laplacian)
        score = round(varianza, 2)
        resultados["score"] = score
        
        if varianza < self.min_quality:
            resultados["mensaje"] = f"Imagen borrosa (índice: {score})."
            return resultados
        
        brillo = np.mean(gris_np)
        if brillo < 30:
            resultados["mensaje"] = "Imagen demasiado oscura."
            return resultados
        if brillo > 245:
            resultados["mensaje"] = "Imagen sobreexpuesta."
            return resultados
            
        resultados["ok"] = True
        resultados["mensaje"] = f"Calidad OK (nitidez: {score})."
        return resultados

    def _leer_fecha_con_ia(self, archivo_bytes: bytes) -> date | None:
        """Usa GPT-4o-mini para encontrar la fecha de vencimiento del SOAT."""
        try:
            import openai
            client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
            
            b64_image = base64.b64encode(archivo_bytes).decode("utf-8")
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Eres un experto leyendo documentos de tránsito colombianos, específicamente SOAT / FOSFEC. "
                                "Tu ÚNICA misión es encontrar la fecha de vencimiento.\n\n"
                                "BUSCA palabras clave: VIGENCIA, EXPIRA, VENCIMIENTO, VTO, HASTA.\n"
                                "Si encuentras la fecha, devuélvela SOLO en formato AAAA-MM-DD. NADA MÁS.\n"
                                "Si NO logras identificar la fecha con seguridad, devuelve EXACTAMENTE la palabra: NO_ENCONTRADA"
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}",
                                "detail": "high"
                            }
                        }
                    ]
                }],
                max_tokens=15
            )
            
            texto_respuesta = response.choices[0].message.content.strip().upper()
            
            if texto_respuesta == "NO_ENCONTRADA":
                return None
            
            # Limpiar respuesta y buscar fecha
            texto_limpio = re.sub(r'[^0-9\-\/]', '', texto_respuesta)
            
            # Buscar AAAA-MM-DD
            match = re.search(r'(\d{4})-(\d{2})-(\d{2})', texto_limpio)
            if match:
                try:
                    anio, mes, dia = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if 2000 <= anio <= 2035 and 1 <= mes <= 12 and 1 <= dia <= 31:
                        return date(anio, mes, dia)
                except ValueError:
                    pass
            
            # Buscar DD-MM-AAAA o DD/MM/AAAA
            match = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})', texto_limpio)
            if match:
                try:
                    dia, mes, anio = int(match.group(1)), int(match.group(2)), int(match.group(3))
                    if 2000 <= anio <= 2035 and 1 <= mes <= 12 and 1 <= dia <= 31:
                        return date(anio, mes, dia)
                except ValueError:
                    pass
            
            return None
            
        except Exception as e:
            print(f"Error con IA para leer SOAT: {e}")
            return None

    def _determinar_estado(self, fecha_vencimiento: date) -> str:
        diff = (fecha_vencimiento - date.today()).days
        if diff < 0: return "Vencido"
        if diff <= self.dias_alerta: return "Por vencer"
        return "Vigente"
