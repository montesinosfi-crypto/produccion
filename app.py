#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Producción v2.1
- Trazo por cada PUNTO (no por programa completo)
- Todo editable
- Migración automática de columnas
"""

from flask import Flask, request, redirect, url_for, session, render_template_string
from functools import wraps
from datetime import datetime
import os, hashlib, json

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_secreta_produccion_2026")

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
USE_POSTGRES = bool(DATABASE_URL)

if USE_POSTGRES:
    import psycopg2, psycopg2.extras
else:
    import sqlite3
    from pathlib import Path
    DB_PATH = Path(__file__).parent / "produccion.db"


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def dict_cur(conn):
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
                id SERIAL PRIMARY KEY, usuario TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, nombre TEXT, area TEXT, activo INT DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS programas (
                id SERIAL PRIMARY KEY, numero_programa TEXT UNIQUE NOT NULL,
                estado TEXT DEFAULT 'En proceso',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT, observaciones TEXT
            );
            CREATE TABLE IF NOT EXISTS puntos (
                id SERIAL PRIMARY KEY,
                programa_id INT REFERENCES programas(id) ON DELETE CASCADE,
                punto TEXT, modelo TEXT, color TEXT,
                tallas_json TEXT DEFAULT '{}',
                orden_id INT, estado TEXT DEFAULT 'Pendiente Trazo',
                trazo_confirmado INT DEFAULT 0,
                trazo_usuario TEXT, trazo_fecha TEXT, trazo_obs TEXT
            );
            CREATE TABLE IF NOT EXISTS ordenes (
                id SERIAL PRIMARY KEY, numero_orden TEXT UNIQUE NOT NULL,
                punto_id INT, programa_id INT,
                estado_actual TEXT DEFAULT 'Corte',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP, creado_por TEXT
            );
        """)
        # Migrar columnas que puedan faltar
        for sql in [
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_confirmado INT DEFAULT 0",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_usuario TEXT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_fecha TEXT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_obs TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS punto_id INT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS programa_id INT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS orden_id INT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS estado TEXT DEFAULT 'Pendiente Trazo'",
        ]:
            try:
                cur.execute(sql)
            except Exception:
                pass
    else:
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL, nombre TEXT, area TEXT, activo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS programas (
                id INTEGER PRIMARY KEY AUTOINCREMENT, numero_programa TEXT UNIQUE NOT NULL,
                estado TEXT DEFAULT 'En proceso', fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                creado_por TEXT, observaciones TEXT
            );
            CREATE TABLE IF NOT EXISTS puntos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, programa_id INTEGER,
                punto TEXT, modelo TEXT, color TEXT, tallas_json TEXT DEFAULT '{}',
                orden_id INTEGER, estado TEXT DEFAULT 'Pendiente Trazo',
                trazo_confirmado INTEGER DEFAULT 0, trazo_usuario TEXT, trazo_fecha TEXT, trazo_obs TEXT
            );
            CREATE TABLE IF NOT EXISTS ordenes (
                id INTEGER PRIMARY KEY AUTOINCREMENT, numero_orden TEXT UNIQUE NOT NULL,
                punto_id INTEGER, programa_id INTEGER, estado_actual TEXT DEFAULT 'Corte',
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP, creado_por TEXT
            );
        """)

    conn.commit()
    cur.execute("SELECT COUNT(*) FROM usuarios")
    row = cur.fetchone()
    c = row[0] if not isinstance(row, dict) else list(row.values())[0]
    if c == 0:
        def h(p): return hashlib.sha256(p.encode()).hexdigest()
        users = [
            ("admin", h("admin123"), "Administrador", "Admin"),
            ("programa", h("programa123"), "Programa de Corte", "Programa"),
            ("trazo", h("trazo123"), "Área de Trazo", "Trazo"),
            ("corte", h("corte123"), "Área de Corte", "Corte"),
            ("gerente", h("gerente123"), "Gerente", "Gerente"),
        ]
        for u in users:
            if USE_POSTGRES:
                cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area) VALUES (%s,%s,%s,%s)", u)
            else:
                cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area) VALUES (?,?,?,?)", u)
        conn.commit()
    conn.close()
    print("✓ DB lista")


def hp(p): return hashlib.sha256(p.encode()).hexdigest()


def login_required(f):
    @wraps(f)
    def d(*a, **k):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*a, **k)
    return d


CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:#f1f5f9;color:#1e293b}
.nav{background:#0f2744;color:#fff;padding:.85rem 1.4rem;display:flex;justify-content:space-between;align-items:center}
.nav a{color:rgba(255,255,255,.9);text-decoration:none;margin-left:1rem;font-size:.88rem}
.container{max-width:1000px;margin:1.4rem auto;padding:0 1rem}
.card{background:#fff;border-radius:12px;padding:1.3rem;margin-bottom:1.1rem;box-shadow:0 1px 6px rgba(0,0,0,.07);border:1px solid #e2e8f0}
h1{font-size:1.35rem;color:#0f2744;margin-bottom:.4rem}
h2{font-size:1.1rem;color:#0f2744;margin-bottom:.7rem}
.btn{display:inline-block;padding:.48rem 1rem;border-radius:8px;border:none;font-weight:600;cursor:pointer;text-decoration:none;font-size:.86rem}
.btn-primary{background:#3b82f6;color:#fff}.btn-success{background:#059669;color:#fff}
.btn-warning{background:#d97706;color:#fff}.btn-outline{background:#fff;border:1px solid #cbd5e1;color:#475569}
.btn-sm{padding:.28rem .65rem;font-size:.78rem}
.alert{padding:.75rem 1rem;border-radius:8px;margin-bottom:1rem}
.alert-ok{background:#d1fae5;color:#065f46}.alert-err{background:#fee2e2;color:#991b1b}
table{width:100%;border-collapse:collapse;font-size:.86rem}
th{background:#f8fafc;padding:.6rem;text-align:left;border-bottom:2px solid #e2e8f0;font-size:.75rem;text-transform:uppercase;color:#64748b}
td{padding:.55rem;border-bottom:1px solid #f1f5f9}
.badge{display:inline-block;padding:.18rem .55rem;border-radius:999px;font-size:.7rem;font-weight:600}
.badge-pend{background:#fef3c7;color:#92400e}.badge-ok{background:#d1fae5;color:#065f46}
.badge-info{background:#dbeafe;color:#1e40af}.badge-warn{background:#ffedd5;color:#9a3412}
label{display:block;font-weight:600;margin-bottom:.22rem;font-size:.84rem}
input,select,textarea{width:100%;padding:.5rem .7rem;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:.85rem;font-size:.9rem}
.form-row{display:flex;gap:.9rem;flex-wrap:wrap}.form-row>div{flex:1;min-width:130px}
.tallas{display:flex;flex-wrap:wrap;gap:.35rem;margin-bottom:.7rem}
.tallas div{text-align:center}.tallas input{width:58px;margin:0}.tallas label{font-size:.7rem}
"""

def page(title, body, user=None):
    nav = ""
    if user:
        nav = f'''<div class="nav"><div><strong>Sistema de Producción</strong>
            <a href="/">Inicio</a><a href="/programa/nuevo">+ Programa</a></div>
            <div>{user.get("nombre","")} ({user.get("area","")}) <a href="/logout">Salir</a></div></div>'''
    return f'<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{CSS}</style></head><body>{nav}<div class="container">{body}</div></body></html>'


@app.route("/login", methods=["GET","POST"])
def login():
    err = ""
    if request.method == "POST":
        u = request.form.get("usuario","").strip()
        p = request.form.get("password","")
        try:
            conn = get_db(); cur = dict_cur(conn)
            cur.execute(f"SELECT * FROM usuarios WHERE usuario={ph()} AND activo=1", (u,))
            user = cur.fetchone(); conn.close()
            if user and user["password_hash"] == hp(p):
                session.update({"user_id":user["id"],"nombre":user["nombre"],"area":user["area"],"usuario":user["usuario"]})
                return redirect(url_for("index"))
            err = "Usuario o contraseña incorrectos"
        except Exception as e:
            err = str(e)
    body = f'''<div style="max-width:380px;margin:3rem auto" class="card">
        <h1 style="text-align:center">Sistema de Producción</h1>
        <p style="text-align:center;color:#64748b;margin-bottom:1.1rem">Inicia sesión</p>
        {"<div class='alert alert-err'>"+err+"</div>" if err else ""}
        <form method="POST"><label>Usuario</label><input name="usuario" required autofocus>
        <label>Contraseña</label><input type="password" name="password" required>
        <button class="btn btn-primary" style="width:100%;padding:.7rem">Entrar</button></form>
        <div style="margin-top:1rem;font-size:.78rem;color:#64748b;background:#f8fafc;padding:.8rem;border-radius:8px">
        admin/admin123 · programa/programa123 · trazo/trazo123 · corte/corte123 · gerente/gerente123</div></div>'''
    return page("Login", body)


@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    conn = get_db(); cur = dict_cur(conn)
    cur.execute("SELECT * FROM programas ORDER BY id DESC LIMIT 30")
    progs = cur.fetchall(); conn.close()
    rows = ""
    for p in progs:
        rows += f'''<tr><td><strong>{p["numero_programa"]}</strong></td>
            <td><span class="badge badge-info">{p["estado"]}</span></td>
            <td>{p["creado_por"] or "—"}</td>
            <td><a href="/programa/{p["id"]}" class="btn btn-outline btn-sm">Ver</a></td></tr>'''
    body = f'''<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.7rem">
        <h1 style="margin:0">Programas de Corte</h1>
        <a href="/programa/nuevo" class="btn btn-primary">+ Nuevo Programa</a></div></div>
        <div class="card">{"<table><thead><tr><th>Programa</th><th>Estado</th><th>Creado por</th><th></th></tr></thead><tbody>"+rows+"</tbody></table>" if rows else "<p style='color:#64748b'>No hay programas.</p>"}</div>'''
    return page("Inicio", body, session)


@app.route("/programa/nuevo", methods=["GET","POST"])
@login_required
def programa_nuevo():
    if request.method == "POST":
        num = request.form.get("numero_programa","").strip()
        obs = request.form.get("observaciones","").strip()
        puntos = request.form.getlist("punto[]")
        modelos = request.form.getlist("modelo[]")
        colores = request.form.getlist("color[]")
        tjs = request.form.getlist("tallas_json[]")
        user = session.get("nombre") or session.get("usuario")
        if not num: return redirect(url_for("programa_nuevo"))
        conn = get_db(); cur = conn.cursor()
        try:
            if USE_POSTGRES:
                cur.execute("INSERT INTO programas (numero_programa,creado_por,observaciones) VALUES (%s,%s,%s) RETURNING id", (num,user,obs))
                pid = cur.fetchone()[0]
            else:
                cur.execute("INSERT INTO programas (numero_programa,creado_por,observaciones) VALUES (?,?,?)", (num,user,obs))
                pid = cur.lastrowid
            for i in range(len(puntos)):
                if puntos[i].strip() and modelos[i].strip():
                    tj = tjs[i] if i < len(tjs) else "{}"
                    if USE_POSTGRES:
                        cur.execute("INSERT INTO puntos (programa_id,punto,modelo,color,tallas_json,estado) VALUES (%s,%s,%s,%s,%s,'Pendiente Trazo')",
                                    (pid, puntos[i].strip(), modelos[i].strip(), colores[i].strip(), tj))
                    else:
                        cur.execute("INSERT INTO puntos (programa_id,punto,modelo,color,tallas_json,estado) VALUES (?,?,?,?,?,'Pendiente Trazo')",
                                    (pid, puntos[i].strip(), modelos[i].strip(), colores[i].strip(), tj))
            conn.commit()
            return redirect(url_for("ver_programa", prog_id=pid))
        except Exception as e:
            conn.rollback()
            return page("Error", f'<div class="alert alert-err">Error: {e}</div><a href="/programa/nuevo" class="btn btn-outline">Volver</a>', session)
        finally:
            conn.close()

    body = '''<div class="card"><h1>Nuevo Programa de Corte</h1>
    <form method="POST"><label>Número de Programa *</label>
    <input name="numero_programa" required placeholder="PROG-2026-001">
    <label>Observaciones</label><textarea name="observaciones" rows="2"></textarea>
    <h2 style="margin-top:1rem">Puntos</h2><div id="puntos"></div>
    <button type="button" class="btn btn-outline btn-sm" onclick="addP()" style="margin:.5rem 0 1rem">+ Agregar punto</button>
    <div><button type="submit" class="btn btn-primary">Crear Programa</button>
    <a href="/" class="btn btn-outline">Cancelar</a></div></form></div>
    <script>
    const T=["XS","S","M","L","XL","XXL","3XL","4XL","5XL","6XL"]; let i=0;
    function addP(){const c=document.getElementById("puntos"); const d=document.createElement("div");
    d.className="card"; d.style="padding:1rem;background:#f8fafc;margin-bottom:.6rem";
    d.innerHTML=`<div class="form-row"><div><label>Punto</label><input name="punto[]" required></div>
    <div><label>Modelo</label><input name="modelo[]" required></div>
    <div><label>Color</label><input name="color[]" required></div></div>
    <label>Cantidades por talla</label><div class="tallas" id="t${i}"></div>
    <input type="hidden" name="tallas_json[]" id="j${i}" value="{}">`;
    c.appendChild(d); const g=document.getElementById("t"+i);
    T.forEach(t=>{const x=document.createElement("div");
    x.innerHTML=`<label>${t}</label><input type="number" min="0" value="0" data-t="${t}" data-i="${i}" onchange="upd(${i})">`;
    g.appendChild(x)}); i++}
    function upd(idx){const o={}; document.querySelectorAll(`input[data-i="${idx}"]`).forEach(el=>{if(+el.value>0)o[el.dataset.t]=+el.value});
    document.getElementById("j"+idx).value=JSON.stringify(o)}
    addP();
    </script>'''
    return page("Nuevo Programa", body, session)


@app.route("/programa/<int:prog_id>")
@login_required
def ver_programa(prog_id):
    conn = get_db(); cur = dict_cur(conn)
    cur.execute(f"SELECT * FROM programas WHERE id={ph()}", (prog_id,))
    prog = cur.fetchone()
    if not prog: conn.close(); return redirect(url_for("index"))
    cur.execute(f"SELECT * FROM puntos WHERE programa_id={ph()} ORDER BY id", (prog_id,))
    puntos = cur.fetchall(); conn.close()

    rows = ""
    for p in puntos:
        try: tallas = json.loads(p["tallas_json"] or "{}")
        except: tallas = {}
        th = " ".join(f'<span class="badge badge-info">{k}:{v}</span>' for k,v in tallas.items()) or "—"
        trazo_ok = p.get("trazo_confirmado")
        if trazo_ok:
            trazo_btn = f'<span class="badge badge-ok">✓ Trazo OK</span> <a href="/trazo/{p["id"]}" class="btn btn-outline btn-sm">Editar</a>'
        else:
            trazo_btn = f'<a href="/trazo/{p["id"]}" class="btn btn-warning btn-sm">Confirmar Trazo</a>'
        if trazo_ok and not p.get("orden_id"):
            orden_btn = f'<a href="/corte/asignar/{p["id"]}" class="btn btn-primary btn-sm">Asignar Orden</a>'
        elif p.get("orden_id"):
            orden_btn = f'<span class="badge badge-ok">Orden #{p["orden_id"]}</span> <a href="/corte/asignar/{p["id"]}" class="btn btn-outline btn-sm">Editar</a>'
        else:
            orden_btn = "—"
        rows += f'''<tr>
            <td><strong>{p["punto"]}</strong></td><td>{p["modelo"]}</td><td>{p["color"]}</td>
            <td>{th}</td><td>{trazo_btn}</td><td>{orden_btn}</td></tr>'''

    body = f'''<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.7rem">
        <div><h1 style="margin-bottom:.25rem">Programa: {prog["numero_programa"]}</h1>
        <span class="badge badge-info">{prog["estado"]}</span></div>
        <a href="/" class="btn btn-outline">← Volver</a></div></div>
        <div class="card"><h2>Puntos del Programa</h2>
        <table><thead><tr><th>Punto</th><th>Modelo</th><th>Color</th><th>Tallas</th><th>Trazo</th><th>Orden</th></tr></thead>
        <tbody>{rows or "<tr><td colspan=6>Sin puntos</td></tr>"}</tbody></table></div>'''
    return page(f"Programa {prog['numero_programa']}", body, session)


# ===== TRAZO POR PUNTO =====
@app.route("/trazo/<int:punto_id>", methods=["GET","POST"])
@login_required
def trazo_punto(punto_id):
    conn = get_db(); cur = dict_cur(conn)
    cur.execute(f"""SELECT p.*, pr.numero_programa, pr.id as prog_id
        FROM puntos p JOIN programas pr ON pr.id=p.programa_id WHERE p.id={ph()}""", (punto_id,))
    punto = cur.fetchone(); conn.close()
    if not punto: return redirect(url_for("index"))

    if request.method == "POST":
        user = session.get("nombre") or session.get("usuario")
        obs = request.form.get("observaciones","").strip()
        fecha = datetime.now().strftime("%Y-%m-%d")
        conn = get_db(); cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("""UPDATE puntos SET trazo_confirmado=1, trazo_usuario=%s, trazo_fecha=%s,
                trazo_obs=%s, estado='Trazo Listo' WHERE id=%s""", (user, fecha, obs, punto_id))
        else:
            cur.execute("""UPDATE puntos SET trazo_confirmado=1, trazo_usuario=?, trazo_fecha=?,
                trazo_obs=?, estado='Trazo Listo' WHERE id=?""", (user, fecha, obs, punto_id))
        conn.commit(); conn.close()
        return redirect(url_for("ver_programa", prog_id=punto["prog_id"]))

    body = f'''<div class="card">
        <h1>Confirmar Trazo del Punto</h1>
        <p>Programa: <strong>{punto["numero_programa"]}</strong> · Punto: <strong>{punto["punto"]}</strong></p>
        <p>{punto["modelo"]} / {punto["color"]}</p>
        <form method="POST" style="margin-top:1rem">
            <label>Observaciones</label><textarea name="observaciones" rows="3">{punto.get("trazo_obs") or ""}</textarea>
            <button type="submit" class="btn btn-success">Confirmar Trazo de este Punto</button>
            <a href="/programa/{punto["prog_id"]}" class="btn btn-outline">Cancelar</a>
        </form></div>'''
    return page("Trazo", body, session)


# ===== ASIGNAR / EDITAR ORDEN =====
@app.route("/corte/asignar/<int:punto_id>", methods=["GET","POST"])
@login_required
def corte_asignar(punto_id):
    conn = get_db(); cur = dict_cur(conn)
    cur.execute(f"""SELECT p.*, pr.numero_programa, pr.id as prog_id
        FROM puntos p JOIN programas pr ON pr.id=p.programa_id WHERE p.id={ph()}""", (punto_id,))
    punto = cur.fetchone()
    orden = None
    if punto and punto.get("orden_id"):
        cur.execute(f"SELECT * FROM ordenes WHERE id={ph()}", (punto["orden_id"],))
        orden = cur.fetchone()
    conn.close()
    if not punto: return redirect(url_for("index"))
    try: tallas = json.loads(punto["tallas_json"] or "{}")
    except: tallas = {}
    total = sum(int(v) for v in tallas.values() if str(v).isdigit())

    if request.method == "POST":
        num = request.form.get("numero_orden","").strip()
        user = session.get("nombre") or session.get("usuario")
        if not num: return redirect(url_for("corte_asignar", punto_id=punto_id))
        conn = get_db(); cur = conn.cursor()
        try:
            if orden:
                # Editar orden existente
                if USE_POSTGRES:
                    cur.execute("UPDATE ordenes SET numero_orden=%s WHERE id=%s", (num, orden["id"]))
                else:
                    cur.execute("UPDATE ordenes SET numero_orden=? WHERE id=?", (num, orden["id"]))
            else:
                if USE_POSTGRES:
                    cur.execute("""INSERT INTO ordenes (numero_orden,punto_id,programa_id,estado_actual,creado_por)
                        VALUES (%s,%s,%s,'Corte',%s) RETURNING id""", (num, punto_id, punto["prog_id"], user))
                    oid = cur.fetchone()[0]
                    cur.execute("UPDATE puntos SET orden_id=%s, estado='Con Orden' WHERE id=%s", (oid, punto_id))
                else:
                    cur.execute("""INSERT INTO ordenes (numero_orden,punto_id,programa_id,estado_actual,creado_por)
                        VALUES (?,?,?,'Corte',?)""", (num, punto_id, punto["prog_id"], user))
                    oid = cur.lastrowid
                    cur.execute("UPDATE puntos SET orden_id=?, estado='Con Orden' WHERE id=?", (oid, punto_id))
            conn.commit()
            return redirect(url_for("ver_programa", prog_id=punto["prog_id"]))
        except Exception as e:
            conn.rollback()
            return page("Error", f'<div class="alert alert-err">Error: {e}</div><a href="/programa/{punto["prog_id"]}" class="btn btn-outline">Volver</a>', session)
        finally:
            conn.close()

    th = " ".join(f'<span class="badge badge-info">{k}:{v}</span>' for k,v in tallas.items())
    valor = orden["numero_orden"] if orden else ""
    body = f'''<div class="card">
        <h1>{"Editar" if orden else "Asignar"} Número de Orden</h1>
        <p>Programa: <strong>{punto["numero_programa"]}</strong> · Punto: <strong>{punto["punto"]}</strong></p>
        <p>{punto["modelo"]} / {punto["color"]} · Piezas: <strong>{total}</strong></p>
        <p style="margin-bottom:1rem">{th}</p>
        <form method="POST">
            <label>Número de Orden *</label>
            <input name="numero_orden" required value="{valor}" placeholder="OP-2026-050">
            <button type="submit" class="btn btn-primary">{"Guardar cambios" if orden else "Crear Orden"}</button>
            <a href="/programa/{punto["prog_id"]}" class="btn btn-outline">Cancelar</a>
        </form></div>'''
    return page("Orden", body, session)


try:
    init_db()
except Exception as e:
    print("init error:", e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
