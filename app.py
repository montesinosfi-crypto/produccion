#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Producción v3
Flujo: Programa de Corte → Trazo → Corte (asigna Orden) → Asignación → Habilitado → Maquila → Terminado
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime, timedelta
import os
import hashlib
import json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "produccion_v3_secreto_2026")

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


def dict_cursor(conn):
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()


def ph():
    return "%s" if USE_POSTGRES else "?"


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
                creado_por TEXT,
                observaciones TEXT
            );
            CREATE TABLE IF NOT EXISTS puntos (
                id SERIAL PRIMARY KEY,
                programa_id INTEGER NOT NULL REFERENCES programas(id) ON DELETE CASCADE,
                punto TEXT NOT NULL,
                modelo TEXT NOT NULL,
                color TEXT NOT NULL,
                tallas_json TEXT NOT NULL DEFAULT '{}',
                orden_id INTEGER,
                estado TEXT DEFAULT 'Pendiente'
            );
            CREATE TABLE IF NOT EXISTS trazo (
                id SERIAL PRIMARY KEY,
                programa_id INTEGER NOT NULL UNIQUE REFERENCES programas(id) ON DELETE CASCADE,
                confirmado INTEGER DEFAULT 0,
                usuario TEXT,
                fecha_confirmacion TEXT,
                observaciones TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ordenes (
                id SERIAL PRIMARY KEY,
                numero_orden TEXT NOT NULL UNIQUE,
                punto_id INTEGER REFERENCES puntos(id),
                programa_id INTEGER,
                estado_actual TEXT NOT NULL DEFAULT 'Corte',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT
            );
            CREATE TABLE IF NOT EXISTS corte (
                id SERIAL PRIMARY KEY,
                orden_id INTEGER NOT NULL UNIQUE REFERENCES ordenes(id) ON DELETE CASCADE,
                fecha_inicio TEXT,
                fecha_final TEXT,
                fecha_entrega_tampografia TEXT,
                tampografia_lista TEXT DEFAULT 'No',
                piezas_totales INTEGER DEFAULT 0,
                usuario TEXT,
                observaciones TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS asignacion (
                id SERIAL PRIMARY KEY,
                orden_id INTEGER NOT NULL UNIQUE REFERENCES ordenes(id) ON DELETE CASCADE,
                fecha_salida_maquila TEXT,
                nombre_maquilero TEXT,
                usuario TEXT,
                observaciones TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS habilitado (
                id SERIAL PRIMARY KEY,
                orden_id INTEGER NOT NULL UNIQUE REFERENCES ordenes(id) ON DELETE CASCADE,
                estado TEXT NOT NULL,
                usuario TEXT,
                observaciones TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS maquila (
                id SERIAL PRIMARY KEY,
                orden_id INTEGER NOT NULL UNIQUE REFERENCES ordenes(id) ON DELETE CASCADE,
                fecha_envio TEXT,
                fecha_regreso TEXT,
                usuario_envio TEXT,
                usuario_regreso TEXT,
                observaciones TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS historial (
                id SERIAL PRIMARY KEY,
                referencia_tipo TEXT,
                referencia_id INTEGER,
                etapa TEXT NOT NULL,
                accion TEXT,
                usuario TEXT,
                detalle TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    else:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                nombre TEXT,
                area TEXT,
                activo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS programas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_programa TEXT NOT NULL UNIQUE,
                estado TEXT NOT NULL DEFAULT 'Pendiente Trazo',
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT,
                observaciones TEXT
            );
            CREATE TABLE IF NOT EXISTS puntos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                programa_id INTEGER NOT NULL,
                punto TEXT NOT NULL,
                modelo TEXT NOT NULL,
                color TEXT NOT NULL,
                tallas_json TEXT NOT NULL DEFAULT '{}',
                orden_id INTEGER,
                estado TEXT DEFAULT 'Pendiente',
                FOREIGN KEY (programa_id) REFERENCES programas(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS trazo (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                programa_id INTEGER NOT NULL UNIQUE,
                confirmado INTEGER DEFAULT 0,
                usuario TEXT,
                fecha_confirmacion TEXT,
                observaciones TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (programa_id) REFERENCES programas(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_orden TEXT NOT NULL UNIQUE,
                punto_id INTEGER,
                programa_id INTEGER,
                estado_actual TEXT NOT NULL DEFAULT 'Corte',
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT
            );
            CREATE TABLE IF NOT EXISTS corte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL UNIQUE,
                fecha_inicio TEXT,
                fecha_final TEXT,
                fecha_entrega_tampografia TEXT,
                tampografia_lista TEXT DEFAULT 'No',
                piezas_totales INTEGER DEFAULT 0,
                usuario TEXT,
                observaciones TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS asignacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL UNIQUE,
                fecha_salida_maquila TEXT,
                nombre_maquilero TEXT,
                usuario TEXT,
                observaciones TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS habilitado (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL UNIQUE,
                estado TEXT NOT NULL,
                usuario TEXT,
                observaciones TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS maquila (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL UNIQUE,
                fecha_envio TEXT,
                fecha_regreso TEXT,
                usuario_envio TEXT,
                usuario_regreso TEXT,
                observaciones TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referencia_tipo TEXT,
                referencia_id INTEGER,
                etapa TEXT NOT NULL,
                accion TEXT,
                usuario TEXT,
                detalle TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.commit()

    cur.execute("SELECT COUNT(*) as c FROM usuarios")
    row = cur.fetchone()
    count = row[0] if not isinstance(row, dict) else row["c"]
    if count == 0:
        def hp(p): return hashlib.sha256(p.encode()).hexdigest()
        users = [
            ("admin", hp("admin123"), "Administrador", "Admin"),
            ("programa", hp("programa123"), "Programa de Corte", "Programa"),
            ("trazo", hp("trazo123"), "Área de Trazo", "Trazo"),
            ("corte", hp("corte123"), "Área de Corte", "Corte"),
            ("gerente", hp("gerente123"), "Gerente", "Gerente"),
            ("habilitado", hp("habilitado123"), "Habilitado", "Habilitado"),
        ]
        for u in users:
            if USE_POSTGRES:
                cur.execute("INSERT INTO usuarios (usuario, password_hash, nombre, area) VALUES (%s,%s,%s,%s)", u)
            else:
                cur.execute("INSERT INTO usuarios (usuario, password_hash, nombre, area) VALUES (?,?,?,?)", u)
        conn.commit()
        print("✓ Usuarios creados")
    conn.close()
    print("✓ Base de datos lista")


def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()


def log_hist(ref_tipo, ref_id, etapa, accion, usuario, detalle=""):
    conn = get_db()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute("INSERT INTO historial (referencia_tipo, referencia_id, etapa, accion, usuario, detalle) VALUES (%s,%s,%s,%s,%s,%s)",
                    (ref_tipo, ref_id, etapa, accion, usuario, detalle))
    else:
        cur.execute("INSERT INTO historial (referencia_tipo, referencia_id, etapa, accion, usuario, detalle) VALUES (?,?,?,?,?,?)",
                    (ref_tipo, ref_id, etapa, accion, usuario, detalle))
    conn.commit()
    conn.close()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ============================================================
# AUTH
# ============================================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        cur = dict_cursor(conn)
        cur.execute(f"SELECT * FROM usuarios WHERE usuario = {ph()} AND activo = 1", (usuario,))
        user = cur.fetchone()
        conn.close()
        if user and user["password_hash"] == hash_password(password):
            session["user_id"] = user["id"]
            session["usuario"] = user["usuario"]
            session["nombre"] = user["nombre"]
            session["area"] = user["area"]
            flash(f"Bienvenido, {user['nombre']}", "success")
            return redirect(url_for("index"))
        flash("Usuario o contraseña incorrectos", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ============================================================
# DASHBOARD
# ============================================================
@app.route("/")
@login_required
def index():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute("SELECT * FROM programas ORDER BY id DESC LIMIT 50")
    programas = cur.fetchall()
    cur.execute("""
        SELECT o.*, p.modelo, p.color, p.punto, pr.numero_programa
        FROM ordenes o
        LEFT JOIN puntos p ON p.id = o.punto_id
        LEFT JOIN programas pr ON pr.id = o.programa_id
        ORDER BY o.id DESC LIMIT 50
    """)
    ordenes = cur.fetchall()
    conn.close()
    return render_template("index.html", programas=programas, ordenes=ordenes)


# ============================================================
# 1. PROGRAMA DE CORTE
# ============================================================
@app.route("/programas")
@login_required
def lista_programas():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute("SELECT * FROM programas ORDER BY id DESC")
    programas = cur.fetchall()
    conn.close()
    return render_template("lista_programas.html", programas=programas)


@app.route("/programa/nuevo", methods=["GET", "POST"])
@login_required
def programa_nuevo():
    if request.method == "POST":
        numero = request.form.get("numero_programa", "").strip()
        observaciones = request.form.get("observaciones", "").strip()
        usuario = session.get("nombre") or session.get("usuario")

        puntos = request.form.getlist("punto[]")
        modelos = request.form.getlist("modelo[]")
        colores = request.form.getlist("color[]")
        # tallas: cada punto puede tener varias tallas enviadas como tallas_0_XS, tallas_0_S, etc.
        # Simplificamos: enviamos un JSON por punto
        tallas_raw = request.form.getlist("tallas_json[]")

        if not numero:
            flash("Número de programa obligatorio", "error")
            return redirect(url_for("programa_nuevo"))

        conn = get_db()
        cur = conn.cursor()
        try:
            if USE_POSTGRES:
                cur.execute("INSERT INTO programas (numero_programa, creado_por, observaciones) VALUES (%s,%s,%s) RETURNING id",
                            (numero, usuario, observaciones))
                prog_id = cur.fetchone()[0]
            else:
                cur.execute("INSERT INTO programas (numero_programa, creado_por, observaciones) VALUES (?,?,?)",
                            (numero, usuario, observaciones))
                prog_id = cur.lastrowid

            for i in range(len(puntos)):
                if puntos[i].strip() and modelos[i].strip():
                    tj = tallas_raw[i] if i < len(tallas_raw) else "{}"
                    if USE_POSTGRES:
                        cur.execute("INSERT INTO puntos (programa_id, punto, modelo, color, tallas_json) VALUES (%s,%s,%s,%s,%s)",
                                    (prog_id, puntos[i].strip(), modelos[i].strip(), colores[i].strip(), tj))
                    else:
                        cur.execute("INSERT INTO puntos (programa_id, punto, modelo, color, tallas_json) VALUES (?,?,?,?,?)",
                                    (prog_id, puntos[i].strip(), modelos[i].strip(), colores[i].strip(), tj))

            conn.commit()
            log_hist("programa", prog_id, "Programa", "Programa creado", usuario)
            flash(f"Programa {numero} creado", "success")
            return redirect(url_for("ver_programa", prog_id=prog_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error: {e}", "error")
            return redirect(url_for("programa_nuevo"))
        finally:
            conn.close()

    return render_template("programa_form.html")


@app.route("/programa/<int:prog_id>")
@login_required
def ver_programa(prog_id):
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(f"SELECT * FROM programas WHERE id = {ph()}", (prog_id,))
    programa = cur.fetchone()
    if not programa:
        flash("Programa no encontrado", "error")
        conn.close()
        return redirect(url_for("lista_programas"))

    cur.execute(f"SELECT * FROM puntos WHERE programa_id = {ph()} ORDER BY id", (prog_id,))
    puntos = cur.fetchall()
    # parse tallas
    puntos_parsed = []
    for p in puntos:
        try:
            tallas = json.loads(p["tallas_json"] or "{}")
        except:
            tallas = {}
        puntos_parsed.append({**dict(p), "tallas": tallas})

    cur.execute(f"SELECT * FROM trazo WHERE programa_id = {ph()}", (prog_id,))
    trazo = cur.fetchone()
    conn.close()
    return render_template("ver_programa.html", programa=programa, puntos=puntos_parsed, trazo=trazo)


# ============================================================
# 2. TRAZO
# ============================================================
@app.route("/trazo/<int:prog_id>", methods=["GET", "POST"])
@login_required
def confirmar_trazo(prog_id):
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(f"SELECT * FROM programas WHERE id = {ph()}", (prog_id,))
    programa = cur.fetchone()
    if not programa:
        flash("Programa no encontrado", "error")
        conn.close()
        return redirect(url_for("lista_programas"))

    cur.execute(f"SELECT * FROM trazo WHERE programa_id = {ph()}", (prog_id,))
    trazo = cur.fetchone()
    conn.close()

    if request.method == "POST":
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()
        fecha = datetime.now().strftime("%Y-%m-%d")

        conn = get_db()
        cur = conn.cursor()
        if trazo:
            if USE_POSTGRES:
                cur.execute("UPDATE trazo SET confirmado=1, usuario=%s, fecha_confirmacion=%s, observaciones=%s WHERE programa_id=%s",
                            (usuario, fecha, observaciones, prog_id))
            else:
                cur.execute("UPDATE trazo SET confirmado=1, usuario=?, fecha_confirmacion=?, observaciones=? WHERE programa_id=?",
                            (usuario, fecha, observaciones, prog_id))
        else:
            if USE_POSTGRES:
                cur.execute("INSERT INTO trazo (programa_id, confirmado, usuario, fecha_confirmacion, observaciones) VALUES (%s,1,%s,%s,%s)",
                            (prog_id, usuario, fecha, observaciones))
            else:
                cur.execute("INSERT INTO trazo (programa_id, confirmado, usuario, fecha_confirmacion, observaciones) VALUES (?,1,?,?,?)",
                            (prog_id, usuario, fecha, observaciones))

        if USE_POSTGRES:
            cur.execute("UPDATE programas SET estado = 'Trazo Listo' WHERE id = %s", (prog_id,))
        else:
            cur.execute("UPDATE programas SET estado = 'Trazo Listo' WHERE id = ?", (prog_id,))
        conn.commit()
        conn.close()
        log_hist("programa", prog_id, "Trazo", "Trazo confirmado", usuario, observaciones)
        flash("Trazo confirmado. Ahora Corte puede asignar órdenes.", "success")
        return redirect(url_for("ver_programa", prog_id=prog_id))

    return render_template("trazo_form.html", programa=programa, trazo=trazo)


# ============================================================
# 3. CORTE - Asignar Orden a un Punto
# ============================================================
@app.route("/corte/asignar/<int:punto_id>", methods=["GET", "POST"])
@login_required
def corte_asignar_orden(punto_id):
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(f"""
        SELECT p.*, pr.numero_programa, pr.estado as prog_estado, pr.id as prog_id
        FROM puntos p
        JOIN programas pr ON pr.id = p.programa_id
        WHERE p.id = {ph()}
    """, (punto_id,))
    punto = cur.fetchone()
    if not punto:
        flash("Punto no encontrado", "error")
        conn.close()
        return redirect(url_for("lista_programas"))

    try:
        tallas = json.loads(punto["tallas_json"] or "{}")
    except:
        tallas = {}
    total_piezas = sum(int(v) for v in tallas.values() if str(v).isdigit())

    if request.method == "POST":
        numero_orden = request.form.get("numero_orden", "").strip()
        fecha_inicio = request.form.get("fecha_inicio", "").strip()
        fecha_final = request.form.get("fecha_final", "").strip()
        fecha_tamp = request.form.get("fecha_entrega_tampografia", "").strip()
        tampografia = request.form.get("tampografia_lista", "No")
        observaciones = request.form.get("observaciones", "").strip()
        usuario = session.get("nombre") or session.get("usuario")

        if not numero_orden:
            flash("Número de orden obligatorio", "error")
            return redirect(url_for("corte_asignar_orden", punto_id=punto_id))

        conn2 = get_db()
        cur2 = conn2.cursor()
        try:
            if USE_POSTGRES:
                cur2.execute("""
                    INSERT INTO ordenes (numero_orden, punto_id, programa_id, estado_actual, creado_por)
                    VALUES (%s,%s,%s,'Corte',%s) RETURNING id
                """, (numero_orden, punto_id, punto["prog_id"], usuario))
                orden_id = cur2.fetchone()[0]
            else:
                cur2.execute("""
                    INSERT INTO ordenes (numero_orden, punto_id, programa_id, estado_actual, creado_por)
                    VALUES (?,?,?,'Corte',?)
                """, (numero_orden, punto_id, punto["prog_id"], usuario))
                orden_id = cur2.lastrowid

            if USE_POSTGRES:
                cur2.execute("""
                    INSERT INTO corte (orden_id, fecha_inicio, fecha_final, fecha_entrega_tampografia,
                                       tampografia_lista, piezas_totales, usuario, observaciones)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """, (orden_id, fecha_inicio, fecha_final, fecha_tamp, tampografia, total_piezas, usuario, observaciones))
                cur2.execute("UPDATE puntos SET orden_id=%s, estado='Con Orden' WHERE id=%s", (orden_id, punto_id))
            else:
                cur2.execute("""
                    INSERT INTO corte (orden_id, fecha_inicio, fecha_final, fecha_entrega_tampografia,
                                       tampografia_lista, piezas_totales, usuario, observaciones)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (orden_id, fecha_inicio, fecha_final, fecha_tamp, tampografia, total_piezas, usuario, observaciones))
                cur2.execute("UPDATE puntos SET orden_id=?, estado='Con Orden' WHERE id=?", (orden_id, punto_id))

            conn2.commit()
            log_hist("orden", orden_id, "Corte", "Orden asignada al punto", usuario,
                     f"Programa {punto['numero_programa']} - Punto {punto['punto']}")
            flash(f"Orden {numero_orden} creada y vinculada al punto", "success")
            return redirect(url_for("ver_orden", orden_id=orden_id))
        except Exception as e:
            conn2.rollback()
            flash(f"Error: {e}", "error")
            return redirect(url_for("corte_asignar_orden", punto_id=punto_id))
        finally:
            conn2.close()

    conn.close()
    return render_template("corte_asignar.html", punto=punto, tallas=tallas, total_piezas=total_piezas)


# ============================================================
# ÓRDENES (flujo posterior)
# ============================================================
@app.route("/orden/<int:orden_id>")
@login_required
def ver_orden(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(f"""
        SELECT o.*, p.punto, p.modelo, p.color, p.tallas_json, pr.numero_programa
        FROM ordenes o
        LEFT JOIN puntos p ON p.id = o.punto_id
        LEFT JOIN programas pr ON pr.id = o.programa_id
        WHERE o.id = {ph()}
    """, (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))

    try:
        tallas = json.loads(orden["tallas_json"] or "{}") if orden.get("tallas_json") else {}
    except:
        tallas = {}

    cur.execute(f"SELECT * FROM corte WHERE orden_id = {ph()}", (orden_id,))
    corte = cur.fetchone()
    cur.execute(f"SELECT * FROM asignacion WHERE orden_id = {ph()}", (orden_id,))
    asignacion = cur.fetchone()
    cur.execute(f"SELECT * FROM habilitado WHERE orden_id = {ph()}", (orden_id,))
    habilitado = cur.fetchone()
    cur.execute(f"SELECT * FROM maquila WHERE orden_id = {ph()}", (orden_id,))
    maquila = cur.fetchone()
    cur.execute(f"SELECT * FROM historial WHERE referencia_tipo='orden' AND referencia_id = {ph()} ORDER BY fecha_registro DESC", (orden_id,))
    historial = cur.fetchall()
    conn.close()
    return render_template("ver_orden.html", orden=orden, tallas=tallas, corte=corte,
                           asignacion=asignacion, habilitado=habilitado, maquila=maquila, historial=historial)


@app.route("/asignacion/<int:orden_id>", methods=["GET", "POST"])
@login_required
def asignacion(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(f"SELECT * FROM ordenes WHERE id = {ph()}", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))
    cur.execute(f"SELECT * FROM asignacion WHERE orden_id = {ph()}", (orden_id,))
    asig = cur.fetchone()
    conn.close()

    if request.method == "POST":
        fecha_salida = request.form.get("fecha_salida_maquila", "").strip()
        maquilero = request.form.get("nombre_maquilero", "").strip()
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()

        conn = get_db()
        cur = conn.cursor()
        if asig:
            if USE_POSTGRES:
                cur.execute("UPDATE asignacion SET fecha_salida_maquila=%s, nombre_maquilero=%s, usuario=%s, observaciones=%s WHERE orden_id=%s",
                            (fecha_salida, maquilero, usuario, observaciones, orden_id))
            else:
                cur.execute("UPDATE asignacion SET fecha_salida_maquila=?, nombre_maquilero=?, usuario=?, observaciones=? WHERE orden_id=?",
                            (fecha_salida, maquilero, usuario, observaciones, orden_id))
        else:
            if USE_POSTGRES:
                cur.execute("INSERT INTO asignacion (orden_id, fecha_salida_maquila, nombre_maquilero, usuario, observaciones) VALUES (%s,%s,%s,%s,%s)",
                            (orden_id, fecha_salida, maquilero, usuario, observaciones))
            else:
                cur.execute("INSERT INTO asignacion (orden_id, fecha_salida_maquila, nombre_maquilero, usuario, observaciones) VALUES (?,?,?,?,?)",
                            (orden_id, fecha_salida, maquilero, usuario, observaciones))
        if USE_POSTGRES:
            cur.execute("UPDATE ordenes SET estado_actual='Asignacion' WHERE id=%s", (orden_id,))
        else:
            cur.execute("UPDATE ordenes SET estado_actual='Asignacion' WHERE id=?", (orden_id,))
        conn.commit()
        conn.close()
        log_hist("orden", orden_id, "Asignacion", "Asignación realizada", usuario, f"Maquilero: {maquilero}")
        flash("Asignación guardada", "success")
        return redirect(url_for("ver_orden", orden_id=orden_id))

    return render_template("asignacion.html", orden=orden, asignacion=asig)


@app.route("/habilitado/<int:orden_id>", methods=["GET", "POST"])
@login_required
def habilitado(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(f"SELECT * FROM ordenes WHERE id = {ph()}", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))
    cur.execute(f"SELECT * FROM habilitado WHERE orden_id = {ph()}", (orden_id,))
    hab = cur.fetchone()
    conn.close()

    if request.method == "POST":
        estado = request.form.get("estado", "Parcial")
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()
        conn = get_db()
        cur = conn.cursor()
        if hab:
            if USE_POSTGRES:
                cur.execute("UPDATE habilitado SET estado=%s, usuario=%s, observaciones=%s WHERE orden_id=%s",
                            (estado, usuario, observaciones, orden_id))
            else:
                cur.execute("UPDATE habilitado SET estado=?, usuario=?, observaciones=? WHERE orden_id=?",
                            (estado, usuario, observaciones, orden_id))
        else:
            if USE_POSTGRES:
                cur.execute("INSERT INTO habilitado (orden_id, estado, usuario, observaciones) VALUES (%s,%s,%s,%s)",
                            (orden_id, estado, usuario, observaciones))
            else:
                cur.execute("INSERT INTO habilitado (orden_id, estado, usuario, observaciones) VALUES (?,?,?,?)",
                            (orden_id, estado, usuario, observaciones))
        if USE_POSTGRES:
            cur.execute("UPDATE ordenes SET estado_actual='Habilitado' WHERE id=%s", (orden_id,))
        else:
            cur.execute("UPDATE ordenes SET estado_actual='Habilitado' WHERE id=?", (orden_id,))
        conn.commit()
        conn.close()
        log_hist("orden", orden_id, "Habilitado", "Habilitado registrado", usuario, f"Estado: {estado}")
        flash("Habilitado guardado", "success")
        return redirect(url_for("ver_orden", orden_id=orden_id))

    return render_template("habilitado.html", orden=orden, habilitado=hab)


@app.route("/maquila/<int:orden_id>", methods=["GET", "POST"])
@login_required
def maquila(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute(f"SELECT * FROM ordenes WHERE id = {ph()}", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))
    cur.execute(f"SELECT * FROM maquila WHERE orden_id = {ph()}", (orden_id,))
    maq = cur.fetchone()
    cur.execute(f"SELECT * FROM habilitado WHERE orden_id = {ph()}", (orden_id,))
    hab = cur.fetchone()
    conn.close()

    if request.method == "POST":
        accion = request.form.get("accion")
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()
        fecha = request.form.get("fecha", "").strip() or datetime.now().strftime("%Y-%m-%d")

        conn = get_db()
        cur = conn.cursor()
        if accion == "enviar":
            if maq:
                if USE_POSTGRES:
                    cur.execute("UPDATE maquila SET fecha_envio=%s, usuario_envio=%s, observaciones=%s WHERE orden_id=%s",
                                (fecha, usuario, observaciones, orden_id))
                else:
                    cur.execute("UPDATE maquila SET fecha_envio=?, usuario_envio=?, observaciones=? WHERE orden_id=?",
                                (fecha, usuario, observaciones, orden_id))
            else:
                if USE_POSTGRES:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_envio, usuario_envio, observaciones) VALUES (%s,%s,%s,%s)",
                                (orden_id, fecha, usuario, observaciones))
                else:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_envio, usuario_envio, observaciones) VALUES (?,?,?,?)",
                                (orden_id, fecha, usuario, observaciones))
            if USE_POSTGRES:
                cur.execute("UPDATE ordenes SET estado_actual='En_Maquila' WHERE id=%s", (orden_id,))
            else:
                cur.execute("UPDATE ordenes SET estado_actual='En_Maquila' WHERE id=?", (orden_id,))
            log_hist("orden", orden_id, "Maquila", "Enviado a maquila", usuario)
            flash("Enviado a maquila", "success")
        elif accion == "regresar":
            if maq:
                if USE_POSTGRES:
                    cur.execute("UPDATE maquila SET fecha_regreso=%s, usuario_regreso=%s, observaciones=%s WHERE orden_id=%s",
                                (fecha, usuario, observaciones, orden_id))
                else:
                    cur.execute("UPDATE maquila SET fecha_regreso=?, usuario_regreso=?, observaciones=? WHERE orden_id=?",
                                (fecha, usuario, observaciones, orden_id))
            else:
                if USE_POSTGRES:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_regreso, usuario_regreso, observaciones) VALUES (%s,%s,%s,%s)",
                                (orden_id, fecha, usuario, observaciones))
                else:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_regreso, usuario_regreso, observaciones) VALUES (?,?,?,?)",
                                (orden_id, fecha, usuario, observaciones))
            if USE_POSTGRES:
                cur.execute("UPDATE ordenes SET estado_actual='Terminado' WHERE id=%s", (orden_id,))
            else:
                cur.execute("UPDATE ordenes SET estado_actual='Terminado' WHERE id=?", (orden_id,))
            log_hist("orden", orden_id, "Maquila", "Regreso - TERMINADO", usuario)
            flash("Orden TERMINADA", "success")
        conn.commit()
        conn.close()
        return redirect(url_for("ver_orden", orden_id=orden_id))

    return render_template("maquila.html", orden=orden, maquila=maq, habilitado=hab)


@app.route("/agenda")
@login_required
def agenda():
    conn = get_db()
    cur = dict_cursor(conn)
    hoy = datetime.now().date()
    dias = []
    trad = {"Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
            "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"}
    for i in range(15):
        fecha = hoy + timedelta(days=i)
        fecha_str = fecha.strftime("%Y-%m-%d")
        cur.execute(f"""
            SELECT o.numero_orden, o.id, a.nombre_maquilero, a.fecha_salida_maquila
            FROM asignacion a
            JOIN ordenes o ON o.id = a.orden_id
            WHERE a.fecha_salida_maquila = {ph()}
            ORDER BY o.numero_orden
        """, (fecha_str,))
        ordenes = cur.fetchall()
        dias.append({
            "fecha": fecha, "fecha_str": fecha_str,
            "nombre_dia": trad.get(fecha.strftime("%A"), fecha.strftime("%A")),
            "ordenes": ordenes, "total_ordenes": len(ordenes)
        })
    conn.close()
    return render_template("agenda.html", dias=dias, hoy=hoy.strftime("%Y-%m-%d"))


# Init
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Error init_db: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=not USE_POSTGRES)
