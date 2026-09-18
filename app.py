#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Producción - Versión Simple y Estable
"""

from flask import Flask, request, redirect, url_for, session, flash, render_template_string
from functools import wraps
import os
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_secreta_produccion_2026")

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    import psycopg2
    import psycopg2.extras
    USE_POSTGRES = True
else:
    import sqlite3
    from pathlib import Path
    DB_PATH = Path(__file__).parent / "produccion.db"
    USE_POSTGRES = False


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id SERIAL PRIMARY KEY,
                usuario TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nombre TEXT,
                area TEXT,
                activo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS programas (
                id SERIAL PRIMARY KEY,
                numero_programa TEXT NOT NULL UNIQUE,
                estado TEXT NOT NULL DEFAULT 'Pendiente Trazo',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT
            );
        """)
    else:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nombre TEXT,
                area TEXT,
                activo INTEGER DEFAULT 1
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS programas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_programa TEXT NOT NULL UNIQUE,
                estado TEXT NOT NULL DEFAULT 'Pendiente Trazo',
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT
            )
        """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM usuarios")
    row = cur.fetchone()
    count = row[0] if not isinstance(row, dict) else list(row.values())[0]
    if count == 0:
        def hp(p): return hashlib.sha256(p.encode()).hexdigest()
        users = [
            ("admin", hp("admin123"), "Administrador", "Admin"),
            ("corte", hp("corte123"), "Área de Corte", "Corte"),
            ("gerente", hp("gerente123"), "Gerente", "Gerente"),
        ]
        for u in users:
            if USE_POSTGRES:
                cur.execute("INSERT INTO usuarios (usuario, password_hash, nombre, area) VALUES (%s,%s,%s,%s)", u)
            else:
                cur.execute("INSERT INTO usuarios (usuario, password_hash, nombre, area) VALUES (?,?,?,?)", u)
        conn.commit()
    conn.close()


def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


LOGIN_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - Producción</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', sans-serif; background: linear-gradient(135deg, #0f2744, #1a3a5c); min-height: 100vh; display: flex; align-items: center; justify-content: center; }
        .card { background: white; border-radius: 16px; padding: 2.5rem; width: 100%; max-width: 380px; box-shadow: 0 20px 50px rgba(0,0,0,0.3); }
        h1 { text-align: center; color: #0f2744; margin-bottom: 0.3rem; }
        p { text-align: center; color: #64748b; margin-bottom: 1.5rem; font-size: 0.9rem; }
        label { display: block; font-weight: 600; margin-bottom: 0.3rem; font-size: 0.9rem; }
        input { width: 100%; padding: 0.7rem; border: 1px solid #cbd5e1; border-radius: 8px; margin-bottom: 1rem; font-size: 1rem; }
        button { width: 100%; padding: 0.75rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; }
        button:hover { background: #2563eb; }
        .error { background: #fee2e2; color: #991b1b; padding: 0.7rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.9rem; }
        .hint { margin-top: 1.2rem; font-size: 0.8rem; color: #64748b; background: #f8fafc; padding: 0.8rem; border-radius: 8px; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Sistema de Producción</h1>
        <p>Inicia sesión</p>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <label>Usuario</label>
            <input type="text" name="usuario" required autofocus>
            <label>Contraseña</label>
            <input type="password" name="password" required>
            <button type="submit">Entrar</button>
        </form>
        <div class="hint">
            <b>Usuarios de prueba:</b><br>
            admin / admin123<br>
            corte / corte123<br>
            gerente / gerente123
        </div>
    </div>
</body>
</html>
"""

HOME_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Inicio - Producción</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: 'Segoe UI', sans-serif; background: #f1f5f9; }
        .nav { background: #0f2744; color: white; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; }
        .nav a { color: white; text-decoration: none; margin-left: 1rem; }
        .container { max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
        .card { background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 1px 6px rgba(0,0,0,0.08); margin-bottom: 1.5rem; }
        h1 { color: #0f2744; margin-bottom: 0.5rem; }
        .success { background: #d1fae5; color: #065f46; padding: 0.8rem; border-radius: 8px; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="nav">
        <strong>Sistema de Producción</strong>
        <div>
            <span>{{ nombre }} ({{ area }})</span>
            <a href="/logout">Salir</a>
        </div>
    </div>
    <div class="container">
        {% if mensaje %}<div class="success">{{ mensaje }}</div>{% endif %}
        <div class="card">
            <h1>¡Bienvenido!</h1>
            <p>El sistema ya está funcionando correctamente.</p>
            <p style="margin-top:1rem;color:#64748b;">Próximo paso: iremos agregando el módulo de Programas de Corte, Trazo, Órdenes, etc.</p>
        </div>
        <div class="card">
            <h2>Estado del sistema</h2>
            <p>✅ Login funcionando</p>
            <p>✅ Base de datos conectada</p>
            <p>✅ Usuarios activos</p>
        </div>
    </div>
</body>
</html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        try:
            conn = get_db()
            if USE_POSTGRES:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cur.execute("SELECT * FROM usuarios WHERE usuario = %s AND activo = 1", (usuario,))
            else:
                cur = conn.cursor()
                cur.execute("SELECT * FROM usuarios WHERE usuario = ? AND activo = 1", (usuario,))
            user = cur.fetchone()
            conn.close()
            if user:
                if isinstance(user, dict):
                    phash = user["password_hash"]
                    uid = user["id"]
                    nombre = user["nombre"]
                    area = user["area"]
                else:
                    phash = user[2]
                    uid = user[0]
                    nombre = user[3]
                    area = user[4]
                if phash == hash_password(password):
                    session["user_id"] = uid
                    session["nombre"] = nombre
                    session["area"] = area
                    return redirect(url_for("index"))
            error = "Usuario o contraseña incorrectos"
        except Exception as e:
            error = f"Error de conexión: {e}"
    return render_template_string(LOGIN_HTML, error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    return render_template_string(HOME_HTML,
                                  nombre=session.get("nombre"),
                                  area=session.get("area"),
                                  mensaje="Sesión iniciada correctamente")


# Inicializar DB
try:
    init_db()
    print("✓ Base de datos lista")
except Exception as e:
    print(f"Error init_db: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
