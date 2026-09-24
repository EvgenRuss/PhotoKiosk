import os
import sqlite3
import time
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Пути для загрузки файлов и БД
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
DB_PATH = os.path.join(app.root_path, 'photo_kiosk.db')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Инициализация базы данных SQLite
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Таблица фотографий
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS photos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица заказов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            items_json TEXT NOT NULL,
            total INTEGER NOT NULL,
            status TEXT DEFAULT 'ПРИНЯТ',
            created_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Типы сувениров
MERCH_TYPES = [
    {"id": "photo_10x15", "name": "Печать фото 10x15", "price": 150},
    {"id": "magnet", "name": "Магнит на холодильник", "price": 350},
    {"id": "mug", "name": "Кружка с фото", "price": 600},
    {"id": "photobook", "name": "Фотобук / Альбом", "price": 1200}
]

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/api/gallery', methods=['GET'])
def get_gallery():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, url FROM photos ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    
    photos = [{"id": r[0], "url": r[1]} for r in rows]
    return jsonify({"photos": photos, "merch_types": MERCH_TYPES})

@app.route('/api/upload-photos', methods=['POST'])
def upload_photos():
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'Файлы не выбраны'}), 400

    uploaded_count = 0
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_filename = f"{int(time.time()*1000)}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(filepath)

            photo_url = f"/static/uploads/{unique_filename}"
            cursor.execute("INSERT INTO photos (url) VALUES (?)", (photo_url,))
            uploaded_count += 1

    conn.commit()
    conn.close()
    return jsonify({'message': f'Загружено {uploaded_count} фото!', 'count': uploaded_count})

@app.route('/api/create-order', methods=['POST'])
def create_order():
    import json
    data = request.json
    items_json = json.dumps(data.get('items', []), ensure_ascii=False)
    total = data.get('total', 0)
    created_at = time.strftime("%H:%M:%S")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (items_json, total, status, created_at) VALUES (?, ?, 'ПРИНЯТ', ?)",
        (items_json, total, created_at)
    )
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({'success': True, 'order_id': order_id})

@app.route('/api/orders', methods=['GET'])
def get_orders():
    import json
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, items_json, total, status, created_at FROM orders ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()

    orders = []
    for r in rows:
        orders.append({
            'id': r[0],
            'items': json.loads(r[1]),
            'total': r[2],
            'status': r[3],
            'time': r[4]
        })
    return jsonify(orders)

@app.route('/api/orders/<int:order_id>/complete', methods=['POST'])
def complete_order(order_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE orders SET status = 'ВЫДАН' WHERE id = ?", (order_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)