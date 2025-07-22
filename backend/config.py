# backend/config.py
# Este archivo centraliza las configuraciones importantes del proyecto.

import os

# --- Configuración de Tesseract OCR ---
# ¡IMPORTANTE! Cambia esta ruta a donde instalaste Tesseract en tu PC.
# Esta es la ruta al archivo ejecutable tesseract.exe.
TESSERACT_CMD_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- Configuración de la Base de Datos ---
# Define la ruta a la base de datos SQLite.
DATABASE_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'database.db')

# --- Configuración de Modelos ---
# Define las rutas a los modelos de YOLO que vamos a utilizar.
# Asegurarse de que las rutas sean absolutas
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
YOLO_BASE_MODEL_PATH = os.path.join(MODELS_DIR, 'yolov8n.pt')
YOLO_PLATE_DETECTOR_PATH = os.path.join(MODELS_DIR, 'yolov8n.pt')  # Usar el modelo base por ahora
YOLO_PLATE_DETECTOR_PATH = os.path.join(os.path.dirname(__file__), '..', 'models', 'license_plate_detector.pt')

# --- Configuración de la Cámara ---
# Fuentes de video. 0 suele ser la webcam integrada.
# Puedes añadir más fuentes, como una URL de una cámara IP.
CAMERA_SOURCES = {
    "webcam": 0,
    "ip_cam_cellphone": "http://10.244.244.82:8080/video" # Ejemplo, reemplaza con la URL de tu app de cámara IP
}

# --- Clases de Objetos ---
# Clases que el modelo YOLO puede detectar. El índice corresponde al ID de la clase.
# Esto es útil si tu modelo detecta múltiples objetos y solo te interesan algunos.
# Para un modelo de placas, la clase podría ser 'license_plate' (ID 0).
# Para yolov8n.pt, las clases relevantes son: 2 (car), 3 (motorcycle), 5 (bus), 7 (truck)
YOLO_CLASSES = {
    'license_plate': 0,
    'car': 2,
    'motorcycle': 3,
    'bus': 5,
    'truck': 7
}
