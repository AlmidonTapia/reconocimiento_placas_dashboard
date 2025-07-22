# backend/camera_manager.py
# Gestiona la captura de video desde diferentes fuentes.

import cv2
from config import CAMERA_SOURCES
import time

class CameraManager:
    def __init__(self):
        self.caps = {}  # Diccionario para almacenar objetos VideoCapture
        self.active_source = None
        self.current_cap = None
        print("CameraManager inicializado.")
        print(f"Fuentes de cámara disponibles: {list(CAMERA_SOURCES.keys())}")

    def select_source(self, source_name: str):
        """
        Selecciona una fuente de video y la activa.
        
        Args:
            source_name (str): El nombre de la fuente (ej. 'webcam', 'ip_cam_cellphone').
        """
        if source_name not in CAMERA_SOURCES:
            print(f"Error: La fuente de cámara '{source_name}' no está definida en config.py")
            return False

        if self.active_source == source_name and self.current_cap and self.current_cap.isOpened():
            print(f"La fuente '{source_name}' ya está activa.")
            return True

        self.release_current_source() # Libera la cámara anterior si hay una

        source_path = CAMERA_SOURCES[source_name]
        print(f"Intentando abrir la fuente de cámara: '{source_name}' en la ruta: {source_path}")
        
        # Intentar abrir la nueva fuente de video
        cap = cv2.VideoCapture(source_path)
        
        # Para cámaras IP, a veces necesitan un momento para conectar
        if isinstance(source_path, str) and source_path.startswith('http'):
            time.sleep(1)

        if not cap.isOpened():
            print(f"Error: No se pudo abrir la fuente de video '{source_name}'.")
            self.current_cap = None
            self.active_source = None
            return False
        
        print(f"Fuente de cámara '{source_name}' seleccionada y abierta exitosamente.")
        self.current_cap = cap
        self.active_source = source_name
        return True

    def get_frame(self):
        """
        Captura un solo frame de la fuente de video activa.
        
        Returns:
            tuple: (bool, np.ndarray) - Un booleano que indica éxito y el frame capturado.
        """
        if self.current_cap and self.current_cap.isOpened():
            success, frame = self.current_cap.read()
            if not success:
                print(f"Advertencia: No se pudo leer el frame de '{self.active_source}'. Intentando reconectar.")
                # Intentar reabrir la fuente en caso de desconexión
                self.select_source(self.active_source)
                return False, None
            
            # Reducir resolución para procesamiento más rápido
            height, width = frame.shape[:2]
            if width > 800:
                scale = 800 / width
                new_width = 800
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)
            
            return True, frame
        
        # print("No hay una fuente de cámara activa o no está abierta.")
        return False, None

    def release_current_source(self):
        """Libera el objeto de captura de video actual."""
        if self.current_cap:
            print(f"Liberando la fuente de cámara: {self.active_source}")
            self.current_cap.release()
            self.current_cap = None
            self.active_source = None

    def __del__(self):
        """Asegurarse de que todas las cámaras se liberen al destruir el objeto."""
        self.release_current_source()
