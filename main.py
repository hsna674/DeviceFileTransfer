from flask import Flask, request, redirect, url_for, session, render_template, Blueprint
from werkzeug.middleware.proxy_fix import ProxyFix
import os

PRODUCTION = os.environ.get('PRODUCTION', '').lower() in ['1', 'true', 'yes']
app = Flask(__name__)
app.secret_key = os.urandom(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

if PRODUCTION:
    print("Using production mode")
    url_prefix = "/file-transfer"
    USERNAME = "admin"
    PASSWORD = "S3cureP@ssw0rd!2025"
else:
    print("Using development mode")
    url_prefix = ""
    USERNAME = "admin"
    PASSWORD = "admin"

file_transfer = Blueprint('file_transfer', __name__, url_prefix=url_prefix)

@file_transfer.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == USERNAME and password == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for('file_transfer.hello'))
        else:
            error = "Invalid credentials."
    return render_template('login.html', error=error)

@file_transfer.route('/logout')
def logout():
    session.pop("logged_in", None)
    return redirect(url_for('file_transfer.login'))

@file_transfer.route('/')
def hello():
    if not session.get("logged_in"):
        return redirect(url_for('file_transfer.login'))
    return "Hello, World 2! (You are logged in)"

app.register_blueprint(file_transfer)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=1010)