from flask import Flask, request, redirect, url_for, session, render_template, Blueprint, g
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import logging
import sys

PRODUCTION = os.environ.get('PRODUCTION', '').lower() in ['1', 'true', 'yes']

# Configure logging
if PRODUCTION:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
else:
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

# Get logger for this module
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

# Configure Flask's logger to use the same handler
app.logger.handlers = []
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG if not PRODUCTION else logging.INFO)

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
        logger.info("Database initialized successfully")

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

        logger.info(f"Signup attempt for username: {username}")

        if access_code != ACCESS_CODE:
            error = 'Invalid access code.'
            logger.warning(f"Invalid access code attempted for username: {username}")
        elif not username or not password:
            error = 'Username and password required.'
            logger.warning("Signup attempt with missing username or password")
        else:
            db = get_db()
            try:
                db.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                           (username, generate_password_hash(password)))
                db.commit()
                logger.info(f"User successfully registered: {username}")
                return redirect(url_for('file_transfer.login'))
            except sqlite3.IntegrityError:
                error = 'Username already exists.'
                logger.warning(f"Signup attempt with existing username: {username}")
    return render_template('signup.html', error=error)

@file_transfer.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        logger.info(f"Login attempt for username: {username}")

        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user[2], password):
            session["logged_in"] = True
            session["username"] = username
            logger.info(f"Successful login for user: {username}")
            return redirect(url_for('file_transfer.hello'))
        else:
            error = "Invalid credentials."
            logger.warning(f"Failed login attempt for username: {username}")
    return render_template('login.html', error=error)

@file_transfer.route('/logout')
def logout():
    username = session.get("username", "Unknown")
    session.pop("logged_in", None)
    session.pop("username", None)
    logger.info(f"User logged out: {username}")
    return redirect(url_for('file_transfer.login'))

@file_transfer.route('/')
def hello():
    if not session.get("logged_in"):
        logger.debug("Unauthorized access attempt to main page")
        return redirect(url_for('file_transfer.login'))
    username = session.get('username', 'User')
    logger.debug(f"Main page accessed by user: {username}")
    return f"Hello, {username}!"

with app.app_context():
    init_db()
app.register_blueprint(file_transfer)

if __name__ == "__main__":
    app.run(debug=not PRODUCTION)
