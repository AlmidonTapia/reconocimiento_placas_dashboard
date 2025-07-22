# Dashboard de Reconocimiento de Placas

Sistema automatizado de reconocimiento de placas vehiculares con integración SUNARP y interfaz web en tiempo real.

## 🚀 Características

- **Reconocimiento OCR**: Detección automática de placas vehiculares usando EasyOCR con aceleración GPU
- **Interfaz Web en Tiempo Real**: Dashboard interactivo con WebSockets para actualizaciones en vivo
- **Sistema Anti-Duplicados**: Previene el registro múltiple de la misma placa en un período configurable
- **Integración SUNARP**: Consulta automática de información vehicular en el registro de SUNARP
- **Base de Datos SQLite**: Almacenamiento persistente con operaciones CRUD
- **Múltiples Fuentes de Video**: Soporte para webcam y cámaras IP
- **Captura de Imágenes**: Almacenamiento automático de imágenes de placas detectadas

## 🛠️ Tecnologías

- **Backend**: Python 3.10, Flask, SocketIO, SQLite
- **Frontend**: HTML5, CSS3, JavaScript (Vanilla), WebSockets
- **OCR**: EasyOCR con CUDA 11.8
- **Web Scraping**: Requests, BeautifulSoup4
- **Procesamiento**: OpenCV, NumPy

## 📋 Requisitos

- Python 3.10+
- CUDA 11.8+ (para aceleración GPU)
- NVIDIA RTX 3050 6GB o superior (recomendado)
- Windows 10/11

## 🔧 Instalación

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd reconocimiento_placas_dashboard
```

2. **Crear entorno virtual**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Descargar modelo YOLOv8** (opcional)
```bash
python download_model.py
```

5. **Ejecutar la aplicación**
```bash
python backend/app.py
```

6. **Abrir navegador**
```
http://localhost:5000
```

## 🎮 Uso

### Panel de Control

- **Control de Video**: Iniciar/detener stream de cámara
- **Fuente de Cámara**: Seleccionar entre webcam o cámara IP
- **Base de Datos**: Limpiar registros y actualizar contadores
- **Anti-Duplicados**: Configurar tiempo de deduplicación (5-120 segundos)

### Funciones Principales

1. **Detección Automática**: Las placas se detectan automáticamente en tiempo real
2. **Visualización**: Ver imágenes capturadas de cada placa
3. **Consulta SUNARP**: Información vehicular oficial con un clic
4. **Gestión de Datos**: Eliminar registros individuales o limpiar base de datos

## ⚙️ Configuración

### Sistema Anti-Duplicados

El sistema incluye un mecanismo avanzado de deduplicación:

- **Cache en memoria**: Para consultas rápidas
- **Configuración flexible**: 5-120 segundos de ventana
- **Limpieza automática**: Cache se limpia periódicamente
- **Estadísticas en tiempo real**: Monitoreo del estado del cache

### Configuración de Cámaras

Editar `backend/config.py`:

```python
CAMERA_SOURCES = {
    "webcam": 0,
    "ip_cam_cellphone": "http://192.168.1.100:8080/video"
}
```

## 📁 Estructura del Proyecto

```
reconocimiento_placas_dashboard/
├── backend/
│   ├── app.py              # Aplicación Flask principal
│   ├── database.py         # Gestión de base de datos con anti-duplicados
│   ├── camera_manager.py   # Gestión de fuentes de video
│   ├── plate_detector.py   # Lógica de detección OCR
│   ├── sunarp_scraper.py   # Integración con SUNARP
│   └── config.py          # Configuraciones
├── templates/
│   └── dashboard.html     # Interfaz web con controles anti-duplicados
├── data/
│   ├── captured/          # Imágenes capturadas
│   └── screenshots/       # Capturas de SUNARP
├── models/               # Modelos de ML
├── static/              # Archivos estáticos
└── requirements.txt     # Dependencias
```

## 🔄 API Endpoints

### Placas
- `GET /api/plates` - Listar placas
- `GET /api/plates/count` - Contador total
- `POST /api/plates/delete` - Eliminar placa
- `POST /api/plates/clear` - Limpiar todas

### SUNARP
- `POST /api/sunarp/consult` - Consultar vehículo

### Configuración
- `GET/POST /api/settings/deduplication` - Configurar anti-duplicados
- `POST /api/cache/clear` - Limpiar cache
- `GET /api/cache/stats` - Estadísticas del cache

## 🎯 Características del Sistema Anti-Duplicados

### Funcionamiento

1. **Cache en Memoria**: Almacena temporalmente las placas detectadas
2. **Verificación de Base de Datos**: Consulta registros recientes antes de insertar
3. **Ventana Temporal Configurable**: 5-120 segundos de período de deduplicación
4. **Limpieza Automática**: El cache se limpia cada 60 segundos
5. **Estadísticas en Tiempo Real**: Monitoreo del estado del sistema

### Beneficios

- ✅ Elimina registros duplicados del mismo vehículo
- ✅ Mejora la precisión de los datos
- ✅ Reduce el ruido en la base de datos
- ✅ Configurable según necesidades específicas
- ✅ Alto rendimiento con cache en memoria

## 🐛 Solución de Problemas

### Error de CUDA
```bash
# Verificar instalación de CUDA
nvidia-smi
```

### Error de cámara
- Verificar permisos de cámara en Windows
- Comprobar que la cámara no esté siendo usada por otra aplicación

### Error de SUNARP
- El servicio puede tener restricciones temporales
- Se muestran datos simulados como ejemplo

## 📝 Changelog

### v1.0.0 (21/07/2025)
- ✅ Sistema anti-duplicados implementado
- ✅ Cache en memoria para mejor rendimiento
- ✅ Configuración flexible de deduplicación
- ✅ Interfaz mejorada con controles de configuración
- ✅ Estadísticas en tiempo real del cache
- ✅ Integración SUNARP sin dependencias de navegador
- ✅ Dashboard profesional con design system

## 👥 Contribuir

1. Fork el proyecto
2. Crear rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

## 🙏 Agradecimientos

- YOLOv8 para detección de objetos
- EasyOCR para reconocimiento de texto
- OpenCV para procesamiento de imágenes
- Flask y SocketIO para el backend web
- SUNARP por la información vehicular

---

**Desarrollado con ❤️ para la automatización del reconocimiento vehicular**
