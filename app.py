#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Producción - Versión para Render (PostgreSQL)
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from functools import wraps
from datetime import datetime, timedelta
import os
import hashlib

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "produccion_render_secreto_2026")

# ============================================================
# CONEXIÓN A BASE DE DATOS
# ============================================================
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Render usa postgres:// pero psycopg2 necesita postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    import psycopg2
    import psycopg2.extras
    USE_POSTGRES = True
else:
    import sqlite3
    from pathlib import Path
    DB_PATH = Path(__file__).parent / "produccion_red.db"
    USE_POSTGRES = False


def get_db():
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn


def dict_cursor(conn):
    if USE_POSTGRES:
        return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    return conn.cursor()


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
            CREATE TABLE IF NOT EXISTS ordenes (
                id SERIAL PRIMARY KEY,
                numero_orden TEXT NOT NULL UNIQUE,
                estado_actual TEXT NOT NULL DEFAULT 'Corte',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT
            );
            CREATE TABLE IF NOT EXISTS lineas (
                id SERIAL PRIMARY KEY,
                orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE,
                modelo TEXT NOT NULL,
                color TEXT NOT NULL,
                piezas_totales INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS corte (
                id SERIAL PRIMARY KEY,
                orden_id INTEGER NOT NULL UNIQUE REFERENCES ordenes(id) ON DELETE CASCADE,
                fecha_inicio TEXT,
                fecha_final TEXT,
                fecha_entrega_tampografia TEXT,
                tampografia_lista TEXT DEFAULT 'No',
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
                orden_id INTEGER NOT NULL REFERENCES ordenes(id) ON DELETE CASCADE,
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
            CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_orden TEXT NOT NULL UNIQUE,
                estado_actual TEXT NOT NULL DEFAULT 'Corte',
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT
            );
            CREATE TABLE IF NOT EXISTS lineas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL,
                modelo TEXT NOT NULL,
                color TEXT NOT NULL,
                piezas_totales INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS corte (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER NOT NULL UNIQUE,
                fecha_inicio TEXT,
                fecha_final TEXT,
                fecha_entrega_tampografia TEXT,
                tampografia_lista TEXT DEFAULT 'No',
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
                orden_id INTEGER NOT NULL,
                etapa TEXT NOT NULL,
                accion TEXT,
                usuario TEXT,
                detalle TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (orden_id) REFERENCES ordenes(id) ON DELETE CASCADE
            );
        """)

    conn.commit()

    # Usuarios por defecto
    cur.execute("SELECT COUNT(*) as c FROM usuarios")
    row = cur.fetchone()
    count = row[0] if not USE_POSTGRES else row[0]
    if isinstance(row, dict):
        count = row["c"]

    if count == 0:
        def hp(p):
            return hashlib.sha256(p.encode()).hexdigest()
        users = [
            ("admin", hp("admin123"), "Administrador", "Admin"),
            ("corte", hp("corte123"), "Área de Corte", "Corte"),
            ("gerente", hp("gerente123"), "Gerente de Producción", "Gerente"),
            ("habilitado", hp("habilitado123"), "Área de Habilitado", "Habilitado"),
        ]
        for u in users:
            cur.execute(
                "INSERT INTO usuarios (usuario, password_hash, nombre, area) VALUES (%s, %s, %s, %s)" if USE_POSTGRES
                else "INSERT INTO usuarios (usuario, password_hash, nombre, area) VALUES (?, ?, ?, ?)",
                u
            )
        conn.commit()
        print("✓ Usuarios por defecto creados")

    conn.close()
    print("✓ Base de datos lista")


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def registrar_historial(orden_id, etapa, accion, usuario, detalle=""):
    conn = get_db()
    cur = conn.cursor()
    if USE_POSTGRES:
        cur.execute(
            "INSERT INTO historial (orden_id, etapa, accion, usuario, detalle) VALUES (%s, %s, %s, %s, %s)",
            (orden_id, etapa, accion, usuario, detalle)
        )
    else:
        cur.execute(
            "INSERT INTO historial (orden_id, etapa, accion, usuario, detalle) VALUES (?, ?, ?, ?, ?)",
            (orden_id, etapa, accion, usuario, detalle)
        )
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
# RUTAS
# ============================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "")
        conn = get_db()
        cur = dict_cursor(conn)
        if USE_POSTGRES:
            cur.execute("SELECT * FROM usuarios WHERE usuario = %s AND activo = 1", (usuario,))
        else:
            cur.execute("SELECT * FROM usuarios WHERE usuario = ? AND activo = 1", (usuario,))
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
    flash("Sesión cerrada", "success")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute("""
        SELECT o.*,
               (SELECT COALESCE(SUM(piezas_totales),0) FROM lineas WHERE orden_id = o.id) as total_piezas,
               a.nombre_maquilero,
               a.fecha_salida_maquila,
               h.estado as estado_habilitado
        FROM ordenes o
        LEFT JOIN asignacion a ON a.orden_id = o.id
        LEFT JOIN habilitado h ON h.orden_id = o.id
        ORDER BY o.id DESC
    """)
    ordenes = cur.fetchall()
    conn.close()
    return render_template("index.html", ordenes=ordenes)


@app.route("/orden/<int:orden_id>")
@login_required
def ver_orden(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)

    if USE_POSTGRES:
        cur.execute("SELECT * FROM ordenes WHERE id = %s", (orden_id,))
    else:
        cur.execute("SELECT * FROM ordenes WHERE id = ?", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))

    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM lineas WHERE orden_id = {ph}", (orden_id,))
    lineas = cur.fetchall()
    cur.execute(f"SELECT * FROM corte WHERE orden_id = {ph}", (orden_id,))
    corte = cur.fetchone()
    cur.execute(f"SELECT * FROM asignacion WHERE orden_id = {ph}", (orden_id,))
    asignacion = cur.fetchone()
    cur.execute(f"SELECT * FROM habilitado WHERE orden_id = {ph}", (orden_id,))
    habilitado = cur.fetchone()
    cur.execute(f"SELECT * FROM maquila WHERE orden_id = {ph}", (orden_id,))
    maquila = cur.fetchone()
    cur.execute(f"SELECT * FROM historial WHERE orden_id = {ph} ORDER BY fecha_registro DESC", (orden_id,))
    historial = cur.fetchall()
    conn.close()

    return render_template("ver_orden.html", orden=orden, lineas=lineas, corte=corte,
                           asignacion=asignacion, habilitado=habilitado, maquila=maquila, historial=historial)


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
        ph = "%s" if USE_POSTGRES else "?"
        cur.execute(f"""
            SELECT o.numero_orden, o.id, a.nombre_maquilero, a.fecha_salida_maquila,
                   (SELECT COALESCE(SUM(piezas_totales),0) FROM lineas WHERE orden_id = o.id) as total_piezas
            FROM asignacion a
            JOIN ordenes o ON o.id = a.orden_id
            WHERE a.fecha_salida_maquila = {ph}
            ORDER BY o.numero_orden
        """, (fecha_str,))
        ordenes = cur.fetchall()
        dias.append({
            "fecha": fecha,
            "fecha_str": fecha_str,
            "nombre_dia": trad.get(fecha.strftime("%A"), fecha.strftime("%A")),
            "ordenes": ordenes,
            "total_ordenes": len(ordenes),
            "total_piezas": sum((o["total_piezas"] or 0) for o in ordenes)
        })
    conn.close()
    return render_template("agenda.html", dias=dias, hoy=hoy.strftime("%Y-%m-%d"))


@app.route("/corte/nueva", methods=["GET", "POST"])
@login_required
def corte_nueva():
    if request.method == "POST":
        numero_orden = request.form.get("numero_orden", "").strip()
        fecha_inicio = request.form.get("fecha_inicio", "").strip()
        fecha_final = request.form.get("fecha_final", "").strip()
        fecha_tampografia = request.form.get("fecha_entrega_tampografia", "").strip()
        tampografia = request.form.get("tampografia_lista", "No")
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()
        modelos = request.form.getlist("modelo[]")
        colores = request.form.getlist("color[]")
        piezas = request.form.getlist("piezas[]")

        if not numero_orden:
            flash("El número de orden es obligatorio", "error")
            return redirect(url_for("corte_nueva"))

        conn = get_db()
        cur = conn.cursor()
        try:
            if USE_POSTGRES:
                cur.execute(
                    "INSERT INTO ordenes (numero_orden, estado_actual, creado_por) VALUES (%s, 'Corte', %s) RETURNING id",
                    (numero_orden, usuario)
                )
                orden_id = cur.fetchone()[0]
            else:
                cur.execute(
                    "INSERT INTO ordenes (numero_orden, estado_actual, creado_por) VALUES (?, 'Corte', ?)",
                    (numero_orden, usuario)
                )
                orden_id = cur.lastrowid

            for i in range(len(modelos)):
                if modelos[i].strip():
                    if USE_POSTGRES:
                        cur.execute(
                            "INSERT INTO lineas (orden_id, modelo, color, piezas_totales) VALUES (%s, %s, %s, %s)",
                            (orden_id, modelos[i].strip(), colores[i].strip(), int(piezas[i] or 0))
                        )
                    else:
                        cur.execute(
                            "INSERT INTO lineas (orden_id, modelo, color, piezas_totales) VALUES (?, ?, ?, ?)",
                            (orden_id, modelos[i].strip(), colores[i].strip(), int(piezas[i] or 0))
                        )

            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO corte (orden_id, fecha_inicio, fecha_final, fecha_entrega_tampografia,
                                       tampografia_lista, usuario, observaciones)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (orden_id, fecha_inicio, fecha_final, fecha_tampografia, tampografia, usuario, observaciones))
            else:
                cur.execute("""
                    INSERT INTO corte (orden_id, fecha_inicio, fecha_final, fecha_entrega_tampografia,
                                       tampografia_lista, usuario, observaciones)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (orden_id, fecha_inicio, fecha_final, fecha_tampografia, tampografia, usuario, observaciones))

            conn.commit()
            registrar_historial(orden_id, "Corte", "Orden creada", usuario,
                                f"Tampografía: {tampografia} | Entrega: {fecha_tampografia}")
            flash(f"Orden {numero_orden} creada", "success")
            return redirect(url_for("ver_orden", orden_id=orden_id))
        except Exception as e:
            conn.rollback()
            flash(f"Error: posiblemente el número de orden ya existe. ({e})", "error")
            return redirect(url_for("corte_nueva"))
        finally:
            conn.close()

    return render_template("corte_form.html", orden=None, corte=None, lineas=[])


@app.route("/corte/editar/<int:orden_id>", methods=["GET", "POST"])
@login_required
def corte_editar(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM ordenes WHERE id = {ph}", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))

    cur.execute(f"SELECT * FROM corte WHERE orden_id = {ph}", (orden_id,))
    corte = cur.fetchone()
    cur.execute(f"SELECT * FROM lineas WHERE orden_id = {ph}", (orden_id,))
    lineas = cur.fetchall()
    conn.close()

    if request.method == "POST":
        fecha_inicio = request.form.get("fecha_inicio", "").strip()
        fecha_final = request.form.get("fecha_final", "").strip()
        fecha_tampografia = request.form.get("fecha_entrega_tampografia", "").strip()
        tampografia = request.form.get("tampografia_lista", "No")
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()
        modelos = request.form.getlist("modelo[]")
        colores = request.form.getlist("color[]")
        piezas = request.form.getlist("piezas[]")

        conn = get_db()
        cur = conn.cursor()
        if corte:
            if USE_POSTGRES:
                cur.execute("""
                    UPDATE corte SET fecha_inicio=%s, fecha_final=%s, fecha_entrega_tampografia=%s,
                    tampografia_lista=%s, usuario=%s, observaciones=%s, fecha_registro=CURRENT_TIMESTAMP
                    WHERE orden_id=%s
                """, (fecha_inicio, fecha_final, fecha_tampografia, tampografia, usuario, observaciones, orden_id))
            else:
                cur.execute("""
                    UPDATE corte SET fecha_inicio=?, fecha_final=?, fecha_entrega_tampografia=?,
                    tampografia_lista=?, usuario=?, observaciones=?, fecha_registro=CURRENT_TIMESTAMP
                    WHERE orden_id=?
                """, (fecha_inicio, fecha_final, fecha_tampografia, tampografia, usuario, observaciones, orden_id))
        else:
            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO corte (orden_id, fecha_inicio, fecha_final, fecha_entrega_tampografia,
                                       tampografia_lista, usuario, observaciones)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (orden_id, fecha_inicio, fecha_final, fecha_tampografia, tampografia, usuario, observaciones))
            else:
                cur.execute("""
                    INSERT INTO corte (orden_id, fecha_inicio, fecha_final, fecha_entrega_tampografia,
                                       tampografia_lista, usuario, observaciones)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (orden_id, fecha_inicio, fecha_final, fecha_tampografia, tampografia, usuario, observaciones))

        if USE_POSTGRES:
            cur.execute("DELETE FROM lineas WHERE orden_id = %s", (orden_id,))
        else:
            cur.execute("DELETE FROM lineas WHERE orden_id = ?", (orden_id,))

        for i in range(len(modelos)):
            if modelos[i].strip():
                if USE_POSTGRES:
                    cur.execute(
                        "INSERT INTO lineas (orden_id, modelo, color, piezas_totales) VALUES (%s, %s, %s, %s)",
                        (orden_id, modelos[i].strip(), colores[i].strip(), int(piezas[i] or 0))
                    )
                else:
                    cur.execute(
                        "INSERT INTO lineas (orden_id, modelo, color, piezas_totales) VALUES (?, ?, ?, ?)",
                        (orden_id, modelos[i].strip(), colores[i].strip(), int(piezas[i] or 0))
                    )

        conn.commit()
        conn.close()
        registrar_historial(orden_id, "Corte", "Corte modificado", usuario,
                            f"Tampografía: {tampografia} | Entrega: {fecha_tampografia}")
        flash("Corte actualizado", "success")
        return redirect(url_for("ver_orden", orden_id=orden_id))

    return render_template("corte_form.html", orden=orden, corte=corte, lineas=lineas)


@app.route("/asignacion/<int:orden_id>", methods=["GET", "POST"])
@login_required
def asignacion(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM ordenes WHERE id = {ph}", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))
    cur.execute(f"SELECT * FROM asignacion WHERE orden_id = {ph}", (orden_id,))
    asignacion_actual = cur.fetchone()
    conn.close()

    if request.method == "POST":
        fecha_salida = request.form.get("fecha_salida_maquila", "").strip()
        maquilero = request.form.get("nombre_maquilero", "").strip()
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()

        conn = get_db()
        cur = conn.cursor()
        if asignacion_actual:
            if USE_POSTGRES:
                cur.execute("""
                    UPDATE asignacion SET fecha_salida_maquila=%s, nombre_maquilero=%s, usuario=%s,
                    observaciones=%s, fecha_registro=CURRENT_TIMESTAMP WHERE orden_id=%s
                """, (fecha_salida, maquilero, usuario, observaciones, orden_id))
            else:
                cur.execute("""
                    UPDATE asignacion SET fecha_salida_maquila=?, nombre_maquilero=?, usuario=?,
                    observaciones=?, fecha_registro=CURRENT_TIMESTAMP WHERE orden_id=?
                """, (fecha_salida, maquilero, usuario, observaciones, orden_id))
            accion = "Asignación modificada"
        else:
            if USE_POSTGRES:
                cur.execute("""
                    INSERT INTO asignacion (orden_id, fecha_salida_maquila, nombre_maquilero, usuario, observaciones)
                    VALUES (%s, %s, %s, %s, %s)
                """, (orden_id, fecha_salida, maquilero, usuario, observaciones))
            else:
                cur.execute("""
                    INSERT INTO asignacion (orden_id, fecha_salida_maquila, nombre_maquilero, usuario, observaciones)
                    VALUES (?, ?, ?, ?, ?)
                """, (orden_id, fecha_salida, maquilero, usuario, observaciones))
            accion = "Asignación realizada"

        if USE_POSTGRES:
            cur.execute("UPDATE ordenes SET estado_actual = 'Asignacion' WHERE id = %s", (orden_id,))
        else:
            cur.execute("UPDATE ordenes SET estado_actual = 'Asignacion' WHERE id = ?", (orden_id,))
        conn.commit()
        conn.close()
        registrar_historial(orden_id, "Asignacion", accion, usuario, f"Maquilero: {maquilero} | Salida: {fecha_salida}")
        flash("Asignación guardada", "success")
        return redirect(url_for("ver_orden", orden_id=orden_id))

    return render_template("asignacion.html", orden=orden, asignacion=asignacion_actual)


@app.route("/habilitado/<int:orden_id>", methods=["GET", "POST"])
@login_required
def habilitado(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM ordenes WHERE id = {ph}", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))
    cur.execute(f"SELECT * FROM habilitado WHERE orden_id = {ph}", (orden_id,))
    hab_actual = cur.fetchone()
    conn.close()

    if request.method == "POST":
        estado = request.form.get("estado", "Parcial")
        usuario = session.get("nombre") or session.get("usuario")
        observaciones = request.form.get("observaciones", "").strip()

        conn = get_db()
        cur = conn.cursor()
        if hab_actual:
            if USE_POSTGRES:
                cur.execute("""
                    UPDATE habilitado SET estado=%s, usuario=%s, observaciones=%s, fecha_registro=CURRENT_TIMESTAMP
                    WHERE orden_id=%s
                """, (estado, usuario, observaciones, orden_id))
            else:
                cur.execute("""
                    UPDATE habilitado SET estado=?, usuario=?, observaciones=?, fecha_registro=CURRENT_TIMESTAMP
                    WHERE orden_id=?
                """, (estado, usuario, observaciones, orden_id))
            accion = "Habilitado actualizado"
        else:
            if USE_POSTGRES:
                cur.execute("INSERT INTO habilitado (orden_id, estado, usuario, observaciones) VALUES (%s, %s, %s, %s)",
                            (orden_id, estado, usuario, observaciones))
            else:
                cur.execute("INSERT INTO habilitado (orden_id, estado, usuario, observaciones) VALUES (?, ?, ?, ?)",
                            (orden_id, estado, usuario, observaciones))
            accion = "Habilitado registrado"

        if USE_POSTGRES:
            cur.execute("UPDATE ordenes SET estado_actual = 'Habilitado' WHERE id = %s", (orden_id,))
        else:
            cur.execute("UPDATE ordenes SET estado_actual = 'Habilitado' WHERE id = ?", (orden_id,))
        conn.commit()
        conn.close()
        registrar_historial(orden_id, "Habilitado", accion, usuario, f"Estado: {estado}")
        flash("Habilitado guardado", "success")
        return redirect(url_for("ver_orden", orden_id=orden_id))

    return render_template("habilitado.html", orden=orden, habilitado=hab_actual)


@app.route("/maquila/<int:orden_id>", methods=["GET", "POST"])
@login_required
def maquila(orden_id):
    conn = get_db()
    cur = dict_cursor(conn)
    ph = "%s" if USE_POSTGRES else "?"
    cur.execute(f"SELECT * FROM ordenes WHERE id = {ph}", (orden_id,))
    orden = cur.fetchone()
    if not orden:
        flash("Orden no encontrada", "error")
        conn.close()
        return redirect(url_for("index"))
    cur.execute(f"SELECT * FROM maquila WHERE orden_id = {ph}", (orden_id,))
    maquila_actual = cur.fetchone()
    cur.execute(f"SELECT * FROM habilitado WHERE orden_id = {ph}", (orden_id,))
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
            if maquila_actual:
                if USE_POSTGRES:
                    cur.execute("UPDATE maquila SET fecha_envio=%s, usuario_envio=%s, observaciones=%s WHERE orden_id=%s",
                                (fecha, usuario, observaciones, orden_id))
                else:
                    cur.execute("UPDATE maquila SET fecha_envio=?, usuario_envio=?, observaciones=? WHERE orden_id=?",
                                (fecha, usuario, observaciones, orden_id))
            else:
                if USE_POSTGRES:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_envio, usuario_envio, observaciones) VALUES (%s, %s, %s, %s)",
                                (orden_id, fecha, usuario, observaciones))
                else:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_envio, usuario_envio, observaciones) VALUES (?, ?, ?, ?)",
                                (orden_id, fecha, usuario, observaciones))
            if USE_POSTGRES:
                cur.execute("UPDATE ordenes SET estado_actual = 'En_Maquila' WHERE id = %s", (orden_id,))
            else:
                cur.execute("UPDATE ordenes SET estado_actual = 'En_Maquila' WHERE id = ?", (orden_id,))
            registrar_historial(orden_id, "Maquila", "Enviado a maquila", usuario, observaciones)
            flash("Orden enviada a maquila", "success")

        elif accion == "regresar":
            if maquila_actual:
                if USE_POSTGRES:
                    cur.execute("UPDATE maquila SET fecha_regreso=%s, usuario_regreso=%s, observaciones=%s WHERE orden_id=%s",
                                (fecha, usuario, observaciones, orden_id))
                else:
                    cur.execute("UPDATE maquila SET fecha_regreso=?, usuario_regreso=?, observaciones=? WHERE orden_id=?",
                                (fecha, usuario, observaciones, orden_id))
            else:
                if USE_POSTGRES:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_regreso, usuario_regreso, observaciones) VALUES (%s, %s, %s, %s)",
                                (orden_id, fecha, usuario, observaciones))
                else:
                    cur.execute("INSERT INTO maquila (orden_id, fecha_regreso, usuario_regreso, observaciones) VALUES (?, ?, ?, ?)",
                                (orden_id, fecha, usuario, observaciones))
            if USE_POSTGRES:
                cur.execute("UPDATE ordenes SET estado_actual = 'Terminado' WHERE id = %s", (orden_id,))
            else:
                cur.execute("UPDATE ordenes SET estado_actual = 'Terminado' WHERE id = ?", (orden_id,))
            registrar_historial(orden_id, "Maquila", "Regreso de maquila - TERMINADO", usuario, observaciones)
            flash("Orden marcada como TERMINADA", "success")

        conn.commit()
        conn.close()
        return redirect(url_for("ver_orden", orden_id=orden_id))

    return render_template("maquila.html", orden=orden, maquila=maquila_actual, habilitado=hab)


# Inicializar DB al arrancar
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"Error init_db: {e}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=not USE_POSTGRES)
