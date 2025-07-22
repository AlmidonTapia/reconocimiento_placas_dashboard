# backend/database.py
# Módulo para gestionar todas las interacciones con la base de datos SQLite.

import sqlite3
import os
from datetime import datetime, timedelta
from config import DATABASE_PATH

# Cache para deduplicación en memoria (mejora rendimiento)
plate_cache = {}
CACHE_CLEANUP_INTERVAL = 60  # Limpiar cache cada 60 segundos

def cleanup_cache():
    """Limpia entradas del cache que han expirado."""
    current_time = datetime.now()
    expired_keys = []
    
    for key, timestamp in plate_cache.items():
        if (current_time - timestamp).seconds > 60:  # Limpiar entradas de más de 60 segundos
            expired_keys.append(key)
    
    for key in expired_keys:
        del plate_cache[key]

def clear_dedup_cache():
    """Limpia completamente el cache de deduplicación."""
    global plate_cache
    plate_cache = {}
    print("Cache de deduplicación limpiado completamente.")

def get_cache_stats():
    """Obtiene estadísticas del cache de deduplicación."""
    cleanup_cache()  # Limpiar entradas expiradas primero
    return {
        "cache_size": len(plate_cache),
        "cached_plates": list(plate_cache.keys())
    }

def init_db():
    """
    Inicializa la base de datos y crea la tabla 'plates' si no existe.
    Esta función es segura de ejecutar múltiples veces.
    """
    print(f"Inicializando base de datos en: {DATABASE_PATH}")
    # Asegurarse de que el directorio 'data' exista
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Crear la tabla para almacenar las matrículas reconocidas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_text TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                camera_source TEXT,
                image_path TEXT,
                image_base64 TEXT
            )
        ''')
        
        # Agregar columna image_base64 si no existe (para compatibilidad con BD existentes)
        try:
            cursor.execute('ALTER TABLE plates ADD COLUMN image_base64 TEXT')
            print("Columna image_base64 agregada a la tabla plates")
        except sqlite3.OperationalError:
            # La columna ya existe
            pass
        
        conn.commit()
        print("Tabla 'plates' creada o ya existente.")
    except sqlite3.Error as e:
        print(f"Error al inicializar la base de datos: {e}")
    finally:
        if conn:
            conn.close()

def add_plate_reading(plate_text, camera_source="unknown", image_path=None, image_base64=None, dedup_seconds=30):
    """
    Añade un nuevo registro de matrícula a la base de datos con deduplicación.
    No registra la misma placa si ya fue detectada en los últimos N segundos.

    Args:
        plate_text (str): El texto de la matrícula reconocida.
        camera_source (str): La fuente de la cámara que capturó la imagen.
        image_path (str, optional): La ruta a la imagen guardada de la matrícula.
        image_base64 (str, optional): La imagen en formato base64.
        dedup_seconds (int): Segundos para evitar duplicados (por defecto 30).
    
    Returns:
        bool: True si la inserción fue exitosa, False si es duplicado o error.
    """
    if not plate_text or not plate_text.strip():
        print("Intento de añadir matrícula vacía. Ignorando.")
        return False
    
    # Limpiar cache periódicamente
    cleanup_cache()
    
    current_time = datetime.now()
    cache_key = f"{plate_text}_{camera_source}"
    
    # Verificar primero en el cache (más rápido)
    if cache_key in plate_cache:
        time_diff = (current_time - plate_cache[cache_key]).total_seconds()
        if time_diff < dedup_seconds:
            print(f"Placa {plate_text} ya registrada recientemente (cache). Tiempo transcurrido: {time_diff:.1f}s")
            return False
        
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Verificar duplicados en BD solo si no está en cache
        if cache_key not in plate_cache:
            limit_time = current_time - timedelta(seconds=dedup_seconds)
            limit_timestamp = limit_time.strftime("%Y-%m-%d %H:%M:%S")
            
            cursor.execute('''
                SELECT COUNT(*) FROM plates 
                WHERE plate_text = ? 
                AND camera_source = ? 
                AND timestamp > ?
            ''', (plate_text, camera_source, limit_timestamp))
            
            recent_count = cursor.fetchone()[0]
            
            if recent_count > 0:
                print(f"Placa {plate_text} ya registrada recientemente en BD. Ignorando duplicado.")
                # Actualizar cache para evitar futuras consultas
                plate_cache[cache_key] = current_time
                return False
        
        # Insertar el nuevo registro
        cursor.execute('''
            INSERT INTO plates (plate_text, timestamp, camera_source, image_path, image_base64)
            VALUES (?, ?, ?, ?, ?)
        ''', (plate_text, timestamp, camera_source, image_path, image_base64))
        
        conn.commit()
        
        # Actualizar cache con la nueva entrada
        plate_cache[cache_key] = current_time
        
        print(f"Matrícula añadida a la BD: {plate_text} (cámara: {camera_source})")
        return True
        
    except sqlite3.Error as e:
        print(f"Error al añadir matrícula a la BD: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_latest_plates(limit=10):
    """
    Obtiene las últimas matrículas registradas en la base de datos.
    
    Args:
        limit (int): El número máximo de registros a obtener.
        
    Returns:
        list: Una lista de tuplas con los datos de las matrículas.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT plate_text, timestamp, camera_source, image_base64 FROM plates ORDER BY timestamp DESC LIMIT ?", (limit,))
        records = cursor.fetchall()
        return records
    except sqlite3.Error as e:
        print(f"Error al obtener matrículas de la BD: {e}")
        return []
    finally:
        if conn:
            conn.close()

def clear_all_plates():
    """
    Elimina todos los registros de matrículas de la base de datos.
    
    Returns:
        bool: True si la limpieza fue exitosa, False en caso contrario.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM plates")
        conn.commit()
        
        # Reiniciar el contador de autoincremento
        cursor.execute("DELETE FROM sqlite_sequence WHERE name='plates'")
        conn.commit()
        
        print("Base de datos limpiada exitosamente")
        return True
    except sqlite3.Error as e:
        print(f"Error al limpiar la base de datos: {e}")
        return False
    finally:
        if conn:
            conn.close()

def get_total_plates():
    """
    Obtiene el número total de matrículas registradas en la base de datos.
    
    Returns:
        int: El número total de registros.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM plates")
        count = cursor.fetchone()[0]
        return count
    except sqlite3.Error as e:
        print(f"Error al contar matrículas: {e}")
        return 0
    finally:
        if conn:
            conn.close()

def delete_plate(plate_text, timestamp=None):
    """
    Elimina una matrícula específica de la base de datos.
    
    Args:
        plate_text (str): Texto de la matrícula a eliminar.
        timestamp (str, optional): Timestamp específico para mayor precisión.
        
    Returns:
        bool: True si se eliminó correctamente, False si hubo error.
    """
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        if timestamp:
            # Eliminar registro específico por placa y timestamp
            cursor.execute("DELETE FROM plates WHERE plate_text = ? AND timestamp = ?", 
                         (plate_text, timestamp))
        else:
            # Eliminar el registro más reciente de esa placa
            cursor.execute("""DELETE FROM plates WHERE id = (
                SELECT id FROM plates WHERE plate_text = ? 
                ORDER BY timestamp DESC LIMIT 1
            )""", (plate_text,))
        
        rows_affected = cursor.rowcount
        conn.commit()
        
        if rows_affected > 0:
            print(f"Placa {plate_text} eliminada exitosamente")
            return True
        else:
            print(f"No se encontró la placa {plate_text} para eliminar")
            return False
            
    except sqlite3.Error as e:
        print(f"Error al eliminar la placa: {e}")
        return False
    finally:
        if conn:
            conn.close()

# Esto permite ejecutar 'python backend/database.py' para crear la BD la primera vez.
if __name__ == '__main__':
    print("Ejecutando inicializador de base de datos...")
    init_db()
    print("Proceso de inicialización de BD completado.")
