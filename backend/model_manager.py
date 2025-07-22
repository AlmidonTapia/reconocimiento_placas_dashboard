# backend/model_manager.py
import os
import torch
from ultralytics import YOLO
from config import YOLO_PLATE_DETECTOR_PATH

# Variable global para almacenar el modelo
_model = None

def load_model(model_path=YOLO_PLATE_DETECTOR_PATH):
    """Carga el modelo YOLO desde la ruta especificada."""
    global _model
    
    if not os.path.exists(model_path):
        print(f"Error: No se encontró el modelo en '{model_path}'")
        print(f"Asegúrate de que el modelo '{os.path.basename(model_path)}' esté en la carpeta 'models/'")
        return None

    try:
        # Primero, configurar las variables de entorno necesarias
        os.environ['PYTORCH_ENABLE_UNSAFE_LOAD'] = '1'
        
        # Verificar disponibilidad de CUDA
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f"Dispositivo disponible: {device}")
        
        if device == 'cuda':
            print(f"GPU encontrada: {torch.cuda.get_device_name(0)}")
            torch.backends.cudnn.benchmark = True
        
        # Cargar el modelo
        print(f"Intentando cargar el modelo desde '{model_path}'...")
        _model = YOLO(model_path, task='detect')
        
        # Mover el modelo al dispositivo correspondiente
        _model.to(device)
        
        # Configurar parámetros para inferencia
        _model.conf = 0.35  # umbral de confianza
        _model.iou = 0.45   # umbral de IOU
        
        print(f"Modelo cargado exitosamente en {device}")
        return _model
        
    except Exception as e:
        print(f"Error al cargar el modelo: {str(e)}")
        try:
            print("Intentando método alternativo de carga...")
            _model = YOLO(model_path)
            _model.to(device)
            print("Modelo cargado exitosamente con método alternativo")
            return _model
        except Exception as e2:
            print(f"Error en segundo intento de carga: {str(e2)}")
            return None
        
# Para pruebas
if __name__ == "__main__":
    print("Probando la carga del modelo...")
    model = load_model()
    if model:
        print("Prueba de carga exitosa")
        model.info()
    else:
        print("Prueba de carga fallida")