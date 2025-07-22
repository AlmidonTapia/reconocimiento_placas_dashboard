import os
os.environ['PYTORCH_ENABLE_WEIGHTS_ONLY_OFF'] = '1'

from ultralytics import YOLO
import torch

def check_models():
    try:
        # Intentar cargar el modelo base YOLOv8
        model_base = YOLO('models/yolov8n.pt')
        print("Modelo base YOLOv8 cargado correctamente")
        
        # Intentar cargar el modelo de detección de placas
        model_plates = YOLO('models/license_plate_detector.pt')
        print("Modelo de detección de placas cargado correctamente")
        
        return True
    except Exception as e:
        print(f"Error al cargar los modelos: {str(e)}")
        return False

if __name__ == "__main__":
    print("Verificando modelos...")
    check_models()
