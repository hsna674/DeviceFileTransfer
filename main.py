from flask import Flask, request, redirect, url_for, session, render_template, Blueprint, g, flash, send_from_directory
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import timedelta, datetime
import glob

PRODUCTION = os.environ.get('PRODUCTION', '').lower() in ['1', 'true', 'yes']
app = Flask(__name__)

SECRET_KEY = os.environ.get('SECRET_KEY', '2d810d71054ae86a971f31b1dcecaeb9f3ed6c0069a91cdf6f')
app.secret_key = SECRET_KEY

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = PRODUCTION
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'zip', 'rar', 'mp4', 'mp3', 'avi', 'mov'}

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_list():
    """Get list of uploaded files, sorted by modification time (newest first)"""
    files = []
    if os.path.exists(UPLOAD_FOLDER):
        for filepath in glob.glob(os.path.join(UPLOAD_FOLDER, '*')):
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    'name': os.path.basename(filepath),
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })

    # Sort by modification time (newest first) and keep only last 10
    files.sort(key=lambda x: x['modified'], reverse=True)
    return files[:10]

def cleanup_old_files():
    """Remove files beyond the 10 most recent"""
    files = []
    if os.path.exists(UPLOAD_FOLDER):
        for filepath in glob.glob(os.path.join(UPLOAD_FOLDER, '*')):
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append({
                    'path': filepath,
                    'modified': datetime.fromtimestamp(stat.st_mtime)
                })

    # Sort by modification time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)

    # Remove files beyond the 10 most recent
    for file_info in files[10:]:
        try:
            os.remove(file_info['path'])
        except OSError:
            pass

app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

DATABASE = os.path.join(os.path.dirname(__file__), 'users.db')
ACCESS_CODE = '786020321065335'

# Database helpers
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )''')
        db.commit()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

if PRODUCTION:
    url_prefix = "/file-transfer"
else:
    url_prefix = ""

file_transfer = Blueprint('file_transfer', __name__, url_prefix=url_prefix)

@file_transfer.route('/signup', methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        access_code = request.form.get('access_code')
        if access_code != ACCESS_CODE:
            error = 'Invalid access code.'
        elif not username or not password:
            error = 'Username and password required.'
        else:
            db = get_db()
            try:
                db.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                           (username, generate_password_hash(password)))
                db.commit()
                return redirect(url_for('file_transfer.login'))
            except sqlite3.IntegrityError:
                error = 'Username already exists.'
    return render_template('signup.html', error=error)

@file_transfer.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user[2], password):
            session.permanent = True
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for('file_transfer.hello'))
        else:
            error = "Invalid credentials."
    return render_template('login.html', error=error)

@file_transfer.route('/logout')
def logout():
    session.pop("logged_in", None)
    session.pop("username", None)
    return redirect(url_for('file_transfer.login'))

@file_transfer.route('/')
def hello():
    if not session.get("logged_in"):
        return redirect(url_for('file_transfer.login'))
    return redirect(url_for('file_transfer.dashboard'))

@file_transfer.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for('file_transfer.login'))

    files = get_file_list()

    if request.method == 'POST':
        # Handle file upload
        uploaded_file = request.files.get('file')
        if uploaded_file and uploaded_file.filename and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            # Handle duplicate filenames by adding timestamp
            if os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], filename)):
                name, ext = os.path.splitext(filename)
                timestamp = datetime.now().strftime("_%Y%m%d_%H%M%S")
                filename = f"{name}{timestamp}{ext}"

            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            uploaded_file.save(file_path)
            flash('File uploaded successfully.', 'success')
            cleanup_old_files()  # Clean up old files after upload
            return redirect(url_for('file_transfer.dashboard'))  # Redirect to avoid resubmission
        else:
            flash('Invalid file type or no file selected.', 'error')

    return render_template('dashboard.html', files=files)

@file_transfer.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@file_transfer.route('/delete/<filename>', methods=['POST'])
def delete_file(filename):
    if not session.get("logged_in"):
        return redirect(url_for('file_transfer.login'))

    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('File deleted successfully.', 'success')
        else:
            flash('File not found.', 'error')
    except OSError:
        flash('Error deleting file.', 'error')

    return redirect(url_for('file_transfer.dashboard'))

with app.app_context():
    init_db()
app.register_blueprint(file_transfer)

if __name__ == "__main__":
    app.run(debug=not PRODUCTION)
