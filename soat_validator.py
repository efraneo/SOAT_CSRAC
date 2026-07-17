"""
soat_validator.py
Validación de imágenes de SOAT:
- Detección de calidad (pixelación / desenfoque)
- Extracción de texto con OCR (Tesseract)
- Detección de fecha de vencimiento
- Determinación del estado del SOAT
"""
import re
import cv2
import numpy as np
from PIL import Image
from datetime import datetime, date
from dateutil.parser import parse as parse_fecha
import pytesseract
from config import Config

# Configurar ruta de Tesseract si está definida
if Config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD


class SOATValidator:
    """Validador de documentos SOAT."""

    def __init__(self):
        self.min_quality = Config.MIN_IMAGE_QUALITY_SCORE
        self.min_width = Config.MIN_IMAGE_WIDTH
        self.min_height = Config.MIN_IMAGE_HEIGHT
        self.dias_alerta = Config.SOAT_ALERTA_DIAS

    def validar_archivo(self, archivo_bytes: bytes, nombre_archivo: str) -> dict:
        """
        Punto de entrada principal.
        Recibe los bytes del archivo y retorna un dict con:
          - calidad_ok: bool
          - calidad_score: float
          - calidad_mensaje: str
          - texto_extraido: str
          - fecha_vencimiento: date | None
          - estado: str ("Vigente", "Vencido", "Por vencer", "No legible")
          - mensaje_general: str
        """
        resultado = {
            "calidad_ok": False,
            "calidad_score": 0.0,
            "calidad_mensaje": "",
            "texto_extraido": "",
            "fecha_vencimiento": None,
            "estado": "No legible",
            "mensaje_general": ""
        }

        # ── Paso 1: Verificar que sea imagen ──
        extensiones_permitidas = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
        ext = nombre_archivo.lower().rsplit(".", 1)[-1] if "." in nombre_archivo else ""
        if f".{ext}" not in extensiones_permitidas:
            resultado["calidad_mensaje"] = (
                f"El archivo '{nombre_archivo}' no es una imagen válida. "
                f"Formatos permitidos: JPG, PNG, BMP, TIFF, WEBP"
            )
            resultado["mensaje_general"] = resultado["calidad_mensaje"]
            return resultado

        # ── Paso 2: Cargar imagen ──
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

        # ── Paso 3: Evaluar calidad de imagen ──
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

        # ── Paso 4: Preprocesar imagen para OCR ──
        imagen_procesada = self._preprocesar_imagen(imagen)

        # ── Paso 5: Extraer texto con OCR ──
        texto = self._extraer_texto(imagen_procesada)
        resultado["texto_extraido"] = texto

        if not texto or len(texto.strip()) < 15:
            resultado["estado"] = "No legible"
            resultado["mensaje_general"] = (
                "❌ No se pudo extraer texto del SOAT. "
                "Asegúrate de que la imagen sea clara y contenga el documento completo."
            )
            return resultado

        # ── Paso 6: Buscar fecha de vencimiento ──
        fecha_venc = self._buscar_fecha_vencimiento(texto)
        resultado["fecha_vencimiento"] = fecha_venc

        if fecha_venc is None:
            resultado["estado"] = "No legible"
            resultado["mensaje_general"] = (
                "⚠️ Se extrajo texto pero no se encontró la fecha de vencimiento del SOAT. "
                "Verifica que la imagen muestre claramente la fecha de vigencia."
            )
            return resultado

        # ── Paso 7: Determinar estado ──
        estado = self._determinar_estado(fecha_venc)
        resultado["estado"] = estado

        fecha_str = fecha_venc.strftime("%d/%m/%Y")
        if estado == "Vigente":
            resultado["mensaje_general"] = (
                f"✅ SOAT VIGENTE. Fecha de vencimiento: {fecha_str}."
            )
        elif estado == "Por vencer":
            dias_restantes = (fecha_venc - date.today()).days
            resultado["mensaje_general"] = (
                f"⚠️ SOAT POR VENCER. Vence el {fecha_str} "
                f"(faltan {dias_restantes} días)."
            )
        else:
            resultado["mensaje_general"] = (
                f"🚨 SOAT VENCIDO. Fecha de vencimiento: {fecha_str}."
            )

        return resultado

    def _evaluar_calidad(self, imagen: np.ndarray) -> dict:
        """Evalúa la calidad de la imagen usando varianza del Laplaciano y resolución."""
        resultados = {"score": 0.0, "ok": False, "mensaje": ""}

        # Verificar resolución
        h, w = imagen.shape[:2]
        if w < self.min_width or h < self.min_height:
            resultados["mensaje"] = (
                f"Resolución muy baja ({w}x{h}). "
                f"Mínimo requerido: {self.min_width}x{self.min_height} píxeles."
            )
            return resultados

        # Convertir a escala de grises
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

        # Calcular varianza del Laplaciano (métrica de desenfoque)
        varianza = cv2.Laplacian(gris, cv2.CV_64F).var()
        resultados["score"] = round(varianza, 2)

        if varianza < self.min_quality:
            resultados["mensaje"] = (
                f"Imagen pixelada o borrosa (índice de nitidez: {varianza:.1f}, "
                f"mínimo requerido: {self.min_quality:.1f})."
            )
            return resultados

        # Verificar si la imagen es demasiado oscura o clara
        brillo_medio = np.mean(gris)
        if brillo_medio < 40:
            resultados["mensaje"] = (
                f"Imagen demasiado oscura (brillo: {brillo_medio:.0f}). "
                "Mejora la iluminación."
            )
            return resultados
        if brillo_medio > 240:
            resultados["mensaje"] = (
                f"Imagen sobreexpuesta (brillo: {brillo_medio:.0f}). "
                "Reduce la luz al tomar la foto."
            )
            return resultados

        resultados["ok"] = True
        resultados["mensaje"] = (
            f"Calidad aceptable (nitidez: {varianza:.1f}, "
            f"resolución: {w}x{h}, brillo: {brillo_medio:.0f})."
        )
        return resultados

    def _preprocesar_imagen(self, imagen: np.ndarray) -> np.ndarray:
        """Preprocesa la imagen para mejorar el OCR."""
        # Convertir a escala de grises
        gris = cv2.cvtColor(imagen, cv2.COLOR_BGR2GRAY)

        # Reducir ruido
        denoised = cv2.fastNlMeansDenoising(gris, h=10)

        # Umbral adaptativo
        umbral = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )

        # Escalar si es muy pequeña
        h, w = umbral.shape
        if w < 800:
            escala = 800 / w
            umbral = cv2.resize(umbral, None, fx=escala, fy=escala,
                                interpolation=cv2.INTER_CUBIC)

        return umbral

    def _extraer_texto(self, imagen_procesada: np.ndarray) -> str:
        """Extrae texto de la imagen usando Tesseract OCR."""
        try:
            # Configuración para español y mejor detección
            custom_config = r'--oem 3 --psm 6 -l spa+eng'
            texto = pytesseract.image_to_string(imagen_procesada, config=custom_config)
            return texto.strip()
        except Exception as e:
            print(f"Error en OCR: {e}")
            return ""

    def _buscar_fecha_vencimiento(self, texto: str) -> date | None:
        """
        Busca la fecha de vencimiento del SOAT en el texto extraído.
        Usa múltiples estrategias:
        1. Buscar cerca de palabras clave
        2. Buscar todos los patrones de fecha
        3. Tomar la más probable como fecha de vencimiento
        """
        texto_upper = texto.upper()

        # Palabras clave que suelen estar cerca de la fecha de vencimiento
        keywords = [
            "VENCIMIENTO", "VIGENCIA", "EXPIRA", "FECHA DE VENC",
            "VENCE", "VALIDO HASTA", "VIGENTE HASTA", "HASTA",
            "FIN DE VIGENCIA", "TERMINO", "VTO"
        ]

        # ── Estrategia 1: Buscar fecha cerca de keywords ──
        for kw in keywords:
            idx = texto_upper.find(kw)
            if idx != -1:
                # Tomar una ventana de 80 caracteres después del keyword
                ventana = texto[idx:idx + 80]
                fecha = self._extraer_fecha_de_texto(ventana)
                if fecha:
                    return fecha

        # ── Estrategia 2: Buscar todas las fechas y tomar la más futura ──
        todas_fechas = self._extraer_todas_fechas(texto)
        if todas_fechas:
            # La fecha de vencimiento suele ser la más futura
            todas_fechas.sort(reverse=True)
            return todas_fechas[0]

        return None

    def _extraer_fecha_de_texto(self, texto: str) -> date | None:
        """Intenta extraer una fecha de un fragmento de texto."""
        # Patrón DD/MM/AAAA o DD-MM-AAAA
        pat1 = r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})'
        match = re.search(pat1, texto)
        if match:
            try:
                dia, mes, anio = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2035:
                    return date(anio, mes, dia)
            except ValueError:
                pass

        # Patrón AAAA-MM-DD
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

        # DD/MM/AAAA o DD-MM-AAAA
        for match in re.finditer(r'(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})', texto):
            try:
                dia, mes, anio = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2035:
                    fechas.append(date(anio, mes, dia))
            except ValueError:
                pass

        # AAAA-MM-DD
        for match in re.finditer(r'(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})', texto):
            try:
                anio, mes, dia = int(match.group(1)), int(match.group(2)), int(match.group(3))
                if 1 <= dia <= 31 and 1 <= mes <= 12 and 2000 <= anio <= 2035:
                    fechas.append(date(anio, mes, dia))
            except ValueError:
                pass

        return fechas

    def _determinar_estado(self, fecha_vencimiento: date) -> str:
        """Determina el estado del SOAT según la fecha de vencimiento."""
        hoy = date.today()
        diferencia = (fecha_vencimiento - hoy).days

        if diferencia < 0:
            return "Vencido"
        elif diferencia <= self.dias_alerta:
            return "Por vencer"
        else:
            return "Vigente"
