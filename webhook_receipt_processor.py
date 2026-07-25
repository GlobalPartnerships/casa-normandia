#!/usr/bin/env python3
"""
Webhook para procesar recibos de pago de Casa Normandía
Recibe imágenes, extrae datos con Google Cloud Vision API y los guarda en Google Sheets
"""

import os
import re
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import google.cloud.vision
from google.cloud import vision
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Extensiones permitidas
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

# Configuración
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/cloud-platform']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', 'your_spreadsheet_id_here')
SHEET_NAME = 'Recibos'  # Nombre de la hoja donde se guardarán los datos

def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_credentials():
    """Obtiene las credenciales de Google Cloud"""
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'credentials.json')
    return Credentials.from_service_account_file(creds_path, scopes=SCOPES)

def extract_text_from_image(image_path):
    """Extrae texto de una imagen usando Google Cloud Vision API"""
    try:
        creds = get_credentials()
        client = vision.ImageAnnotatorClient(credentials=creds)
        
        with open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)
        response = client.text_detection(image=image)
        
        if response.error.message:
            logger.error(f"Error en Vision API: {response.error.message}")
            return None
            
        texts = response.text_annotations
        if texts:
            return texts[0].description
        return None
        
    except Exception as e:
        logger.error(f"Error extrayendo texto: {str(e)}")
        return None

def parse_receipt_data(text):
    """Parsea el texto del recibo para extraer datos estructurados"""
    if not text:
        return None
    
    data = {
        'fecha': None,
        'proveedor': None,
        'total': None,
        'iva': None
    }
    
    # Patrones regex para extraer datos
    patterns = {
        'fecha': [
            r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',
            r'\b(\d{2,4}[-/]\d{1,2}[-/]\d{1,2})\b',
            r'Fecha[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'Date[:\s]*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})'
        ],
        'total': [
            r'Total[:\s]*\$?\s*(\d+(?:\.\d{2})?)',
            r'TOTAL[:\s]*\$?\s*(\d+(?:\.\d{2})?)',
            r'Importe[:\s]*\$?\s*(\d+(?:\.\d{2})?)',
            r'\$?\s*(\d+(?:\.\d{2})?)\s*(?:TOTAL|Total|Importe)'
        ],
        'iva': [
            r'IVA[:\s]*\$?\s*(\d+(?:\.\d{2})?)',
            r'I\.V\.A\.[:\s]*\$?\s*(\d+(?:\.\d{2})?)',
            r'VAT[:\s]*\$?\s*(\d+(?:\.\d{2})?)',
            r'Impuesto[:\s]*\$?\s*(\d+(?:\.\d{2})?)'
        ]
    }
    
    # Extraer fecha
    for pattern in patterns['fecha']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1)
            try:
                # Intentar diferentes formatos de fecha
                for fmt in ['%d-%m-%Y', '%d/%m/%Y', '%Y-%m-%d', '%Y/%m/%d', '%d-%m-%y', '%d/%m/%y']:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        data['fecha'] = parsed_date.strftime('%Y-%m-%d')
                        break
                    except ValueError:
                        continue
                if data['fecha']:
                    break
            except:
                continue
    
    # Extraer total
    for pattern in patterns['total']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['total'] = float(match.group(1))
            break
    
    # Extraer IVA
    for pattern in patterns['iva']:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['iva'] = float(match.group(1))
            break
    
    # Extraer proveedor (primera línea o palabras clave)
    lines = text.split('\n')
    for line in lines[:5]:  # Revisar primeras 5 líneas
        line = line.strip()
        if line and len(line) > 3 and not re.search(r'\d', line):
            # Excluir líneas que parecen direcciones o códigos
            if not re.search(r'[A-Z]{2,}\s*\d{4,}', line) and not re.search(r'^\d+$', line):
                data['proveedor'] = line[:50]  # Limitar a 50 caracteres
                break
    
    return data

def save_to_google_sheets(data):
    """Guarda los datos extraídos en Google Sheets"""
    try:
        creds = get_credentials()
        
        # Conectar a Google Sheets
        gc = gspread.authorize(creds)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        # Obtener o crear la hoja
        try:
            worksheet = spreadsheet.worksheet(SHEET_NAME)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=SHEET_NAME, rows="100", cols="20")
            # Agregar encabezados
            headers = ['Fecha', 'Proveedor', 'Total', 'IVA', 'Fecha de Procesamiento', 'Estado']
            worksheet.append_row(headers)
        
        # Preparar fila para insertar
        row = [
            data.get('fecha', ''),
            data.get('proveedor', ''),
            data.get('total', ''),
            data.get('iva', ''),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Procesado'
        ]
        
        # Insertar nueva fila
        worksheet.append_row(row)
        logger.info(f"Datos guardados en Google Sheets: {row}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error guardando en Google Sheets: {str(e)}")
        return False

@app.route('/webhook/receipt', methods=['POST'])
def process_receipt():
    """Endpoint principal del webhook para procesar recibos"""
    try:
        # Verificar si hay archivo en la solicitud
        if 'image' not in request.files:
            return jsonify({'error': 'No se encontró archivo de imagen'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'Nombre de archivo vacío'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Tipo de archivo no permitido'}), 400
        
        # Crear directorio de uploads si no existe
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Guardar archivo temporalmente
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"Archivo guardado: {filepath}")
        
        # Extraer texto de la imagen
        text = extract_text_from_image(filepath)
        if not text:
            os.remove(filepath)
            return jsonify({'error': 'No se pudo extraer texto de la imagen'}), 400
        
        logger.info(f"Texto extraído: {text[:200]}...")
        
        # Parsear datos del recibo
        receipt_data = parse_receipt_data(text)
        if not receipt_data:
            os.remove(filepath)
            return jsonify({'error': 'No se pudieron extraer datos del recibo'}), 400
        
        logger.info(f"Datos parseados: {receipt_data}")
        
        # Guardar en Google Sheets
        if save_to_google_sheets(receipt_data):
            # Limpiar archivo temporal
            os.remove(filepath)
            
            return jsonify({
                'success': True,
                'message': 'Recibo procesado exitosamente',
                'data': receipt_data
            }), 200
        else:
            os.remove(filepath)
            return jsonify({'error': 'Error guardando datos en Google Sheets'}), 500
            
    except Exception as e:
        logger.error(f"Error procesando recibo: {str(e)}")
        return jsonify({'error': f'Error interno: {str(e)}'}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint para verificar el estado del servicio"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/', methods=['GET'])
def index():
    """Endpoint de información"""
    return jsonify({
        'service': 'Casa Normandía Receipt Processor',
        'version': '1.0.0',
        'endpoints': {
            'POST /webhook/receipt': 'Procesar recibo de pago',
            'GET /health': 'Verificar estado del servicio'
        }
    })

if __name__ == '__main__':
    # Crear directorio de uploads
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Iniciar servidor
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
