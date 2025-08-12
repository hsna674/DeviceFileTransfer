from flask import Flask, request, redirect, url_for, session, render_template, Blueprint, g
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import timedelta

PRODUCTION = os.environ.get('PRODUCTION', '').lower() in ['1', 'true', 'yes']
app = Flask(__name__)

SECRET_KEY = os.environ.get('SECRET_KEY', '2d810d71054ae86a971f31b1dcecaeb9f3ed6c0069a91cdf6f')
app.secret_key = SECRET_KEY

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_SECURE'] = PRODUCTION
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

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
    return f"Hello, {session.get('username', 'User')}!"

with app.app_context():
    init_db()
app.register_blueprint(file_transfer)

if __name__ == "__main__":
    app.run(debug=not PRODUCTION)
