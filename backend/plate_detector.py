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
    seen_plates = set()
    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        confidence = float(box.conf[0])
        class_id = int(box.cls[0])
        class_name = model.names[class_id]
        if 'license' in class_name.lower() and confidence >= 0.60:
            plate_crop = frame[y1:y2, x1:x2]
            saved_image_path = save_capture(plate_crop)
            plate_text = perform_ocr(plate_crop)
            from ocr_processor import is_valid_peruvian_plate, clean_text
            plate_text_clean = clean_text(plate_text)
            # Corrección automática de confusiones comunes (X/K, S/5, Z/2, G/6, B/8, I/1, O/0, etc)
            confusion_pairs = [
                ("X", "K"), ("K", "X"),
                ("S", "5"), ("5", "S"),
                ("Z", "2"), ("2", "Z"),
                ("G", "6"), ("6", "G"),
                ("B", "8"), ("8", "B"),
                ("I", "1"), ("1", "I"),
                ("O", "0"), ("0", "O"),
                ("V", "I"), ("I", "V")
            ]
            # Generar todas las variantes posibles cambiando cada par de confusión
            def generate_variants(base):
                variants = set([base])
                for a, b in confusion_pairs:
                    if a in base:
                        v = base.replace(a, b)
                        if v != base:
                            variants.add(v)
                return variants
            alternatives = set()
            if plate_text_clean and is_valid_peruvian_plate(plate_text_clean):
                alternatives.add(plate_text_clean)
            # Generar variantes recursivamente (una pasada)
            for alt in list(alternatives):
                alternatives.update(generate_variants(alt))
            # Filtrar solo placas válidas
            valid_alternatives = set([p for p in alternatives if is_valid_peruvian_plate(p)])
            for alt_plate in valid_alternatives:
                if not alt_plate or alt_plate in seen_plates:
                    continue
                seen_plates.add(alt_plate)
                plate_image_base64 = ""
                try:
                    _, buffer = cv2.imencode('.jpg', plate_crop)
                    plate_image_base64 = base64.b64encode(buffer).decode('utf-8')
                except Exception as e:
                    print(f"Error al convertir imagen a base64: {e}")
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                label = f"{alt_plate} ({confidence:.2f})"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w, y1), (0, 255, 0), -1)
                cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
                detected_plates.append({
                    "plate_text": alt_plate,
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
