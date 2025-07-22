# backend/plate_detector.py
# Este módulo utiliza el modelo YOLO para detectar matrículas en una imagen.

import cv2
import numpy as np
import torch
from model_manager import load_model
from ocr_processor import perform_ocr
from config import YOLO_CLASSES
import os
from datetime import datetime
import torch.cuda
import base64

# Cargar el modelo una sola vez al iniciar el módulo
model = load_model()

def detect_and_process_plates(frame: np.ndarray, camera_source: str) -> tuple[np.ndarray, list]:
    """
    Detecta matrículas en un frame, realiza OCR y dibuja los resultados.

    Args:
        frame (np.ndarray): El frame de video (imagen) a procesar.
        camera_source (str): Identificador de la fuente de la cámara.

    Returns:
        tuple: 
            - np.ndarray: El frame con las detecciones dibujadas.
            - list: Una lista de diccionarios, cada uno con los datos de una matrícula reconocida.
    """
    if model is None:
        # Si el modelo no se cargó, devuelve el frame original
        cv2.putText(frame, "Error: Modelo no cargado", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        return frame, []

    # Realizar la inferencia con el modelo YOLO con optimizaciones
    with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
        results = model(frame, conf=0.35, iou=0.45, verbose=False)
    
    detected_plates = []
    
    # Liberar memoria CUDA después de la inferencia
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    # results[0].boxes contiene las cajas de las detecciones
    for box in results[0].boxes:
        # Obtener las coordenadas de la caja (x1, y1, x2, y2)
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        
        # Obtener la confianza y la clase
        confidence = float(box.conf[0])
        class_id = int(box.cls[0])
        class_name = model.names[class_id]
        
        # Nos aseguramos de que la clase sea 'license_plate' o la que corresponda
        # (El modelo que descargamos usa 'license-plate')
        if 'license' in class_name.lower():
            # Recortar la imagen de la matrícula del frame original
            plate_crop = frame[y1:y2, x1:x2]
            
            # Guardar la imagen recortada para referencia y posible re-entrenamiento
            saved_image_path = save_capture(plate_crop)

            # Realizar OCR en la matrícula recortada
            plate_text = perform_ocr(plate_crop)
            
            # Convertir imagen a base64 para guardar en BD
            plate_image_base64 = ""
            try:
                _, buffer = cv2.imencode('.jpg', plate_crop)
                plate_image_base64 = base64.b64encode(buffer).decode('utf-8')
            except Exception as e:
                print(f"Error al convertir imagen a base64: {e}")
            
            # Dibujar la caja delimitadora en el frame
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Preparar la etiqueta con el texto y la confianza
            label = f"{plate_text} ({confidence:.2f})"
            
            # Dibujar un fondo para la etiqueta
            (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w, y1), (0, 255, 0), -1)
            
            # Escribir el texto de la matrícula reconocida
            cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

            # Si el OCR tuvo éxito, añadir a la lista de resultados
            if plate_text:
                detected_plates.append({
                    "plate_text": plate_text,
                    "confidence": confidence,
                    "box": [x1, y1, x2, y2],
                    "image_path": saved_image_path,
                    "image_base64": plate_image_base64
                })
    
    return frame, detected_plates

def save_capture(image: np.ndarray) -> str:
    """Guarda una imagen en la carpeta 'data/captured' y devuelve la ruta."""
    capture_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'captured')
    os.makedirs(capture_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"capture_{timestamp}.jpg"
    filepath = os.path.join(capture_dir, filename)
    
    try:
        cv2.imwrite(filepath, image)
        return filepath
    except Exception as e:
        print(f"Error al guardar la captura: {e}")
        return ""
