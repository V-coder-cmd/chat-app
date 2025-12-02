from flask import Flask, render_template, request, redirect, session, jsonify
from db import get_connection
import hashlib
import os
from datetime import datetime
from db import get_connection

app = Flask(__name__)
app.secret_key = "CHAVE_SECRETA_AQUI"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# -----------------------------------
# Função para criptografar senhas
# -----------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# -----------------------------------
# Página inicial (login)
# -----------------------------------
@app.route("/")
def login_page():
    if "username" in session:
        return redirect("/chat")
    return render_template("login.html")


# -----------------------------------
# Rota de login
# -----------------------------------
@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = hash_password(request.form["password"])

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s",
                (username, password))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user:
        session["username"] = username
        return redirect("/chat")
    else:
        return "⚠️ Usuário ou senha incorretos!"


# -----------------------------------
# Página de cadastro
# -----------------------------------
@app.route("/cadastro")
def cadastro_page():
    return render_template("register.html")


# -----------------------------------
# Rota de cadastro
# -----------------------------------
@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"]
    password = hash_password(request.form["password"])

    conn = get_connection()
    cur = conn.cursor()

    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, password))
        conn.commit()
    except:
        return "⚠️ Nome de usuário já existe!"
    finally:
        cur.close()
        conn.close()

    return redirect("/")


# -----------------------------------
# Página do chat (somente logado)
# -----------------------------------
@app.route("/chat")
def chat():
    if "username" not in session:
        return redirect("/")
    return render_template("chat.html")


# -----------------------------------
# AJAX: buscar mensagens
# -----------------------------------
@app.route("/messages")
def messages():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT * FROM messages ORDER BY timestamp ASC")
    msgs = cur.fetchall()

    cur.close()
    conn.close()
    return jsonify(msgs)


# -----------------------------------
# Enviar mensagem
# -----------------------------------
@app.route("/send", methods=["POST"])
def send():
    if "username" not in session:
        return "NOT LOGGED", 403

    user = session["username"]
    msg = request.form.get("message", "").strip()

    # Caso venha imagem
    image_path = None

    if "file" in request.files:
        file = request.files["file"]
        if file.filename != "":
            # Garante nome único
            filename = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
            filepath = os.path.join(UPLOAD_FOLDER, filename)

            # Salva arquivo
            file.save(filepath)

            image_path = filename

    # Conecta ao banco
    conn = get_connection()
    cur = conn.cursor()

    sql = """
        INSERT INTO messages (username, message, image)
        VALUES (%s, %s, %s)
    """

    cur.execute(sql, (user, msg if msg else None, image_path))
    conn.commit()

    cur.close()
    conn.close()

    return "OK"


typing_user = ""  # variável global para armazenar quem está digitando


@app.route("/typing", methods=["POST"])
def typing():
    global typing_user

    username = session.get("username")
    status = request.form.get("status")  # typing / stop

    if status == "typing":
        typing_user = username
    else:
        typing_user = ""

    return "OK"

@app.route("/clear_chat", methods=["POST"])
def clear_chat():
    if "username" not in session:
        return {"status": "not_logged"}

    username = session["username"]
    print("LIMPANDO MENSAGENS DO USUÁRIO:", username)

    cx = get_connection()
    cur = cx.cursor()

    sql = "DELETE FROM messages WHERE username = %s"
    cur.execute(sql, (username,))
    cx.commit()

    print("TOTAL DE LINHAS APAGADAS:", cur.rowcount)

    cur.close()
    cx.close()

    return {"status": "ok"}





@app.route("/get_typing")
def get_typing():
    return jsonify({"typing": typing_user})


# -----------------------------------
# Logout
# -----------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)