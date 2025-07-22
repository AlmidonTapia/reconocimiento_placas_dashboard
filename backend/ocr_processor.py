import cv2
import numpy as np
import re
import easyocr
import pytesseract

class OCRProcessor:
    """
    Procesador de OCR para reconocimiento de placas de matrícula.
    Utiliza múltiples métodos OCR para maximizar la precisión.
    """
    
    def __init__(self):
        """
        Inicializa el procesador OCR con EasyOCR y Tesseract como backup.
        """
        # Inicializar EasyOCR con español e inglés
        try:
            self.reader = easyocr.Reader(['es', 'en'], gpu=True)
            print("EasyOCR inicializado correctamente con GPU")
        except Exception as e:
            try:
                self.reader = easyocr.Reader(['es', 'en'], gpu=False)
                print("EasyOCR inicializado correctamente con CPU")
            except Exception as e2:
                print(f"Error inicializando EasyOCR: {e2}")
                self.reader = None
        
        # Verificar disponibilidad de Tesseract
        try:
            pytesseract.get_tesseract_version()
            self.tesseract_available = True
            print("Tesseract OCR disponible")
        except:
            self.tesseract_available = False
            print("Tesseract OCR no disponible")
    
    def recognize_text(self, plate_image: np.ndarray) -> str:
        """
        Reconoce el texto de una imagen de matrícula utilizando múltiples métodos OCR.
        
        Args:
            plate_image (np.ndarray): Imagen recortada de la matrícula.
            
        Returns:
            str: Texto reconocido de la matrícula, vacío si no se reconoce nada válido.
        """
        if plate_image is None or plate_image.size == 0:
            return ""
        
        best_result = ""
        confidence_threshold = 0.6
        
        try:
            # Preprocesar la imagen
            processed_image = preprocess_for_ocr(plate_image)
            
            # Método 1: EasyOCR con configuración optimizada para placas
            if self.reader:
                try:
                    # Usar solo caracteres alfanuméricos para mejor rendimiento
                    results = self.reader.readtext(processed_image, 
                                                 allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-',
                                                 width_ths=0.7,
                                                 height_ths=0.7)
                    
                    for (bbox, text, confidence) in results:
                        if confidence > confidence_threshold:
                            cleaned = clean_text(text)
                            if cleaned and is_valid_peruvian_plate(cleaned):
                                if len(cleaned) > len(best_result):
                                    best_result = cleaned
                                    print(f"EasyOCR encontró placa válida: {cleaned} (confianza: {confidence:.2f})")
                                    
                except Exception as e:
                    print(f"Error con EasyOCR: {e}")
            
            # Método 2: Tesseract como backup si EasyOCR no da buenos resultados
            if not best_result and self.tesseract_available:
                try:
                    # Configuración optimizada para placas
                    custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-'
                    text = pytesseract.image_to_string(processed_image, config=custom_config, lang='eng')
                    cleaned = clean_text(text)
                    if cleaned and is_valid_peruvian_plate(cleaned):
                        best_result = cleaned
                        print(f"Tesseract encontró placa válida: {cleaned}")
                except Exception as e:
                    print(f"Error con Tesseract: {e}")
            
            # Método 3: Intentar con imagen original si el procesamiento no funciona
            if not best_result and self.reader:
                try:
                    results = self.reader.readtext(plate_image,
                                                 allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ-',
                                                 width_ths=0.5,
                                                 height_ths=0.5)
                    
                    for (bbox, text, confidence) in results:
                        if confidence > 0.4:  # Umbral más bajo para imagen original
                            cleaned = clean_text(text)
                            if cleaned and len(cleaned) >= 5:
                                # Si no es válido según patrones estrictos, intentar con patrones más flexibles
                                if is_valid_peruvian_plate(cleaned) or len(cleaned) >= 6:
                                    best_result = cleaned
                                    print(f"OCR con imagen original: {cleaned} (confianza: {confidence:.2f})")
                                    break
                                    
                except Exception as e:
                    print(f"Error con imagen original: {e}")
            
            # Método 4: Último intento con parámetros más relajados
            if not best_result and self.reader:
                try:
                    results = self.reader.readtext(plate_image, 
                                                 width_ths=0.3,
                                                 height_ths=0.3,
                                                 mag_ratio=1.5)
                    
                    all_text = ""
                    for (bbox, text, confidence) in results:
                        if confidence > 0.3:
                            all_text += text.upper().replace(' ', '')
                    
                    if all_text:
                        cleaned = clean_text(all_text)
                        if cleaned and len(cleaned) >= 5:
                            best_result = cleaned
                            print(f"OCR último intento: {cleaned}")
                            
                except Exception as e:
                    print(f"Error en último intento: {e}")
            
            if best_result:
                print(f"OCR Final Result: '{best_result}'")
            else:
                print("OCR no pudo reconocer una placa válida")
                
            return best_result
            
        except Exception as e:
            print(f"Error general en OCR: {e}")
            return ""

def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Aplica preprocesamiento avanzado a la imagen de la matrícula para mejorar la precisión del OCR.
    """
    # Redimensionar la imagen para mejor OCR
    height, width = image.shape[:2]
    if height < 60:
        scale = 60 / height
        new_width = int(width * scale)
        image = cv2.resize(image, (new_width, 60), interpolation=cv2.INTER_CUBIC)
    elif height > 200:
        scale = 200 / height
        new_width = int(width * scale)
        image = cv2.resize(image, (new_width, 200), interpolation=cv2.INTER_CUBIC)
    
    # Convertir a escala de grises
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Aplicar filtro bilateral para reducir ruido manteniendo bordes
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    
    # Mejora de contraste usando CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # Binarización adaptativa
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    
    # Operaciones morfológicas para limpiar la imagen
    kernel = np.ones((2,2), np.uint8)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
    
    return binary

def is_valid_peruvian_plate(text: str) -> bool:
    """
    Valida si el texto coincide con el formato de placas peruanas.
    
    Formatos válidos:
    - ABC-123 (3 letras, guión, 3 números)
    - ABC123 (3 letras, 3 números sin guión)
    - A1B-234 (letra, número, letra, guión, 3 números)
    - A1B234 (letra, número, letra, 3 números)
    """
    if not text or len(text) < 5:
        return False
    
    # Remover espacios y guiones para análisis
    clean = re.sub(r'[-\s]', '', text)
    
    if len(clean) < 5 or len(clean) > 8:
        return False
    
    # Patrones de placas peruanas
    patterns = [
        r'^[A-Z]{3}[0-9]{3}$',      # ABC123
        r'^[A-Z][0-9][A-Z][0-9]{3}$', # A1B234
        r'^[A-Z]{2}[0-9]{4}$',      # AB1234
        r'^[A-Z]{4}[0-9]{2}$',      # ABCD12
        r'^[A-Z]{1}[0-9]{2}[A-Z]{1}[0-9]{2}$', # A12B34
        r'^[0-9]{3}[A-Z]{3}$',      # 123ABC
    ]
    
    for pattern in patterns:
        if re.match(pattern, clean):
            return True
    
    return False

def clean_text(text: str) -> str:
    """
    Limpia y valida el texto reconocido por el OCR específicamente para placas peruanas.
    """
    if not text:
        return ""
    
    # Convertir a mayúsculas y limpiar
    text = text.upper().strip()
    
    # Limpiar caracteres no válidos
    cleaned = re.sub(r'[^A-Z0-9-]', '', text)
    
    # Remover guiones múltiples
    cleaned = re.sub(r'-+', '-', cleaned)
    
    # Si es muy corto o muy largo, descartar
    if len(cleaned) < 5 or len(cleaned) > 9:
        return ""
    
    # Si ya es válido, formatear
    if is_valid_peruvian_plate(cleaned):
        return format_plate(cleaned)
    
    # Intentar correcciones comunes
    corrections = {
        'O0': '00',  # O seguida de 0 -> 00
        '0O': '00',  # 0 seguida de O -> 00
        'II': '11',  # II -> 11
        'OO': '00',  # OO -> 00
        'B8': 'B8',  # B8 válido
        '8B': '8B',  # 8B válido
        'S5': 'S5',  # S5 válido
        '5S': '5S',  # 5S válido
    }
    
    # Intentar correcciones
    for wrong, right in corrections.items():
        if wrong in cleaned:
            test_corrected = cleaned.replace(wrong, right)
            if is_valid_peruvian_plate(test_corrected):
                return format_plate(test_corrected)
    
    # Intentar correcciones carácter por carácter
    char_corrections = {
        'O': '0', '0': 'O',  # Intercambiar O y 0
        'I': '1', '1': 'I',  # Intercambiar I y 1
        'S': '5', '5': 'S',  # Intercambiar S y 5
        'B': '8', '8': 'B',  # Intercambiar B y 8
        'Z': '2', '2': 'Z',  # Intercambiar Z y 2
        'G': '6', '6': 'G',  # Intercambiar G y 6
    }
    
    # Generar variaciones
    variations = [cleaned]
    for i, char in enumerate(cleaned):
        if char in char_corrections:
            variation = cleaned[:i] + char_corrections[char] + cleaned[i+1:]
            variations.append(variation)
    
    # Probar variaciones
    for variation in variations:
        if is_valid_peruvian_plate(variation):
            return format_plate(variation)
    
    # Si tiene longitud apropiada pero no coincide con patrones, devolver limpiado
    if 5 <= len(cleaned) <= 8:
        return cleaned
    
    return ""

def format_plate(text: str) -> str:
    """
    Formatea la placa al estándar peruano con guión.
    """
    clean = re.sub(r'[-\s]', '', text)
    
    if len(clean) == 6:
        if re.match(r'^[A-Z]{3}[0-9]{3}$', clean):
            return f"{clean[:3]}-{clean[3:]}"
        elif re.match(r'^[A-Z][0-9][A-Z][0-9]{3}$', clean):
            return f"{clean[:3]}-{clean[3:]}"
    
    return clean

# Instancia global del procesador OCR
ocr_processor = OCRProcessor()

def perform_ocr(plate_image: np.ndarray) -> str:
    """
    Realiza OCR en la imagen de una matrícula usando el procesador global.
    
    Args:
        plate_image (np.ndarray): Imagen que contiene la matrícula.
        
    Returns:
        str: El texto de la matrícula reconocido y limpiado.
    """
    if ocr_processor.reader is None:
        print("OCR no disponible")
        return ""
    
    return ocr_processor.recognize_text(plate_image)

# Para pruebas
if __name__ == '__main__':
    # Carga una imagen de prueba
    test_image_path = '../data/captured/test_plate.jpg'
    try:
        image = cv2.imread(test_image_path)
        if image is None:
            print(f"No se pudo cargar la imagen de prueba en {test_image_path}")
        else:
            print("Realizando prueba de OCR en la imagen...")
            text = perform_ocr(image)
            print(f"Texto reconocido: '{text}'")
    except Exception as e:
        print(f"Error en la prueba: {e}")
