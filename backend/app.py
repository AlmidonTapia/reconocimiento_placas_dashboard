# backend/app.py
# Aplicación principal de Flask que une todo.

import os
import cv2
import base64
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
import threading
import time

# Importaciones de nuestros módulos
from camera_manager import CameraManager
from plate_detector import detect_and_process_plates
from database import init_db, add_plate_reading, get_latest_plates, clear_all_plates, get_total_plates, delete_plate, clear_dedup_cache, get_cache_stats
from config import CAMERA_SOURCES
from sunarp_scraper import consult_vehicle_sunarp

# --- Configuración de la Aplicación ---
app = Flask(__name__, template_folder='../templates', static_folder='../static')
CORS(app) # Permite peticiones desde otros orígenes (nuestro frontend)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Variables Globales ---
camera_manager = CameraManager()
processing_active = False
processing_thread = None
active_camera_source = "webcam" # Fuente por defecto
deduplication_time = 30  # Tiempo en segundos para evitar duplicados (configurable)

# --- Inicialización ---
@app.before_request
def first_request_setup():
    # Esta función se ejecuta antes de la primera petición.
    # Usamos un 'hack' para que se ejecute solo una vez.
    if not app.config.get('DB_INITIALIZED'):
        print("Realizando configuración inicial (Base de Datos)...")
        init_db()
        app.config['DB_INITIALIZED'] = True

# --- Rutas HTTP (API REST) ---
@app.route('/')
def index():
    """Sirve la página principal del dashboard."""
    # Aunque el frontend sea React, esta ruta puede servir como punto de entrada
    # o para pruebas.
    return render_template('dashboard.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    """Devuelve el estado actual del backend."""
    return jsonify({
        'processing_active': processing_active,
        'active_camera': camera_manager.active_source,
        'available_cameras': list(CAMERA_SOURCES.keys())
    })

@app.route('/api/plates', methods=['GET'])
def get_plates():
    """Obtiene los últimos registros de matrículas de la BD."""
    limit = request.args.get('limit', 15, type=int)
    plates = get_latest_plates(limit)
    # Convertir las tuplas de la BD a una lista de diccionarios
    plate_data = [{"plate": p[0], "timestamp": p[1], "camera": p[2], "image_base64": p[3] if len(p) > 3 else None} for p in plates]
    return jsonify(plate_data)

@app.route('/api/plates/clear', methods=['POST'])
def clear_plates():
    """Limpia todos los registros de matrículas de la base de datos."""
    try:
        if clear_all_plates():
            # Emitir evento WebSocket para actualizar contadores en tiempo real
            socketio.emit('plates_cleared', {'count': 0})
            socketio.emit('database_updated', {'total_plates': 0, 'action': 'clear'})
            return jsonify({"success": True, "message": "Base de datos limpiada exitosamente"})
        else:
            return jsonify({"success": False, "message": "Error al limpiar la base de datos"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/api/plates/count', methods=['GET'])
def get_plates_count():
    """Obtiene el número total de matrículas registradas."""
    try:
        count = get_total_plates()
        return jsonify({"count": count})
    except Exception as e:
        return jsonify({"error": f"Error al contar registros: {str(e)}"}), 500

@app.route('/api/plates/delete', methods=['POST'])
def delete_plate_endpoint():
    """Elimina una matrícula específica de la base de datos."""
    try:
        data = request.get_json()
        plate_text = data.get('plate')
        timestamp = data.get('timestamp')
        
        if not plate_text:
            return jsonify({"success": False, "message": "Placa requerida"}), 400
        
        if delete_plate(plate_text, timestamp):
            # Obtener el nuevo conteo y emitir evento WebSocket
            new_count = get_total_plates()
            socketio.emit('database_updated', {'total_plates': new_count, 'action': 'delete', 'plate': plate_text})
            return jsonify({"success": True, "message": "Placa eliminada exitosamente"})
        else:
            return jsonify({"success": False, "message": "No se encontró la placa para eliminar"}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/api/sunarp/consult', methods=['POST'])
def consult_sunarp_endpoint():
    """Consulta información vehicular en SUNARP."""
    try:
        data = request.get_json()
        plate_text = data.get('plate')
        
        if not plate_text:
            return jsonify({"success": False, "message": "Placa requerida"}), 400
        
        # Realizar consulta SUNARP
        result = consult_vehicle_sunarp(plate_text)
        
        # Si hay screenshot en el resultado, incluirlo en la respuesta
        if result.get('success') and 'screenshot' in result:
            return jsonify({
                'success': result['success'],
                'data': result['data'],
                'screenshot': result['screenshot']
            })
        else:
            return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Error en consulta SUNARP: {str(e)}"}), 500

@app.route('/api/settings/deduplication', methods=['GET', 'POST'])
def deduplication_settings():
    """Obtiene o configura el tiempo de deduplicación."""
    global deduplication_time
    
    if request.method == 'GET':
        return jsonify({
            "deduplication_time": deduplication_time,
            "message": f"Tiempo actual de deduplicación: {deduplication_time} segundos"
        })
    
    elif request.method == 'POST':
        try:
            data = request.get_json()
            new_time = data.get('deduplication_time')
            
            if not isinstance(new_time, int) or new_time < 5 or new_time > 300:
                return jsonify({
                    "success": False, 
                    "message": "El tiempo debe ser un número entero entre 5 y 300 segundos"
                }), 400
            
            deduplication_time = new_time
            return jsonify({
                "success": True,
                "deduplication_time": deduplication_time,
                "message": f"Tiempo de deduplicación actualizado a {deduplication_time} segundos"
            })
            
        except Exception as e:
            return jsonify({
                "success": False, 
                "message": f"Error al actualizar configuración: {str(e)}"
            }), 500

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Limpia el cache de deduplicación."""
    try:
        clear_dedup_cache()
        return jsonify({
            "success": True,
            "message": "Cache de deduplicación limpiado exitosamente"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error al limpiar cache: {str(e)}"
        }), 500

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """Obtiene estadísticas del cache de deduplicación."""
    try:
        stats = get_cache_stats()
        return jsonify({
            "success": True,
            "cache_size": stats["cache_size"],
            "cached_plates": stats["cached_plates"]
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error al obtener estadísticas: {str(e)}"
        }), 500

# --- Lógica de Procesamiento de Video (SocketIO) ---

def video_processing_loop():
    """
    Bucle principal que captura frames, los procesa y emite los resultados.
    Se ejecuta en un hilo separado para no bloquear el servidor.
    """
    global processing_active, active_camera_source
    print("Iniciando bucle de procesamiento de video...")
    
    while processing_active:
        # Seleccionar la fuente de cámara si no está activa
        if camera_manager.active_source != active_camera_source:
            if not camera_manager.select_source(active_camera_source):
                print(f"No se pudo cambiar a la cámara {active_camera_source}. Deteniendo procesamiento.")
                processing_active = False
                break
        
        # Obtener frame
        success, frame = camera_manager.get_frame()
        if not success:
            time.sleep(0.5) # Esperar un poco si falla la captura
            continue

        # Procesar el frame para detectar matrículas
        processed_frame, detected_plates = detect_and_process_plates(frame, active_camera_source)

        # Si se detectaron matrículas, guardarlas en la BD y notificar al frontend
        if detected_plates:
            newly_added_plates = []
            for plate in detected_plates:
                # La función add_plate_reading ahora incluye deduplicación automática
                image_base64 = plate.get('image_base64', None)
                if add_plate_reading(plate['plate_text'], active_camera_source, plate['image_path'], image_base64, deduplication_time):
                    newly_added_plates.append({
                        "plate": plate['plate_text'],
                        "timestamp": "Ahora", # El timestamp real está en la BD
                        "camera": active_camera_source,
                        "image": image_base64
                    })
            
            if newly_added_plates:
                # Obtener el conteo actualizado
                new_total = get_total_plates()
                socketio.emit('new_plate', {'plates': newly_added_plates})
                socketio.emit('database_updated', {'total_plates': new_total, 'action': 'add'})

        # Codificar el frame procesado para enviarlo al frontend con calidad reducida
        encode_params = [cv2.IMWRITE_JPEG_QUALITY, 75]  # Reducir calidad JPEG para mejor rendimiento
        _, buffer = cv2.imencode('.jpg', processed_frame, encode_params)
        frame_b64 = base64.b64encode(buffer).decode('utf-8')
        
        # Emitir el frame al cliente
        socketio.emit('video_frame', {'image': frame_b64})
        
        socketio.sleep(0.033) # Ajustado a ~30 FPS

    camera_manager.release_current_source()
    print("Bucle de procesamiento de video detenido.")
    socketio.emit('status_update', {'processing_active': False, 'active_camera': None})


@socketio.on('connect')
def handle_connect():
    """Se ejecuta cuando un cliente se conecta."""
    print('Cliente conectado al WebSocket.')
    # Enviar estado actual al nuevo cliente
    socketio.emit('status_update', {
        'processing_active': processing_active, 
        'active_camera': camera_manager.active_source
    }, room=request.sid)


@socketio.on('disconnect')
def handle_disconnect():
    """Se ejecuta cuando un cliente se desconecta."""
    print('Cliente desconectado del WebSocket.')


@socketio.on('control_stream')
def handle_control_stream(data):
    """Maneja los comandos para iniciar/detener el stream."""
    global processing_active, processing_thread, active_camera_source
    
    command = data.get('action')
    print(f"Comando recibido: {command}")

    if command == 'start':
        if not processing_active:
            processing_active = True
            active_camera_source = data.get('camera_source', 'webcam')
            
            # Iniciar el hilo de procesamiento si no está vivo
            if processing_thread is None or not processing_thread.is_alive():
                processing_thread = socketio.start_background_task(target=video_processing_loop)
            
            socketio.emit('status_update', {'processing_active': True, 'active_camera': active_camera_source})
            print(f"Procesamiento iniciado con la cámara: {active_camera_source}")
        else:
            print("El procesamiento ya estaba activo.")

    elif command == 'stop':
        if processing_active:
            processing_active = False
            # El bucle se detendrá por sí mismo
            print("Señal de detención enviada al bucle de procesamiento.")
        else:
            print("El procesamiento ya estaba detenido.")

    elif command == 'switch_camera':
        new_source = data.get('camera_source')
        if new_source and new_source != active_camera_source:
            print(f"Cambiando cámara a: {new_source}")
            active_camera_source = new_source
            # El bucle de procesamiento detectará el cambio y cambiará la fuente
            socketio.emit('status_update', {'active_camera': new_source})


# --- Punto de Entrada Principal ---
if __name__ == '__main__':
    print("Iniciando servidor Flask-SocketIO...")
    # Usamos eventlet como servidor de producción para un mejor rendimiento de WebSockets
    socketio.run(app, 
                host='127.0.0.1',  # Localhost
                port=5000, 
                debug=True,
                allow_unsafe_werkzeug=True)  # Permitir el debugger en desarrollo
