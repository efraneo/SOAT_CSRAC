"""
soat_validator.py
Validación de imágenes de SOAT usando RapidOCR (No necesita Tesseract en el servidor).
- Detección de calidad (pixelación / desenfoque)
- Extracción de texto con OCR
- Detección de fecha de vencimiento
"""
import re
import cv2
import numpy as np
from datetime import datetime, date
from config import Config


class SOATValidator:
    """Validador de documentos SOAT."""

    def __init__(self):
        self.min_quality = Config.MIN_IMAGE_QUALITY_SCORE
        self.min_width = Config.MIN_IMAGE_WIDTH
        self.min_height = Config.MIN_IMAGE_HEIGHT
        self.dias_alerta = Config.SOAT_ALERTA_DIAS
        self._engine = None

    @property
    def engine(self):
        """Inicializa el motor OCR de forma diferida (solo cuando se necesite)."""
        if self._engine is None:
            from rapidocr_onnxruntime import RapidOCR
            self._engine = RapidOCR()
        return self._engine

    def validar_archivo(self, archivo_bytes: bytes, nombre_archivo: str) -> dict:
        """Punto de entrada principal para validar el SOAT."""
        resultado = {
            "calidad_ok": False,
            "calidad_score": 0.0,
            "calidad_mensaje": "",
            "texto_extraido": "",
            "fecha_vencimiento": None,
            "estado": "No legible",
            "mensaje_general": ""
        }

        extensiones_permitidas = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
        ext = nombre_archivo.lower().rsplit(".", 1)[-1] if "." in nombre_archivo else ""
        if f".{ext}" not in extensiones_permitidas:
            resultado["calidad_mensaje"] = (
                f"El archivo '{nombre_archivo}' no es una imagen válida. "
                f"Formatos permitidos: JPG, PNG, BMP, TIFF, WEBP"
            )
            resultado["mensaje_general"] = resultado["calidad_mensaje"]
            return resultado

        try:
            nparr = np.frombuffer(archivo_bytes, np.uint8)
            imagen = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if imagen is None:
                resultado["calidad_mensaje"] = "No se pudo leer la imagen. El archivo puede estar corrupto."
                resultado["mensaje_general"] = resultado["calidad_mensaje"]
                return resultado
        except Exception as e:
            resultado["calidad_mensaje"] = f"Error al procesar la imagen: {e}"
            resultado["mensaje_general"] = resultado["calidad_mensaje"]
            return resultado

        # Evaluar calidad
        calidad = self._evaluar_calidad(imagen)
        resultado["calidad_score"] = calidad["score"]
        resultado["calidad_ok"] = calidad["ok"]
        resultado["calidad_mensaje"] = calidad["mensaje"]

        if not calidad["ok"]:
            resultado["mensaje_general"] = (
                f"❌ Imagen no apta: {calidad['mensaje']}. "
                "Por favor, toma una foto más clara y nítida del SOAT."
            )
            resultado["estado"] = "No legible"
            return resultado

        # Extraer texto
        texto = self._extraer_texto(imagen)
        resultado["texto_extraido"] = texto

        if not texto or len(texto.strip()) < 15:
            resultado["estado"] = "No legible"
            resultado["mensaje_general"] = (
                "❌ No se pudo extraer texto del SOAT. "
                "Asegúrate de que la imagen sea clara y contenga el documento completo."
            )
            return resultado

        # Buscar fecha
        fecha_venc = self._buscar_fecha_vencimiento(texto)
        resultado["fecha_vencimiento"] = fecha_venc

        if fecha_venc is None:
            resultado["estado"] = "No legible"
            resultado["mensaje_general"] = (
                "⚠️ Se extrajo texto pero no se encontró la fecha de vencimiento del SOAT."
            )
            return resultado

        # Determinar estado
        estado = self._determinar_estado(fecha_venc)
        resultado["estado"] = estado
        fecha_str = fecha_venc.strftime("%d/%m/%Y")
        
        if estado == "Vigente":
            resultado["mensaje_general"] = f"✅ SOAT VIGENTE. Fecha de vencimiento: {fecha_str}."
        elif estado == "Por vencer":
            dias_restantes = (fecha_venc - date.today()).days
            resultado["mensaje_general"] = f"⚠️ SOAT POR VENCER. Vence el {fecha_str} (faltan {dias_restantes} días)."
        else:
            resultado["mensaje_general"] = f"🚨 SOAT VENCIDO. Fecha de vencimiento: {fecha_str}."

        return resultado

    def _evaluar_calidad(self, imagen: np.ndarray) -> dict:
        """Evalúa la calidad de la imagen usando varianza del Laplaciano y resolución."""
        resultados = {"score": 0.0, "ok": False, "mensaje": ""}
        h, w = imagen.shape[:2]
        
        if w < self.min_width or h < self.min_height:
            resultados["mensaje"] = f"Resolución muy baja ({w}x{h}). Mínimo: {self.min_width}x{self.min_height}."
            return resultados

        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)
        varianza = cv2.Laplacian(gris, cv2.CV_64F).var()
        resultados["score"] = round(varianza, 2)

        if varianza < self.min_quality:
            resultados["mensaje"] = f"Imagen pixelada o borrosa (índice: {varianza:.1f}, mínimo: {self.min_quality:.1f})."
            return resultados

        brillo_medio = np.mean(gris)
        if brillo_medio < 40:
            resultados["mensaje"] = f"Imagen demasiado oscura (brillo: {brillo_medio:.0f})."
            return resultados
        if brillo_medio > 240:
            resultados["mensaje"] = f"Imagen sobreexpuesta (brillo: {brillo_medio:.0f})."
            return resultados

        resultados["ok"] = True
        resultados["mensaje"] = f"Calidad aceptable (nitidez: {varianza:.1f}, resolución: {w}x{h})."
        return resultados

    def _extraer_texto(self, imagen: np.ndarray) -> str:
        """Extrae texto usando RapidOCR."""
        try:
            # RapidOCR recibe imagen BGR de OpenCV directamente
            resultados, _ = self.engine(imagen)
            if not resultados:
                return ""
            
            # Unir todos los textos detectados, filtrando los de baja confianza
            textos = [txt for (_, txt, conf) in resultados if conf > 0.4]
            return " ".join(textos).strip()
        except Exception as e:
            print(f"Error en OCR: {e}")
            return ""

    def _buscar_fecha_vencimiento(self, texto: str) -> date | None:
        """Busca la fecha de vencimiento del SOAT en el texto."""
        texto_upper = texto.upper()
        keywords = [
            "VENCIMIENTO", "VIGENCIA", "EXPIRA", "FECHA DE VENC",
            "VENCE", "VALIDO HASTA", "VIGENTE HASTA", "HASTA",
            "FIN DE VIGENCIA", "TERMINO", "VTO"
        ]

        for kw in keywords:
            idx = texto_upper.find(kw)
            if idx != -1:
                ventana = texto[idx:idx + 80]
                fecha = self._extraer_fecha_de_texto(ventana)
                if fecha:
                    return fecha

        todas_fechas = self._extraer_todas_fechas(texto)
        if todas_fechas:
            todas_fechas.sort(reverse=True)
            return todas_fechas[0]

        return None

    def _extraer_fecha_de_texto(self, texto: str) -> date | None:
        """Intenta extraer una fecha de un fragmento de texto."""
        pat1 = r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})'
        match = re.search(pat1, texto)
        if match:
            try:
                dia, mes, anio = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2035:
                    return date(anio, mes, dia)
            except ValueError:
                pass

        pat2 = r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})'
        match = re.search(pat2, texto)
        if match:
            try:
                anio, mes, dia = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2035:
                    return date(anio, mes, dia)
            except ValueError:
                pass
        return None

    def _extraer_todas_fechas(self, texto: str) -> list:
        """Extrae todas las fechas válidas del texto."""
        fechas = []
        for match in re.finditer(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', texto):
            try:
                dia, mes, anio = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2035:
                    fechas.append(date(anio, mes, dia))
            except ValueError:
                pass

        for match in re.finditer(r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})', texto):
            try:
                anio, mes, dia = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2035:
                    fechas.append(date(anio, mes, dia))
            except ValueError:
                pass
        return fechas

    def _determinar_estado(self, fecha_vencimiento: date) -> str:
        """Determina el estado del SOAT."""
        diferencia = (fecha_vencimiento - date.today()).days
        if diferencia < 0:
            return "Vencido"
        elif diferencia <= self.dias_alerta:
            return "Por vencer"
        else:
            return "Vigente"
