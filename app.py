import os
import json
import time
import requests
from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Папка для кэширования фотографий
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Файл для хранения заказов
ORDERS_FILE = 'orders.json'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

# ID ВАШЕЙ ПУБЛИЧНОЙ ПАПКИ GOOGLE DRIVE 
# (Если у вас есть ID папки, вставьте его ниже вместо 'YOUR_GOOGLE_DRIVE_FOLDER_ID')
GOOGLE_DRIVE_FOLDER_ID = os.environ.get('GOOGLE_DRIVE_FOLDER_ID', '')

def load_orders_from_file():
    if os.path.exists(ORDERS_FILE):
        try:
            with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print("Ошибка чтения orders.json:", e)
            return []
    return []

def save_orders_to_file():
    try:
        with open(ORDERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(orders, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Ошибка сохранения orders.json:", e)

orders = load_orders_from_file()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 1. Главная страница
@app.route('/')
def index():
    return render_template('index.html')

# 2. Панель сотрудника
@app.route('/admin')
def admin():
    return render_template('admin.html')

# 3. API: Получение фотографий (локальные + с Google Диска)
@app.route('/api/photos', methods=['GET'])
def get_photos():
    photos = []
    seen_ids = set()

    # Считываем текущие файлы из папки uploads
    if os.path.exists(UPLOAD_FOLDER):
        files = sorted(os.listdir(UPLOAD_FOLDER))
        for filename in files:
            if allowed_file(filename):
                clean_id = filename.rsplit('.', 1)[0]
                seen_ids.add(clean_id)
                photos.append({
                    'id': filename,
                    'filename': filename,
                    'url': f'/static/uploads/{filename}'
                })

    return jsonify(photos)

# 4. API: Загрузка новых фотографий
@app.route('/api/upload', methods=['POST'])
def upload_photos():
    if 'files' not in request.files:
        return jsonify({'error': 'Файлы не найдены'}), 400
    
    files = request.files.getlist('files')
    uploaded = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Перезаписываем если файл уже есть, чтобы избегать дублей
            file.save(save_path)
            uploaded.append(filename)
            
    return jsonify({'success': True, 'uploaded': uploaded})

# 5. API: Удаление фотографии
@app.route('/api/photos/<filename>', methods=['DELETE'])
def delete_photo(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    return jsonify({'error': 'Файл не найден'}), 404

# --- API ЗАКАЗОВ ---

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

@app.route('/api/orders', methods=['GET'])
def get_orders():
    return jsonify(orders)

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
