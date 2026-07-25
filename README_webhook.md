# Webhook de Procesamiento de Recibos - Casa Normandía

Sistema automatizado para procesar recibos de pago usando inteligencia artificial y guardar los datos en Google Sheets.

## 🚀 Funcionalidades

- **Recepción de imágenes**: Acepta imágenes de recibos a través de un webhook HTTP
- **OCR con Google Cloud Vision**: Extrae texto automáticamente de las imágenes
- **Parseo inteligente**: Identifica y extrae datos clave (Fecha, Proveedor, Total, IVA)
- **Almacenamiento automático**: Guarda los datos en Google Sheets para contabilidad
- **Validación y errores**: Manejo robusto de errores y validación de datos

## 📋 Requisitos

- Python 3.8+
- Cuenta de Google Cloud con acceso a Vision API y Sheets API
- Google Sheets para almacenamiento de datos

## ⚙️ Configuración

### 1. Configurar Google Cloud

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita las siguientes APIs:
   - Cloud Vision API
   - Google Sheets API
4. Crea una cuenta de servicio:
   - Ve a "IAM & Admin" → "Service Accounts"
   - Crea una nueva cuenta de servicio
   - Descarga la clave JSON y renómbrala a `credentials.json`
5. Otorga permisos:
   - Para Google Sheets: Comparte el spreadsheet con el email de la cuenta de servicio

### 2. Configurar Google Sheets

1. Crea un nuevo Google Sheets
2. Copia el ID del URL (ej: `docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit`)
3. Comparte el spreadsheet con el email de tu cuenta de servicio

### 3. Instalación y Configuración Local

```bash
# Clonar o navegar al directorio del proyecto
cd casa-normandia

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración
cp .env.example .env

# Editar .env con tus configuraciones
```

### 4. Variables de Entorno

Edita el archivo `.env`:

```env
# ID del Spreadsheet de Google Sheets
SPREADSHEET_ID=tu_spreadsheet_id_aqui

# Ruta al archivo de credenciales de Google Cloud
GOOGLE_APPLICATION_CREDENTIALS=credentials.json

# Puerto del servidor (opcional)
PORT=5000
```

## 🏃‍♂️ Ejecución

### Modo Desarrollo

```bash
python webhook_receipt_processor.py
```

### Modo Producción (con gunicorn)

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 webhook_receipt_processor:app
```

## 📡 Uso del Webhook

### Endpoint Principal

**POST** `http://localhost:5000/webhook/receipt`

#### Formato de la Petición

```bash
curl -X POST \
  http://localhost:5000/webhook/receipt \
  -H 'Content-Type: multipart/form-data' \
  -F 'image=@ruta/a/tu/recibo.jpg'
```

#### Respuesta Exitosa

```json
{
  "success": true,
  "message": "Recibo procesado exitosamente",
  "data": {
    "fecha": "2024-01-15",
    "proveedor": "Supermercado Central",
    "total": 1250.50,
    "iva": 250.10
  }
}
```

#### Respuesta de Error

```json
{
  "error": "No se pudo extraer texto de la imagen"
}
```

### Endpoint de Health Check

**GET** `http://localhost:5000/health`

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

## 📊 Estructura de Datos en Google Sheets

El sistema crea automáticamente una hoja llamada "Recibos" con la siguiente estructura:

| Columna | Descripción |
|---------|-------------|
| Fecha | Fecha del recibo extraída |
| Proveedor | Nombre del proveedor/emisor |
| Total | Monto total del recibo |
| IVA | Monto del IVA (si se detecta) |
| Fecha de Procesamiento | Timestamp del procesamiento |
| Estado | Estado del procesamiento |

## 🔍 Formatos de Imagen Soportados

- PNG
- JPG/JPEG
- GIF
- BMP
- TIFF
- WebP

Tamaño máximo: 16MB

## 🛠️ Personalización

### Modificar Patrones de Extracción

Puedes ajustar los patrones regex en el archivo `webhook_receipt_processor.py`:

```python
patterns = {
    'fecha': [
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b',
        # Agrega más patrones aquí
    ],
    'total': [
        r'Total[:\s]*\$?\s*(\d+(?:\.\d{2})?)',
        # Agrega más patrones aquí
    ]
}
```

### Agregar Nuevos Campos

1. Modifica el diccionario `data` en `parse_receipt_data()`
2. Agrega patrones regex para el nuevo campo
3. Actualiza la estructura de Google Sheets

## 🔐 Seguridad

- Validación de tipos de archivo
- Límite de tamaño de archivo (16MB)
- Sanitización de nombres de archivo
- Manejo seguro de credenciales

## 🐛 Troubleshooting

### Errores Comunes

1. **"No se encontró archivo de imagen"**
   - Asegúrate de enviar el archivo con el nombre de campo `image`

2. **"Error en Vision API"**
   - Verifica que las credenciales sean correctas
   - Confirma que la Vision API esté habilitada

3. **"Error guardando en Google Sheets"**
   - Verifica el SPREADSHEET_ID
   - Confirma que la cuenta de servicio tenga permisos

### Logs

El sistema genera logs detallados. Puedes cambiar el nivel de logging:

```python
logging.basicConfig(level=logging.DEBUG)  # Para desarrollo
```

## 📈 Monitoreo

### Health Check

Usa el endpoint `/health` para verificar que el servicio esté funcionando correctamente.

### Métricas Sugeridas

- Tiempo de procesamiento por imagen
- Tasa de éxito/fracaso
- Tipos de errores más comunes

## 🚀 Despliegue

### Docker (Opcional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "webhook_receipt_processor.py"]
```

### Cloud Run / Heroku

El webhook es compatible con plataformas serverless. Solo asegúrate de:

1. Incluir el archivo `credentials.json` en variables de entorno
2. Configurar el puerto según la plataforma

## 📞 Soporte

Para problemas o preguntas:

1. Revisa los logs del sistema
2. Verifica la configuración de APIs de Google Cloud
3. Confirma los permisos del Google Sheets

---

**Desarrollado para Casa Normandía - Automatización de Contabilidad**
