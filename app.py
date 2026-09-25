from flask import Flask, render_template, jsonify
import requests

app = Flask(__name__)

# Настройки Google Drive
GOOGLE_API_KEY = "AIzaSyD_ICUO8RTY9yU36F2QHeC1axWhFqqGuZo"
FOLDER_ID = "134MgPoYH4TQui5qOpfqjgj7CqlTndDxP"

def get_google_drive_photos():
    """Получает актуальный список файлов из папки на Google Диске"""
    url = f"https://www.googleapis.com/drive/v3/files?q='{FOLDER_ID}'+in+parents+and+trashed=false&fields=files(id,name,mimeType)&key={GOOGLE_API_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()
        files = data.get('files', [])
        
        photos = []
        for file in files:
            # Фильтруем только изображения
            if file.get('mimeType', '').startswith('image/'):
                photos.append({
                    'id': file['id'],
                    'filename': file['name'],
                    'name': file['name'],
                    'url': f"https://drive.google.com/thumbnail?id={file['id']}&sz=w1000"
                })
        return photos
    except Exception as e:
        print(f"Ошибка получения файлов с Google Drive: {e}")
        return []

@app.route('/')
def index():
    photos = get_google_drive_photos()
    return render_template('index.html', photos=photos)

@app.route('/api/photos')
def api_photos():
    """API эндпоинт для автообновления галереи на клиенте"""
    photos = get_google_drive_photos()
    response = jsonify(photos)
    # Разрешаем фоновые запросы без блокировки CORS
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/employee')
def employee():
    photos = get_google_drive_photos()
    return render_template('employee.html', photos=photos)

if __name__ == '__main__':
    app.run(debug=True)
