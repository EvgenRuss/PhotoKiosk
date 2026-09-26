import os
import json
import time
import requests
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# --- НАСТРОЙКИ GOOGLE DRIVE ---
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '134MgPoYH4TQui5qOpfqjgj7CqlTndDxP')
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyCJc7uk_QLHkzOk9OXKZycdybrIp5KKtZI')

ORDERS_FILE = 'orders.json'

def load_orders_from_file():
    """Загрузка сохраненных заказов из файла"""
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print("Ошибка чтения orders.json:", e)
            return []
    return []

def save_orders_to_file():
    """Сохранение всех заказов в файл"""
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка сохранения orders.json:", e)

orders = load_orders_from_file()

# 1. Главная страница киоска
@app.route('/')
def index():
    return render_template('index.html')

# 2. Панель сотрудника
@app.route('/admin')
def admin():
    return render_template('admin.html')

# 3. API: Получение актуального списка фотографий СТРОГО ИЗ GOOGLE DRIVE
@app.route('/api/photos', methods=['GET'])
def get_photos():
    if not GOOGLE_DRIVE_FOLDER_ID or not GOOGLE_API_KEY:
        return jsonify({'error': 'Не указан GOOGLE_DRIVE_FOLDER_ID или GOOGLE_API_KEY'}), 500

    # Запрос к Google Drive API v3 (получаем только не удаленные изображения)
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        'q': f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and trashed = false and mimeType contains 'image/'",
        'fields': 'files(id, name)',
        'key': GOOGLE_API_KEY,
        'pageSize': 1000
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if 'error' in data:
            print("Ошибка Google Drive API:", data['error'])
            return jsonify({'error': data['error'].get('message', 'Drive API Error')}), 400

        files = data.get('files', [])
        photos = []

        for f in files:
            # Прямая ссылка для отображения фотографии напрямую из Google Диска
            img_url = f"https://lh3.googleusercontent.com/d/{f['id']}"
            photos.append({
                'id': f['id'],
                'filename': f['name'],
                'url': img_url
            })

        return jsonify(photos)

    except Exception as e:
        print("Ошибка обращения к Google Drive:", e)
        return jsonify([]), 500

# --- API ДЛЯ РАБОТЫ С ЗАКАЗАМИ ---

# 4. Создание нового заказа
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    if not data or 'items' not in data:
        return jsonify({'error': 'Некорректные данные'}), 400
    
    order_id = f"ORD-{int(time.time() * 1000) % 1000000}"
    time_str = time.strftime('%H:%M:%S')
    
    new_order = {
        'id': order_id,
        'time': time_str,
        'total': data.get('total', 0),
        'status': 'new',
        'statusText': 'Новый',
        'items': data.get('items', [])
    }
    
    orders.insert(0, new_order)
    save_orders_to_file()
    return jsonify({'success': True, 'order': new_order})

# 5. Получение списка всех заказов
@app.route('/api/orders', methods=['GET'])
def get_orders():
    return jsonify(orders)

# 6. Обновление статуса заказа
@app.route('/api/orders/<order_id>/status', methods=['POST'])
def update_order_status(order_id):
    data = request.json
    new_status = data.get('status')
    
    for ord in orders:
        if ord['id'] == order_id:
            ord['status'] = new_status
            if new_status == 'process':
                ord['statusText'] = 'Печатается'
            elif new_status == 'done':
                ord['statusText'] = 'Выдан'
            
            save_orders_to_file()
            return jsonify({'success': True, 'order': ord})
            
    return jsonify({'error': 'Заказ не найден'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
