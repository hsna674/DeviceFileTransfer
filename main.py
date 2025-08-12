from flask import Flask, request, redirect, url_for, session, render_template_string, Blueprint
from werkzeug.middleware.proxy_fix import ProxyFix
import os

app = Flask(__name__)
app.secret_key = os.urandom(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

# file_transfer = Blueprint('file_transfer', __name__, url_prefix='/file-transfer')

USERNAME = "admin"
PASSWORD = "S3cureP@ssw0rd!2025"

login_form = '''
<!doctype html>
<title>Login</title>
<h2>Login</h2>
<form method="post">
  <input type="text" name="username" placeholder="Username" required><br>
  <input type="password" name="password" placeholder="Password" required><br>
  <input type="submit" value="Login">
  {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
</form>
'''

@app.route('/login', methods=['GET', 'POST'])
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
    return render_template_string(login_form, error=error)

@app.route('/logout')
def logout():
    session.pop("logged_in", None)
    return redirect(url_for('file_transfer.login'))

@app.route('/')
def hello():
    if not session.get("logged_in"):
        return redirect(url_for('file_transfer.login'))
    return "Hello, World 2! (You are logged in)"

# app.register_blueprint(file_transfer)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=1010)