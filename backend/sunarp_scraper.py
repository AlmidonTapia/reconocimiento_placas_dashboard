import requests
from bs4 import BeautifulSoup
import time
import base64
import zlib
import xml.etree.ElementTree as ET
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

class SunarpVehicularScraper:
    def consulta_mtc_por_placa(self, placa):
        """Consulta el servicio SOAP del MTC y retorna los datos del vehículo por placa (decodificados y descomprimidos)"""
        url = "https://www.mtc.gob.pe/consultaccmf/sunarp.asmx"
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": "http://tempuri.org/DatosH_VehiculoSUNARPxPlaca"
        }
        body = f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
  <soap:Body>
    <DatosH_VehiculoSUNARPxPlaca xmlns="http://tempuri.org/">
      <placaNueva>{placa}</placaNueva>
    </DatosH_VehiculoSUNARPxPlaca>
  </soap:Body>
</soap:Envelope>'''
        try:
            resp = requests.post(url, data=body, headers=headers)
            resp.raise_for_status()
            # Parsear XML SOAP
            try:
                root = ET.fromstring(resp.content)
            except Exception as parse_err:
                return {'success': False, 'error': f"Error parseando XML SOAP: {parse_err}"}
            # Buscar ArrayBytes en la respuesta SOAP
            ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'ns': 'http://tempuri.org/'}
            array_bytes = root.find('.//ns:ArrayBytes', ns)
            if array_bytes is None or not array_bytes.text:
                return {'success': False, 'error': 'No se encontró ArrayBytes en la respuesta SOAP'}
            # Decodificar base64 y descomprimir gzip
            compressed = base64.b64decode(array_bytes.text)
            decompressed = zlib.decompress(compressed, 16+zlib.MAX_WBITS)
            # El resultado es XML, parsear y retornar como string o dict
            try:
                result_xml = ET.fromstring(decompressed)
            except Exception as parse_err:
                return {'success': False, 'error': f"Error parseando XML de datos: {parse_err}"}
            data = {child.tag: child.text for child in result_xml}
            return {'success': True, 'data': data, 'xml': decompressed.decode('utf-8')}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def consulta_mtc_get_por_placa(self, placa):
        """Consulta el endpoint HTTP GET del MTC y retorna los datos del vehículo por placa (decodificados y descomprimidos)"""
        url = f"https://www.mtc.gob.pe/consultaccmf/sunarp.asmx/DatosH_VehiculoSUNARPxPlaca?placaNueva={placa}"
        try:
            resp = requests.get(url)
            resp.raise_for_status()
            # Parsear XML
            try:
                root = ET.fromstring(resp.content)
            except Exception as parse_err:
                return {'success': False, 'error': f"Error parseando XML GET: {parse_err}"}
            array_bytes = root.find('.//{http://tempuri.org/}ArrayBytes')
            if array_bytes is None or not array_bytes.text:
                return {'success': False, 'error': 'No se encontró ArrayBytes en la respuesta GET'}
            # Decodificar base64 y descomprimir gzip
            compressed = base64.b64decode(array_bytes.text)
            decompressed = zlib.decompress(compressed, 16+zlib.MAX_WBITS)
            # Intentar parsear como XML, si falla mostrar como texto
            try:
                result_xml = ET.fromstring(decompressed)
                data = {child.tag: child.text for child in result_xml}
                return {'success': True, 'data': data, 'xml': decompressed.decode('utf-8')}
            except Exception:
                texto_datos = decompressed.decode(errors='replace')
                datos_parseados = self.parsear_datos_mtc(texto_datos)
                return {'success': True, 'data': datos_parseados, 'xml': texto_datos}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def parsear_datos_mtc(self, texto_datos):
        """Parsea los datos de texto del MTC y los estructura en un diccionario"""
        resultado = {
            'vehiculos': [],
            'propietarios': []
        }
        lineas = texto_datos.strip().split('\n')
        seccion_actual = None
        for linea in lineas:
            linea = linea.strip()
            if linea == 'DATOS VEHICULO':
                seccion_actual = 'vehiculo'
                continue
            elif linea == 'DATOS PROPIETARIO':
                seccion_actual = 'propietario'
                continue
            if seccion_actual == 'vehiculo' and linea and not linea.startswith('DATOS'):
                partes = linea.rstrip(';').split(',')
                if len(partes) >= 12:
                    vehiculo = {
                        'id_registro': partes[0],
                        'placa': partes[1],
                        'placa_anterior': partes[2],
                        'codigo_estado': partes[3],
                        'categoria': partes[4],
                        'marca': partes[5],
                        'modelo': partes[6],
                        'numero_serie': partes[7],
                        'codigo_combustible': partes[8],
                        'codigo_uso': partes[9],
                        'codigo_carroceria': partes[10],
                        'fecha_primera_inscripcion': partes[11],
                        'id_ultimo_titulo': partes[12] if len(partes) > 12 else ''
                    }
                    resultado['vehiculos'].append(vehiculo)
            elif seccion_actual == 'propietario' and linea and not linea.startswith('DATOS'):
                partes = linea.rstrip(';').split(',')
                if len(partes) >= 11:
                    propietario = {
                        'id_registro': partes[0],
                        'razon_social': partes[1],
                        'apellido_paterno': partes[2],
                        'apellido_materno': partes[3],
                        'nombres': partes[4],
                        'tipo_documento': partes[5],
                        'numero_documento': partes[6].strip(),
                        'tipo_persona': partes[7],
                        'codigo_estado': partes[8],
                        'direccion': partes[9],
                        'fecha_inscripcion': partes[10],
                        'telefono': partes[11] if len(partes) > 11 else '',
                        'id_titulo': partes[12] if len(partes) > 12 else '',
                        'id_ultimo_titulo': partes[13] if len(partes) > 13 else ''
                    }
                    resultado['propietarios'].append(propietario)
        return resultado

    def generar_pdf(self, datos, filename):
        """Genera un PDF con los datos del vehículo y propietario en formato profesional"""
        import os
        
        # Asegurar que el directorio static existe
        static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static')
        if not os.path.exists(static_dir):
            os.makedirs(static_dir)
        
        # Ruta completa del archivo PDF
        pdf_path = os.path.join(static_dir, filename)
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []
        
        # Agregar título
        title = Paragraph("<b>REPORTE VEHICULAR SUNARP</b>", styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 20))
        
        vehiculos = datos.get('vehiculos', [])
        propietarios = datos.get('propietarios', [])
        
        if vehiculos:
            v = vehiculos[0]
            elements.append(Paragraph("<b>Datos del Vehículo</b>", styles['Heading2']))
            veh_table = [
                ["Placa", v.get('placa', '')],
                ["Marca", v.get('marca', '')],
                ["Modelo", v.get('modelo', '')],
                ["Categoría", v.get('categoria', '')],
                ["N° Serie/VIN", v.get('numero_serie', '')],
                ["Combustible", v.get('codigo_combustible', '')],
                ["Uso", v.get('codigo_uso', '')],
                ["Estado", v.get('codigo_estado', '')],
                ["Fecha Inscripción", v.get('fecha_primera_inscripcion', '')],
            ]
            t = Table(veh_table, hAlign='LEFT')
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
            ]))
            elements.append(t)
            elements.append(Spacer(1, 12))
            
        if propietarios:
            p = propietarios[0]
            elements.append(Paragraph("<b>Datos del Propietario</b>", styles['Heading2']))
            prop_table = [
                ["Nombre", p.get('razon_social') or f"{p.get('nombres', '')} {p.get('apellido_paterno', '')} {p.get('apellido_materno', '')}"],
                ["Tipo Documento", p.get('tipo_documento', '')],
                ["N° Documento", p.get('numero_documento', '')],
                ["Dirección", p.get('direccion', '')],
                ["Fecha Inscripción", p.get('fecha_inscripcion', '')],
            ]
            t2 = Table(prop_table, hAlign='LEFT')
            t2.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0,0), (-1,0), 8),
                ('BACKGROUND', (0,1), (-1,-1), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
            ]))
            elements.append(t2)
            
        doc.build(elements)
        with open(pdf_path, 'wb') as f:
            f.write(buffer.getvalue())
        buffer.close()
        
        return pdf_path

    def generar_html_sunarp_info(self, datos):
        """Genera HTML con diseño profesional para info de vehículo, propietario y transferencias."""
        # Diccionarios de códigos a etiquetas legibles
        CATEGORIAS = {
            'M1': 'Automóvil (hasta 8 pasajeros)',
            'M2': 'Minibús',
            'M3': 'Ómnibus',
            'N1': 'Camioneta',
            'N2': 'Camión',
            'N3': 'Camión pesado',
            'L1': 'Motocicleta',
            'L2': 'Mototaxi',
            'L3': 'Motocarga',
            'L4': 'Cuatrimoto',
        }
        COMBUSTIBLES = {
            '01': 'Gasolina', '02': 'Diesel', '03': 'GLP', '04': 'GNV', '05': 'Eléctrico', '06': 'Híbrido',
            'GASOLINA': 'Gasolina', 'DIESEL': 'Diesel', 'GLP': 'GLP', 'GNV': 'GNV', 'ELECTRICO': 'Eléctrico', 'HIBRIDO': 'Híbrido'
        }
        USOS = {
            '01': 'Transporte público', '02': 'Taxi', '03': 'Escolar', '04': 'Carga', '05': 'Turismo', '06': 'Particular',
        }
        ESTADOS = {
            '01': 'En circulación', '02': 'Retirado', '03': 'Robado', '04': 'Chatarra', '05': 'Exportado', '06': 'Baja',
        }
        TIPOS_PERSONA = {
            '01': 'Natural', '02': 'Jurídica', '06': 'Natural',
        }
        TIPOS_DOCUMENTO = {
            '01': 'DNI', '02': 'RUC', '03': 'Carnet Extranjería', '04': 'Pasaporte', '05': 'PTP', '06': 'DNI',
        }
        def label(dic, val):
            if not val or val == '-' or val == '0':
                return '-'
            return dic.get(str(val).zfill(2), dic.get(str(val), val))
        vehiculos = datos.get('vehiculos', [])
        propietarios = datos.get('propietarios', [])
        transferencias = datos.get('transferencias', []) if 'transferencias' in datos else []
        historicos = datos.get('propietarios_historicos', []) if 'propietarios_historicos' in datos else []
        
        # CSS profesional integrado
        html = '''
        <style>
        .sunarp-container { font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 0 auto; }
        .sunarp-header { background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 20px; border-radius: 12px 12px 0 0; text-align: center; }
        .sunarp-header h2 { margin: 0; font-size: 24px; font-weight: 600; }
        .sunarp-header .placa { font-size: 18px; opacity: 0.9; margin-top: 5px; }
        .sunarp-section { background: white; border: 1px solid #e5e7eb; margin-bottom: 20px; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .sunarp-section-header { background: #f8fafc; padding: 15px 20px; border-bottom: 1px solid #e5e7eb; }
        .sunarp-section-header h3 { margin: 0; color: #1f2937; font-size: 18px; font-weight: 600; display: flex; align-items: center; }
        .sunarp-section-header .icon { margin-right: 10px; font-size: 20px; }
        .sunarp-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 0; }
        .sunarp-field { padding: 12px 20px; border-bottom: 1px solid #f3f4f6; display: flex; justify-content: space-between; align-items: center; }
        .sunarp-field:last-child { border-bottom: none; }
        .sunarp-field:nth-child(even) { background: #f9fafb; }
        .sunarp-label { font-weight: 600; color: #374151; min-width: 140px; }
        .sunarp-value { color: #1f2937; text-align: right; font-weight: 500; }
        .sunarp-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; text-transform: uppercase; }
        .badge-active { background: #d1fae5; color: #065f46; }
        .badge-inactive { background: #fee2e2; color: #991b1b; }
        .sunarp-historial ul { list-style: none; padding: 0; margin: 0; }
        .sunarp-historial li { padding: 12px 20px; border-bottom: 1px solid #f3f4f6; display: flex; align-items: center; }
        .sunarp-historial li:last-child { border-bottom: none; }
        .sunarp-historial .date { font-weight: 600; color: #3b82f6; margin-right: 15px; min-width: 100px; }
        .sunarp-historial .desc { flex: 1; color: #374151; }
        .sunarp-actions { padding: 20px; background: #f8fafc; border-top: 1px solid #e5e7eb; text-align: center; }
        .download-btn { background: #059669; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-weight: 600; cursor: pointer; transition: background 0.3s; }
        .download-btn:hover { background: #047857; }
        </style>
        <div class="sunarp-container">'''
        
        if vehiculos:
            v = vehiculos[0]
            placa = v.get('placa', '-')
            html += f'''
            <div class="sunarp-header">
                <h2>🚗 Consulta Vehicular SUNARP</h2>
                <div class="placa">Placa: {placa}</div>
            </div>
            <div class="sunarp-section">
                <div class="sunarp-section-header">
                    <h3><span class="icon">🚙</span>Información del Vehículo</h3>
                </div>
                <div class="sunarp-grid">
                    <div class="sunarp-field">
                        <span class="sunarp-label">N° Placa:</span>
                        <span class="sunarp-value">{v.get('placa', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Placa Anterior:</span>
                        <span class="sunarp-value">{v.get('placa_anterior', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Marca:</span>
                        <span class="sunarp-value">{v.get('marca', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Modelo:</span>
                        <span class="sunarp-value">{v.get('modelo', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Categoría:</span>
                        <span class="sunarp-value">{label(CATEGORIAS, v.get('categoria', '-'))}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">N° Serie/VIN:</span>
                        <span class="sunarp-value">{v.get('numero_serie', '-') or v.get('vin', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Combustible:</span>
                        <span class="sunarp-value">{label(COMBUSTIBLES, v.get('codigo_combustible', '-'))}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Uso:</span>
                        <span class="sunarp-value">{label(USOS, v.get('codigo_uso', '-'))}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Estado:</span>
                        <span class="sunarp-value">
                            <span class="sunarp-badge {'badge-active' if v.get('codigo_estado') == '01' else 'badge-inactive'}">
                                {label(ESTADOS, v.get('codigo_estado', '-') or v.get('estado', '-'))}
                            </span>
                        </span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Fecha Inscripción:</span>
                        <span class="sunarp-value">{v.get('fecha_primera_inscripcion', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">ID Último Título:</span>
                        <span class="sunarp-value">{v.get('id_ultimo_titulo', '-') or '-'}</span>
                    </div>
                </div>
            </div>'''
        
        if propietarios:
            p = propietarios[0]
            # Construir nombre completo correctamente
            razon_social = p.get('razon_social', '').strip()
            if razon_social and razon_social != '-' and razon_social != '':
                nombre = razon_social
            else:
                nombres = p.get('nombres', '').strip()
                ap_paterno = p.get('apellido_paterno', '').strip()
                ap_materno = p.get('apellido_materno', '').strip()
                # Construir nombre completo eliminando espacios extras
                partes_nombre = [nombres, ap_paterno, ap_materno]
                partes_validas = [parte for parte in partes_nombre if parte and parte != '-']
                nombre = ' '.join(partes_validas) if partes_validas else '-'
            html += f'''
            <div class="sunarp-section">
                <div class="sunarp-section-header">
                    <h3><span class="icon">👤</span>Datos del Propietario</h3>
                </div>
                <div class="sunarp-grid">
                    <div class="sunarp-field">
                        <span class="sunarp-label">Nombre:</span>
                        <span class="sunarp-value">{nombre}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Tipo Persona:</span>
                        <span class="sunarp-value">{label(TIPOS_PERSONA, p.get('tipo_persona', '-'))}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Tipo Documento:</span>
                        <span class="sunarp-value">{label(TIPOS_DOCUMENTO, p.get('tipo_documento', '-'))}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">N° Documento:</span>
                        <span class="sunarp-value">{p.get('numero_documento', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Dirección:</span>
                        <span class="sunarp-value">{p.get('direccion', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">Fecha Inscripción:</span>
                        <span class="sunarp-value">{p.get('fecha_inscripcion', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">ID Título:</span>
                        <span class="sunarp-value">{p.get('id_titulo', '-') or '-'}</span>
                    </div>
                    <div class="sunarp-field">
                        <span class="sunarp-label">ID Último Título:</span>
                        <span class="sunarp-value">{p.get('id_ultimo_titulo', '-') or '-'}</span>
                    </div>
                </div>
            </div>'''
        
        if transferencias or historicos:
            html += '''
            <div class="sunarp-section">
                <div class="sunarp-section-header">
                    <h3><span class="icon">📋</span>Historial de Transferencias</h3>
                </div>
                <div class="sunarp-historial">
                    <ul>'''
            for t in transferencias:
                fecha = t.get('fecha', '-')
                desc = t.get('descripcion', '-')
                idt = t.get('id_titulo', '-')
                html += f'<li><span class="date">{fecha}</span><span class="desc">{desc} (ID: {idt})</span></li>'
            if historicos:
                html += '<li><span class="date">Histórico</span><span class="desc"><strong>Propietarios Anteriores:</strong></span></li>'
                for h in historicos:
                    nombre = h.get('nombre', '-')
                    doc = h.get('documento', '-')
                    fecha = h.get('fecha', '-')
                    idt = h.get('id_titulo', '-')
                    html += f'<li><span class="date">{fecha}</span><span class="desc">• {nombre} {doc} (ID:{idt})</span></li>'
            html += '''
                    </ul>
                </div>
            </div>'''
        
        # Agregar botón de descarga PDF
        placa_clean = vehiculos[0].get('placa', 'vehiculo').replace('-', '') if vehiculos else 'vehiculo'
        html += f'''
        <div class="sunarp-actions">
            <button class="download-btn" onclick="descargarPDF('{placa_clean}')">
                📄 Descargar Reporte PDF
            </button>
        </div>
        </div>'''
        
        return html

# Función auxiliar para usar desde app.py
def consult_vehicle_sunarp(plate_number, pdf_filename=None):
    """
    Función auxiliar para consultar un vehículo en SUNARP
    Args:
        plate_number (str): Número de placa
        pdf_filename (str): Si se indica, genera un PDF con los datos
    Returns:
        dict: Resultado de la consulta
    """
    scraper = SunarpVehicularScraper()
    resultado = scraper.consulta_mtc_get_por_placa(plate_number)
    if resultado['success'] and 'data' in resultado:
        datos = resultado['data']
        html = scraper.generar_html_sunarp_info(datos)
        pdf = None
        pdf_path = None
        if pdf_filename:
            pdf_path = scraper.generar_pdf(datos, pdf_filename)
            pdf = pdf_filename
        return {'success': True, 'datos': datos, 'html': html, 'pdf': pdf, 'pdf_path': pdf_path}
    else:
        return {'success': False, 'error': resultado.get('error', 'Error desconocido')}
