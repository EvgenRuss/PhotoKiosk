import os
from flask import Flask, render_template, jsonify, request
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Папка для загрузки фотографий
UPLOAD_FOLDER = os.path.join('static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Допустимые расширения файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 1. Главная страница киоска (для клиентов)
@app.route('/')
def index():
    return render_template('index.html')

# 2. Панель управления (для сотрудников)
@app.route('/admin')
def admin():
    return render_template('admin.html')

# 3. API: Получение списка всех фото
@app.route('/api/photos', methods=['GET'])
def get_photos():
    photos = []
    if os.path.exists(UPLOAD_FOLDER):
        files = os.listdir(UPLOAD_FOLDER)
        for filename in files:
            if allowed_file(filename):
                photos.append({
                    'id': filename,
                    'filename': filename,
                    'url': f'/static/uploads/{filename}'
                })
    return jsonify(photos)

# 4. API: Загрузка новых фото (из админки)
@app.route('/api/upload', methods=['POST'])
def upload_photos():
    if 'files' not in request.files:
        return jsonify({'error': 'Файлы не найдены'}), 400
    
    files = request.files.getlist('files')
    uploaded = []
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # Чтобы избежать перезаписи одинаковых имен
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            uploaded.append(filename)
            
    return jsonify({'success': True, 'uploaded': uploaded})

# 5. API: Удаление фото (из админки)
@app.route('/api/photos/<filename>', methods=['DELETE'])
def delete_photo(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))
    if os.path.exists(filepath):
        os.remove(filepath)
        return jsonify({'success': True})
    return jsonify({'error': 'Файл не найден'}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
