#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema de Producción - Completo + editable
"""

from flask import Flask, request, redirect, url_for, session, render_template_string
from functools import wraps
from datetime import datetime, timedelta
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


def dcur(conn):
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
                punto_id INT, programa_id INT, tipo TEXT DEFAULT 'Programa',
                modelo TEXT, color TEXT, tallas_json TEXT DEFAULT '{}',
                piezas_programadas INT DEFAULT 0, piezas_cortadas INT DEFAULT 0,
                fecha_inicio_corte TEXT, fecha_final_corte TEXT,
                fecha_tampografia TEXT, tampografia_lista TEXT DEFAULT 'No',
                estado_actual TEXT DEFAULT 'Corte',
                habilitado_estado TEXT, habilitado_usuario TEXT, habilitado_obs TEXT,
                maquilero TEXT, fecha_salida_maquila TEXT, fecha_entrega_maquila TEXT,
                maquila_usuario TEXT, maquila_obs TEXT,
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP, creado_por TEXT
            );
        """)
        for sql in [
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_confirmado INT DEFAULT 0",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_usuario TEXT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_fecha TEXT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS trazo_obs TEXT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS orden_id INT",
            "ALTER TABLE puntos ADD COLUMN IF NOT EXISTS estado TEXT DEFAULT 'Pendiente Trazo'",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS punto_id INT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS programa_id INT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS tipo TEXT DEFAULT 'Programa'",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS modelo TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS color TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS tallas_json TEXT DEFAULT '{}'",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS piezas_programadas INT DEFAULT 0",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS piezas_cortadas INT DEFAULT 0",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS fecha_inicio_corte TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS fecha_final_corte TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS fecha_tampografia TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS tampografia_lista TEXT DEFAULT 'No'",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS habilitado_estado TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS habilitado_usuario TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS habilitado_obs TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS maquilero TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS fecha_salida_maquila TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS fecha_entrega_maquila TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS maquila_usuario TEXT",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS maquila_obs TEXT",
        ]:
            try: cur.execute(sql)
            except: pass
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
                punto_id INTEGER, programa_id INTEGER, tipo TEXT DEFAULT 'Programa',
                modelo TEXT, color TEXT, tallas_json TEXT DEFAULT '{}',
                piezas_programadas INTEGER DEFAULT 0, piezas_cortadas INTEGER DEFAULT 0,
                fecha_inicio_corte TEXT, fecha_final_corte TEXT,
                fecha_tampografia TEXT, tampografia_lista TEXT DEFAULT 'No',
                estado_actual TEXT DEFAULT 'Corte',
                habilitado_estado TEXT, habilitado_usuario TEXT, habilitado_obs TEXT,
                maquilero TEXT, fecha_salida_maquila TEXT, fecha_entrega_maquila TEXT,
                maquila_usuario TEXT, maquila_obs TEXT,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP, creado_por TEXT
            );
        """)
    conn.commit()
    cur.execute("SELECT COUNT(*) FROM usuarios")
    row = cur.fetchone()
    c = row[0] if not isinstance(row, dict) else list(row.values())[0]
    if c == 0:
        def h(p): return hashlib.sha256(p.encode()).hexdigest()
        for u in [
            ("admin", h("admin123"), "Administrador", "Admin"),
            ("programa", h("programa123"), "Programa", "Programa"),
            ("trazo", h("trazo123"), "Trazo", "Trazo"),
            ("corte", h("corte123"), "Corte", "Corte"),
            ("gerente", h("gerente123"), "Gerente", "Gerente"),
            ("habilitado", h("habilitado123"), "Habilitado", "Habilitado"),
            ("DISEÑO", h("DISEÑO123"), "Diseño", "Diseño"),
        ]:
            if USE_POSTGRES:
                cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area) VALUES (%s,%s,%s,%s)", u)
            else:
                cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area) VALUES (?,?,?,?)", u)
        conn.commit()

    # Asegurar usuario DISEÑO (solo consulta)
    try:
        if USE_POSTGRES:
            cur.execute("SELECT id FROM usuarios WHERE usuario=%s", ("DISEÑO",))
            if not cur.fetchone():
                cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area) VALUES (%s,%s,%s,%s)",
                            ("DISEÑO", hashlib.sha256("DISEÑO123".encode()).hexdigest(), "Diseño", "Diseño"))
                conn.commit()
        else:
            cur.execute("SELECT id FROM usuarios WHERE usuario=?", ("DISEÑO",))
            if not cur.fetchone():
                cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area) VALUES (?,?,?,?)",
                            ("DISEÑO", hashlib.sha256("DISEÑO123".encode()).hexdigest(), "Diseño", "Diseño"))
                conn.commit()
    except Exception as e:
        print("diseno user:", e)
    conn.close()
    print("✓ DB lista")



def hp(p): return hashlib.sha256(p.encode()).hexdigest()



def can_edit():
    """Usuario Diseño solo puede ver, no modificar."""
    area = (session.get("area") or "").lower()
    usuario = (session.get("usuario") or "").lower()
    if area == "diseño" or area == "diseno" or usuario == "diseño" or usuario == "diseno":
        return False
    return True



def edit_required(f):
    @wraps(f)
    def d(*a, **k):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if not can_edit():
            return page("Solo lectura",
                '<div class="alert alert-err">Tu usuario (Diseño) solo puede consultar. No tiene permisos para modificar o crear.</div>'
                '<a href="/" class="btn btn-outline">Volver al inicio</a>', session)
        return f(*a, **k)
    return d


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
.nav{background:#0f2744;color:#fff;padding:.8rem 1.3rem;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.5rem}
.nav a{color:rgba(255,255,255,.9);text-decoration:none;margin-left:.85rem;font-size:.84rem}
.container{max-width:1050px;margin:1.3rem auto;padding:0 1rem}
.card{background:#fff;border-radius:12px;padding:1.2rem;margin-bottom:1.1rem;box-shadow:0 1px 6px rgba(0,0,0,.07);border:1px solid #e2e8f0}
h1{font-size:1.3rem;color:#0f2744;margin-bottom:.35rem}
h2{font-size:1.05rem;color:#0f2744;margin-bottom:.6rem}
.btn{display:inline-block;padding:.45rem .9rem;border-radius:8px;border:none;font-weight:600;cursor:pointer;text-decoration:none;font-size:.84rem}
.btn-primary{background:#3b82f6;color:#fff}.btn-success{background:#059669;color:#fff}
.btn-warning{background:#d97706;color:#fff}.btn-outline{background:#fff;border:1px solid #cbd5e1;color:#475569}
.btn-danger{background:#dc2626;color:#fff}.btn-sm{padding:.25rem .55rem;font-size:.75rem}
.alert{padding:.7rem 1rem;border-radius:8px;margin-bottom:.9rem}
.alert-ok{background:#d1fae5;color:#065f46}.alert-err{background:#fee2e2;color:#991b1b}
table{width:100%;border-collapse:collapse;font-size:.84rem}
th{background:#f8fafc;padding:.55rem;text-align:left;border-bottom:2px solid #e2e8f0;font-size:.72rem;text-transform:uppercase;color:#64748b}
td{padding:.5rem;border-bottom:1px solid #f1f5f9}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.68rem;font-weight:600}
.badge-pend{background:#fef3c7;color:#92400e}.badge-ok{background:#d1fae5;color:#065f46}
.badge-info{background:#dbeafe;color:#1e40af}.badge-warn{background:#ffedd5;color:#9a3412}
label{display:block;font-weight:600;margin-bottom:.2rem;font-size:.82rem}
input,select,textarea{width:100%;padding:.48rem .7rem;border:1px solid #cbd5e1;border-radius:8px;margin-bottom:.75rem;font-size:.88rem}
.form-row{display:flex;gap:.8rem;flex-wrap:wrap}.form-row>div{flex:1;min-width:120px}
.tallas{display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:.55rem}
.tallas div{text-align:center}.tallas input{width:54px;margin:0}.tallas label{font-size:.68rem}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
@media(max-width:700px){.grid2{grid-template-columns:1fr}}
"""

def page(title, body, user=None):
    nav = ""
    if user:
        if can_edit():
            nav = f'''<div class="nav"><div><strong>Sistema de Producción</strong>
            <a href="/">Inicio</a><a href="/programas">Programas</a>
            <a href="/ordenes">Órdenes</a><a href="/orden/especial">+ Especial</a>
            <a href="/agenda">Agenda</a></div>
            <div>{user.get("nombre","")} ({user.get("area","")}) <a href="/logout">Salir</a></div></div>'''
        else:
            nav = f'''<div class="nav"><div><strong>Sistema de Producción</strong>
            <a href="/">Inicio</a><a href="/programas">Programas</a>
            <a href="/ordenes">Órdenes</a>
            <a href="/agenda">Agenda</a>
            <span style="margin-left:1rem;font-size:.8rem;opacity:.85">(Solo lectura)</span></div>
            <div>{user.get("nombre","")} ({user.get("area","")}) <a href="/logout">Salir</a></div></div>'''
    return f'<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{CSS}</style></head><body>{nav}<div class="container">{body}</div></body></html>'


@app.route("/login", methods=["GET","POST"])
def login():
    err = ""
    if request.method == "POST":
        u = request.form.get("usuario","").strip()
        p = request.form.get("password","")
        try:
            conn = get_db(); cur = dcur(conn)
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
        <p style="text-align:center;color:#64748b;margin-bottom:1rem">Inicia sesión</p>
        {"<div class='alert alert-err'>"+err+"</div>" if err else ""}
        <form method="POST"><label>Usuario</label><input name="usuario" required autofocus>
        <label>Contraseña</label><input type="password" name="password" required>
        <button class="btn btn-primary" style="width:100%;padding:.7rem">Entrar</button></form>
        </div>'''
    return page("Login", body)


@app.route("/logout")
def logout():
    session.clear(); return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    conn = get_db(); cur = dcur(conn)
    cur.execute("SELECT COUNT(*) as c FROM programas")
    row = cur.fetchone()
    nprog = row["c"] if isinstance(row, dict) else row[0]
    cur.execute("SELECT COUNT(*) as c FROM ordenes")
    row = cur.fetchone()
    nord = row["c"] if isinstance(row, dict) else row[0]
    cur.execute("SELECT * FROM ordenes ORDER BY id DESC LIMIT 12")
    ordenes = cur.fetchall()
    conn.close()
    rows = ""
    for o in ordenes:
        rows += f'''<tr><td><strong>{o["numero_orden"]}</strong></td>
            <td>{o.get("modelo") or "—"} / {o.get("color") or ""}</td>
            <td>{o.get("piezas_programadas") or 0}</td>
            <td>{o.get("piezas_cortadas") or 0}</td>
            <td><span class="badge badge-info">{o["estado_actual"]}</span></td>
            <td><a href="/orden/{o["id"]}" class="btn btn-outline btn-sm">Ver</a></td></tr>'''
    body = f'''<div class="card"><h1>Panel de Producción</h1>
        <p style="color:#64748b">{nprog} programas · {nord} órdenes</p>
        <div style="margin-top:.8rem;display:flex;gap:.55rem;flex-wrap:wrap">
            <a href="/programa/nuevo" class="btn btn-primary">+ Programa</a>
            <a href="/orden/especial" class="btn btn-warning">+ Pedido Especial</a>
            <a href="/agenda" class="btn btn-outline">📅 Agenda</a>
        </div></div>
        <div class="card"><h2>Órdenes recientes</h2>
        {"<table><thead><tr><th>Orden</th><th>Modelo</th><th>Prog.</th><th>Cortadas</th><th>Estado</th><th></th></tr></thead><tbody>"+rows+"</tbody></table>" if rows else "<p style='color:#64748b'>Sin órdenes aún.</p>"}</div>'''
    return page("Inicio", body, session)


@app.route("/programas")
@login_required
def programas():
    conn = get_db(); cur = dcur(conn)
    cur.execute("SELECT * FROM programas ORDER BY id DESC")
    progs = cur.fetchall(); conn.close()
    rows = "".join(f'''<tr><td><strong>{p["numero_programa"]}</strong></td>
        <td><span class="badge badge-info">{p["estado"]}</span></td>
        <td>{p["creado_por"] or "—"}</td>
        <td>
            <a href="/programa/{p["id"]}" class="btn btn-outline btn-sm">Ver</a>
            <a href="/programa/editar/{p["id"]}" class="btn btn-outline btn-sm">Editar</a>
        </td></tr>''' for p in progs)
    body = f'''<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.55rem">
        <h1 style="margin:0">Programas de Corte</h1>
        <a href="/programa/nuevo" class="btn btn-primary">+ Nuevo</a></div></div>
        <div class="card">{"<table><thead><tr><th>Programa</th><th>Estado</th><th>Creado</th><th></th></tr></thead><tbody>"+rows+"</tbody></table>" if rows else "<p style='color:#64748b'>No hay programas.</p>"}</div>'''
    return page("Programas", body, session)


@app.route("/programa/nuevo", methods=["GET","POST"])
@login_required
@edit_required
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
                        cur.execute("INSERT INTO puntos (programa_id,punto,modelo,color,tallas_json) VALUES (%s,%s,%s,%s,%s)",
                                    (pid, puntos[i].strip(), modelos[i].strip(), colores[i].strip(), tj))
                    else:
                        cur.execute("INSERT INTO puntos (programa_id,punto,modelo,color,tallas_json) VALUES (?,?,?,?,?)",
                                    (pid, puntos[i].strip(), modelos[i].strip(), colores[i].strip(), tj))
            conn.commit()
            return redirect(url_for("ver_programa", prog_id=pid))
        except Exception as e:
            conn.rollback()
            return page("Error", f'<div class="alert alert-err">{e}</div><a href="/programa/nuevo" class="btn btn-outline">Volver</a>', session)
        finally:
            conn.close()
    body = _form_programa(None, [], "")
    return page("Nuevo Programa", body, session)


@app.route("/programa/editar/<int:prog_id>", methods=["GET","POST"])
@login_required
@edit_required
def programa_editar(prog_id):
    conn = get_db(); cur = dcur(conn)
    cur.execute(f"SELECT * FROM programas WHERE id={ph()}", (prog_id,))
    prog = cur.fetchone()
    if not prog: conn.close(); return redirect(url_for("programas"))
    cur.execute(f"SELECT * FROM puntos WHERE programa_id={ph()} ORDER BY id", (prog_id,))
    puntos = cur.fetchall(); conn.close()

    if request.method == "POST":
        num = request.form.get("numero_programa","").strip()
        obs = request.form.get("observaciones","").strip()
        pts = request.form.getlist("punto[]")
        modelos = request.form.getlist("modelo[]")
        colores = request.form.getlist("color[]")
        tjs = request.form.getlist("tallas_json[]")
        ids_existentes = request.form.getlist("punto_id[]")
        conn = get_db(); cur = conn.cursor()
        try:
            if USE_POSTGRES:
                cur.execute("UPDATE programas SET numero_programa=%s, observaciones=%s WHERE id=%s", (num, obs, prog_id))
            else:
                cur.execute("UPDATE programas SET numero_programa=?, observaciones=? WHERE id=?", (num, obs, prog_id))
            # Actualizar / insertar puntos
            for i in range(len(pts)):
                if not pts[i].strip(): continue
                tj = tjs[i] if i < len(tjs) else "{}"
                pid_exist = ids_existentes[i] if i < len(ids_existentes) else ""
                if pid_exist and pid_exist.isdigit():
                    if USE_POSTGRES:
                        cur.execute("UPDATE puntos SET punto=%s,modelo=%s,color=%s,tallas_json=%s WHERE id=%s AND programa_id=%s",
                                    (pts[i].strip(), modelos[i].strip(), colores[i].strip(), tj, int(pid_exist), prog_id))
                    else:
                        cur.execute("UPDATE puntos SET punto=?,modelo=?,color=?,tallas_json=? WHERE id=? AND programa_id=?",
                                    (pts[i].strip(), modelos[i].strip(), colores[i].strip(), tj, int(pid_exist), prog_id))
                else:
                    if USE_POSTGRES:
                        cur.execute("INSERT INTO puntos (programa_id,punto,modelo,color,tallas_json) VALUES (%s,%s,%s,%s,%s)",
                                    (prog_id, pts[i].strip(), modelos[i].strip(), colores[i].strip(), tj))
                    else:
                        cur.execute("INSERT INTO puntos (programa_id,punto,modelo,color,tallas_json) VALUES (?,?,?,?,?)",
                                    (prog_id, pts[i].strip(), modelos[i].strip(), colores[i].strip(), tj))
            conn.commit()
            return redirect(url_for("ver_programa", prog_id=prog_id))
        except Exception as e:
            conn.rollback()
            return page("Error", f'<div class="alert alert-err">{e}</div>', session)
        finally:
            conn.close()

    body = _form_programa(prog, puntos, prog.get("observaciones") or "")
    return page("Editar Programa", body, session)


def _form_programa(prog, puntos, obs):
    num_val = prog["numero_programa"] if prog else ""
    titulo = f"Editar Programa: {num_val}" if prog else "Nuevo Programa de Corte"
    puntos_js = ""
    if puntos:
        for p in puntos:
            try: t = json.loads(p["tallas_json"] or "{}")
            except: t = {}
            puntos_js += f'addP("{p.get("id") or ""}","{p["punto"]}","{p["modelo"]}","{p["color"]}",{json.dumps(t)});'
    else:
        puntos_js = "addP('','','','',{});"
    return f'''<div class="card"><h1>{titulo}</h1>
    <form method="POST"><label>Número de Programa *</label>
    <input name="numero_programa" required value="{num_val}" placeholder="PROG-2026-001">
    <label>Observaciones</label><textarea name="observaciones" rows="2">{obs}</textarea>
    <h2 style="margin-top:1rem">Puntos</h2><div id="puntos"></div>
    <button type="button" class="btn btn-outline btn-sm" onclick="addP('','','','',{{}})" style="margin:.5rem 0 1rem">+ Punto</button>
    <div><button type="submit" class="btn btn-primary">Guardar</button>
    <a href="{"/programa/"+str(prog["id"]) if prog else "/programas"}" class="btn btn-outline">Cancelar</a></div></form></div>
    <script>
    const T=["XS","S","M","L","XL","XXL","3XL","4XL","5XL","6XL"]; let i=0;
    function addP(id,pto,mod,col,tallas){{
        const c=document.getElementById("puntos"); const d=document.createElement("div");
        d.className="card"; d.style="padding:.9rem;background:#f8fafc;margin-bottom:.5rem";
        d.innerHTML=`<input type="hidden" name="punto_id[]" value="${{id||''}}">
        <div class="form-row"><div><label>Punto</label><input name="punto[]" required value="${{pto||''}}"></div>
        <div><label>Modelo</label><input name="modelo[]" required value="${{mod||''}}"></div>
        <div><label>Color</label><input name="color[]" required value="${{col||''}}"></div></div>
        <label>Cantidades por talla</label><div class="tallas" id="t${{i}}"></div>
        <input type="hidden" name="tallas_json[]" id="j${{i}}" value='${{JSON.stringify(tallas||{{}})}}'>`;
        c.appendChild(d); const g=document.getElementById("t"+i);
        T.forEach(t=>{{const x=document.createElement("div");
        const v=(tallas&&tallas[t])?tallas[t]:0;
        x.innerHTML=`<label>${{t}}</label><input type="number" min="0" value="${{v}}" data-t="${{t}}" data-i="${{i}}" onchange="upd(${{i}})">`;
        g.appendChild(x)}}); i++;
    }}
    function upd(idx){{const o={{}}; document.querySelectorAll(`input[data-i="${{idx}}"]`).forEach(el=>{{if(+el.value>0)o[el.dataset.t]=+el.value}});
    document.getElementById("j"+idx).value=JSON.stringify(o)}}
    {puntos_js}
    </script>'''


@app.route("/programa/<int:prog_id>")
@login_required
def ver_programa(prog_id):
    conn = get_db(); cur = dcur(conn)
    cur.execute(f"SELECT * FROM programas WHERE id={ph()}", (prog_id,))
    prog = cur.fetchone()
    if not prog: conn.close(); return redirect(url_for("programas"))
    cur.execute(f"SELECT * FROM puntos WHERE programa_id={ph()} ORDER BY id", (prog_id,))
    puntos = cur.fetchall(); conn.close()
    rows = ""
    for p in puntos:
        try: tallas = json.loads(p["tallas_json"] or "{}")
        except: tallas = {}
        th = " ".join(f'<span class="badge badge-info">{k}:{v}</span>' for k,v in tallas.items()) or "—"
        prog_piezas = sum(int(v) for v in tallas.values() if str(v).isdigit())
        if p.get("trazo_confirmado"):
            trazo = f'<span class="badge badge-ok">✓ Trazo</span> <a href="/trazo/{p["id"]}" class="btn btn-outline btn-sm">Editar</a>'
        else:
            trazo = f'<a href="/trazo/{p["id"]}" class="btn btn-warning btn-sm">Confirmar Trazo</a>'
        if p.get("trazo_confirmado") and not p.get("orden_id"):
            orden = f'<a href="/corte/desde-punto/{p["id"]}" class="btn btn-primary btn-sm">Asignar Orden</a>'
        elif p.get("orden_id"):
            orden = f'<a href="/orden/{p["orden_id"]}" class="btn btn-outline btn-sm">Ver Orden</a>'
        else:
            orden = "—"
        rows += f'''<tr><td><strong>{p["punto"]}</strong></td><td>{p["modelo"]}</td><td>{p["color"]}</td>
            <td>{th}<br><small>{prog_piezas} pzas</small></td><td>{trazo}</td><td>{orden}</td></tr>'''
    body = f'''<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.55rem">
        <div><h1 style="margin-bottom:.2rem">Programa: {prog["numero_programa"]}</h1>
        <span class="badge badge-info">{prog["estado"]}</span></div>
        <div>
            <a href="/programa/editar/{prog_id}" class="btn btn-outline">✏️ Editar Programa</a>
            <a href="/programas" class="btn btn-outline">← Volver</a>
        </div></div></div>
        <div class="card"><h2>Puntos</h2>
        <table><thead><tr><th>Punto</th><th>Modelo</th><th>Color</th><th>Tallas</th><th>Trazo</th><th>Orden</th></tr></thead>
        <tbody>{rows or "<tr><td colspan=6>Sin puntos</td></tr>"}</tbody></table></div>'''
    return page(f"Programa {prog['numero_programa']}", body, session)


@app.route("/trazo/<int:punto_id>", methods=["GET","POST"])
@login_required
@edit_required
def trazo_punto(punto_id):
    conn = get_db(); cur = dcur(conn)
    cur.execute(f"SELECT p.*, pr.numero_programa, pr.id as prog_id FROM puntos p JOIN programas pr ON pr.id=p.programa_id WHERE p.id={ph()}", (punto_id,))
    punto = cur.fetchone(); conn.close()
    if not punto: return redirect(url_for("programas"))
    if request.method == "POST":
        user = session.get("nombre") or session.get("usuario")
        obs = request.form.get("observaciones","").strip()
        fecha = datetime.now().strftime("%Y-%m-%d")
        conn = get_db(); cur = conn.cursor()
        if USE_POSTGRES:
            cur.execute("UPDATE puntos SET trazo_confirmado=1,trazo_usuario=%s,trazo_fecha=%s,trazo_obs=%s,estado='Trazo Listo' WHERE id=%s",
                        (user,fecha,obs,punto_id))
        else:
            cur.execute("UPDATE puntos SET trazo_confirmado=1,trazo_usuario=?,trazo_fecha=?,trazo_obs=?,estado='Trazo Listo' WHERE id=?",
                        (user,fecha,obs,punto_id))
        conn.commit(); conn.close()
        return redirect(url_for("ver_programa", prog_id=punto["prog_id"]))
    body = f'''<div class="card"><h1>Confirmar Trazo</h1>
        <p>Programa <strong>{punto["numero_programa"]}</strong> · Punto <strong>{punto["punto"]}</strong> · {punto["modelo"]} / {punto["color"]}</p>
        <form method="POST" style="margin-top:1rem"><label>Observaciones</label>
        <textarea name="observaciones" rows="2">{punto.get("trazo_obs") or ""}</textarea>
        <button type="submit" class="btn btn-success">Confirmar Trazo</button>
        <a href="/programa/{punto["prog_id"]}" class="btn btn-outline">Cancelar</a></form></div>'''
    return page("Trazo", body, session)


@app.route("/corte/desde-punto/<int:punto_id>", methods=["GET","POST"])
@login_required
@edit_required
def corte_desde_punto(punto_id):
    conn = get_db(); cur = dcur(conn)
    cur.execute(f"SELECT p.*, pr.numero_programa, pr.id as prog_id FROM puntos p JOIN programas pr ON pr.id=p.programa_id WHERE p.id={ph()}", (punto_id,))
    punto = cur.fetchone(); conn.close()
    if not punto: return redirect(url_for("programas"))
    try: tallas = json.loads(punto["tallas_json"] or "{}")
    except: tallas = {}
    prog_piezas = sum(int(v) for v in tallas.values() if str(v).isdigit())
    if request.method == "POST":
        num = request.form.get("numero_orden","").strip()
        p_prog = int(request.form.get("piezas_programadas") or prog_piezas)
        p_cort = int(request.form.get("piezas_cortadas") or 0)
        f_ini = request.form.get("fecha_inicio_corte","").strip()
        f_fin = request.form.get("fecha_final_corte","").strip()
        f_tamp = request.form.get("fecha_tampografia","").strip()
        tamp = request.form.get("tampografia_lista","No")
        user = session.get("nombre") or session.get("usuario")
        if not num: return redirect(url_for("corte_desde_punto", punto_id=punto_id))
        conn = get_db(); cur = conn.cursor()
        try:
            if USE_POSTGRES:
                cur.execute("""INSERT INTO ordenes (numero_orden,punto_id,programa_id,tipo,modelo,color,tallas_json,
                    piezas_programadas,piezas_cortadas,fecha_inicio_corte,fecha_final_corte,fecha_tampografia,
                    tampografia_lista,estado_actual,creado_por)
                    VALUES (%s,%s,%s,'Programa',%s,%s,%s,%s,%s,%s,%s,%s,%s,'Corte',%s) RETURNING id""",
                    (num,punto_id,punto["prog_id"],punto["modelo"],punto["color"],punto["tallas_json"],
                     p_prog,p_cort,f_ini,f_fin,f_tamp,tamp,user))
                oid = cur.fetchone()[0]
                cur.execute("UPDATE puntos SET orden_id=%s,estado='Con Orden' WHERE id=%s",(oid,punto_id))
            else:
                cur.execute("""INSERT INTO ordenes (numero_orden,punto_id,programa_id,tipo,modelo,color,tallas_json,
                    piezas_programadas,piezas_cortadas,fecha_inicio_corte,fecha_final_corte,fecha_tampografia,
                    tampografia_lista,estado_actual,creado_por)
                    VALUES (?,?,?,'Programa',?,?,?,?,?,?,?,?,?,'Corte',?)""",
                    (num,punto_id,punto["prog_id"],punto["modelo"],punto["color"],punto["tallas_json"],
                     p_prog,p_cort,f_ini,f_fin,f_tamp,tamp,user))
                oid = cur.lastrowid
                cur.execute("UPDATE puntos SET orden_id=?,estado='Con Orden' WHERE id=?",(oid,punto_id))
            conn.commit()
            return redirect(url_for("ver_orden", orden_id=oid))
        except Exception as e:
            conn.rollback()
            return page("Error", f'<div class="alert alert-err">{e}</div>', session)
        finally:
            conn.close()
    th = " ".join(f'<span class="badge badge-info">{k}:{v}</span>' for k,v in tallas.items())
    body = f'''<div class="card"><h1>Asignar Orden (Corte)</h1>
        <p>Programa <strong>{punto["numero_programa"]}</strong> · Punto <strong>{punto["punto"]}</strong></p>
        <p>{punto["modelo"]} / {punto["color"]} · {th}</p>
        <form method="POST" style="margin-top:1rem">
            <label>Número de Orden *</label><input name="numero_orden" required placeholder="OP-2026-050">
            <div class="form-row">
                <div><label>Piezas Programadas</label><input type="number" name="piezas_programadas" value="{prog_piezas}" min="0"></div>
                <div><label>Piezas Cortadas</label><input type="number" name="piezas_cortadas" value="0" min="0"></div>
            </div>
            <div class="form-row">
                <div><label>Fecha Inicio Corte</label><input type="date" name="fecha_inicio_corte"></div>
                <div><label>Fecha Final Corte</label><input type="date" name="fecha_final_corte"></div>
                <div><label>Fecha Tampografía</label><input type="date" name="fecha_tampografia"></div>
            </div>
            <label>¿Tampografía lista?</label>
            <select name="tampografia_lista"><option value="No">No</option><option value="Si">Sí</option></select>
            <button type="submit" class="btn btn-primary">Crear Orden</button>
            <a href="/programa/{punto["prog_id"]}" class="btn btn-outline">Cancelar</a>
        </form></div>'''
    return page("Asignar Orden", body, session)


@app.route("/orden/especial", methods=["GET","POST"])
@login_required
@edit_required
def orden_especial():
    if request.method == "POST":
        num = request.form.get("numero_orden","").strip()
        modelo = request.form.get("modelo","").strip()
        color = request.form.get("color","").strip()
        p_prog = int(request.form.get("piezas_programadas") or 0)
        p_cort = int(request.form.get("piezas_cortadas") or 0)
        f_ini = request.form.get("fecha_inicio_corte","").strip()
        f_fin = request.form.get("fecha_final_corte","").strip()
        f_tamp = request.form.get("fecha_tampografia","").strip()
        tamp = request.form.get("tampografia_lista","No")
        user = session.get("nombre") or session.get("usuario")
        if not num: return redirect(url_for("orden_especial"))
        conn = get_db(); cur = conn.cursor()
        try:
            if USE_POSTGRES:
                cur.execute("""INSERT INTO ordenes (numero_orden,tipo,modelo,color,piezas_programadas,piezas_cortadas,
                    fecha_inicio_corte,fecha_final_corte,fecha_tampografia,tampografia_lista,estado_actual,creado_por)
                    VALUES (%s,'Especial',%s,%s,%s,%s,%s,%s,%s,%s,'Corte',%s) RETURNING id""",
                    (num,modelo,color,p_prog,p_cort,f_ini,f_fin,f_tamp,tamp,user))
                oid = cur.fetchone()[0]
            else:
                cur.execute("""INSERT INTO ordenes (numero_orden,tipo,modelo,color,piezas_programadas,piezas_cortadas,
                    fecha_inicio_corte,fecha_final_corte,fecha_tampografia,tampografia_lista,estado_actual,creado_por)
                    VALUES (?,'Especial',?,?,?,?,?,?,?,?,'Corte',?)""",
                    (num,modelo,color,p_prog,p_cort,f_ini,f_fin,f_tamp,tamp,user))
                oid = cur.lastrowid
            conn.commit()
            return redirect(url_for("ver_orden", orden_id=oid))
        except Exception as e:
            conn.rollback()
            return page("Error", f'<div class="alert alert-err">{e}</div>', session)
        finally:
            conn.close()
    body = '''<div class="card"><h1>Pedido Especial (sin programa)</h1>
        <form method="POST">
            <label>Número de Orden *</label><input name="numero_orden" required>
            <div class="form-row"><div><label>Modelo</label><input name="modelo"></div>
            <div><label>Color</label><input name="color"></div></div>
            <div class="form-row">
                <div><label>Piezas Programadas</label><input type="number" name="piezas_programadas" value="0" min="0"></div>
                <div><label>Piezas Cortadas</label><input type="number" name="piezas_cortadas" value="0" min="0"></div>
            </div>
            <div class="form-row">
                <div><label>Inicio Corte</label><input type="date" name="fecha_inicio_corte"></div>
                <div><label>Final Corte</label><input type="date" name="fecha_final_corte"></div>
                <div><label>Tampografía</label><input type="date" name="fecha_tampografia"></div>
            </div>
            <label>¿Tampografía lista?</label>
            <select name="tampografia_lista"><option value="No">No</option><option value="Si">Sí</option></select>
            <button type="submit" class="btn btn-primary">Crear</button>
            <a href="/" class="btn btn-outline">Cancelar</a>
        </form></div>'''
    return page("Especial", body, session)


@app.route("/ordenes")
@login_required
def lista_ordenes():
    conn = get_db(); cur = dcur(conn)
    cur.execute("SELECT * FROM ordenes ORDER BY id DESC")
    ordenes = cur.fetchall(); conn.close()
    rows = "".join(f'''<tr><td><strong>{o["numero_orden"]}</strong></td>
        <td>{o.get("tipo") or "—"}</td><td>{o.get("modelo") or "—"} / {o.get("color") or ""}</td>
        <td>{o.get("piezas_programadas") or 0}</td><td>{o.get("piezas_cortadas") or 0}</td>
        <td><span class="badge badge-info">{o["estado_actual"]}</span></td>
        <td><a href="/orden/{o["id"]}" class="btn btn-outline btn-sm">Ver</a></td></tr>''' for o in ordenes)
    body = f'''<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.55rem">
        <h1 style="margin:0">Órdenes</h1><a href="/orden/especial" class="btn btn-warning">+ Especial</a></div></div>
        <div class="card">{"<table><thead><tr><th>Orden</th><th>Tipo</th><th>Modelo</th><th>Prog.</th><th>Cortadas</th><th>Estado</th><th></th></tr></thead><tbody>"+rows+"</tbody></table>" if rows else "<p style='color:#64748b'>Sin órdenes.</p>"}</div>'''
    return page("Órdenes", body, session)


@app.route("/orden/<int:orden_id>", methods=["GET","POST"])
@login_required
def ver_orden(orden_id):
    conn = get_db(); cur = dcur(conn)
    cur.execute(f"SELECT * FROM ordenes WHERE id={ph()}", (orden_id,))
    o = cur.fetchone(); conn.close()
    if not o: return redirect(url_for("lista_ordenes"))
    if request.method == "POST":
        if not can_edit():
            return page("Solo lectura",
                '<div class="alert alert-err">Tu usuario (Diseño) solo puede consultar. No tiene permisos para modificar.</div>'
                f'<a href="/orden/{orden_id}" class="btn btn-outline">Volver</a>', session)
        accion = request.form.get("accion")
        user = session.get("nombre") or session.get("usuario")
        conn = get_db(); cur = conn.cursor()
        if accion == "numero":
            nuevo = request.form.get("numero_orden","").strip()
            if nuevo:
                try:
                    if USE_POSTGRES:
                        cur.execute("UPDATE ordenes SET numero_orden=%s WHERE id=%s", (nuevo, orden_id))
                    else:
                        cur.execute("UPDATE ordenes SET numero_orden=? WHERE id=?", (nuevo, orden_id))
                    conn.commit()
                except Exception as e:
                    conn.rollback()
                    conn.close()
                    return page("Error", f'<div class="alert alert-err">No se pudo cambiar el número: {e}<br>Posiblemente ya existe otra orden con ese número.</div><a href="/orden/{orden_id}" class="btn btn-outline">Volver</a>', session)
            conn.close()
            return redirect(url_for("ver_orden", orden_id=orden_id))
        if accion == "corte":
            vals = (int(request.form.get("piezas_programadas") or 0), int(request.form.get("piezas_cortadas") or 0),
                    request.form.get("fecha_inicio_corte","").strip(), request.form.get("fecha_final_corte","").strip(),
                    request.form.get("fecha_tampografia","").strip(), request.form.get("tampografia_lista","No"), orden_id)
            if USE_POSTGRES:
                cur.execute("""UPDATE ordenes SET piezas_programadas=%s,piezas_cortadas=%s,fecha_inicio_corte=%s,
                    fecha_final_corte=%s,fecha_tampografia=%s,tampografia_lista=%s,estado_actual='Corte' WHERE id=%s""", vals)
            else:
                cur.execute("""UPDATE ordenes SET piezas_programadas=?,piezas_cortadas=?,fecha_inicio_corte=?,
                    fecha_final_corte=?,fecha_tampografia=?,tampografia_lista=?,estado_actual='Corte' WHERE id=?""", vals)
        elif accion == "habilitado":
            if USE_POSTGRES:
                cur.execute("UPDATE ordenes SET habilitado_estado=%s,habilitado_usuario=%s,habilitado_obs=%s,estado_actual='Habilitado' WHERE id=%s",
                            (request.form.get("habilitado_estado","Parcial"), user, request.form.get("habilitado_obs","").strip(), orden_id))
            else:
                cur.execute("UPDATE ordenes SET habilitado_estado=?,habilitado_usuario=?,habilitado_obs=?,estado_actual='Habilitado' WHERE id=?",
                            (request.form.get("habilitado_estado","Parcial"), user, request.form.get("habilitado_obs","").strip(), orden_id))
        elif accion == "maquila":
            f_ent = request.form.get("fecha_entrega_maquila","").strip()
            estado = "Terminado" if f_ent else "En_Maquila"
            vals = (request.form.get("maquilero","").strip(), request.form.get("fecha_salida_maquila","").strip(),
                    f_ent, user, request.form.get("maquila_obs","").strip(), estado, orden_id)
            if USE_POSTGRES:
                cur.execute("""UPDATE ordenes SET maquilero=%s,fecha_salida_maquila=%s,fecha_entrega_maquila=%s,
                    maquila_usuario=%s,maquila_obs=%s,estado_actual=%s WHERE id=%s""", vals)
            else:
                cur.execute("""UPDATE ordenes SET maquilero=?,fecha_salida_maquila=?,fecha_entrega_maquila=?,
                    maquila_usuario=?,maquila_obs=?,estado_actual=? WHERE id=?""", vals)
        conn.commit(); conn.close()
        return redirect(url_for("ver_orden", orden_id=orden_id))

    try: tallas = json.loads(o.get("tallas_json") or "{}")
    except: tallas = {}
    th = " ".join(f'<span class="badge badge-info">{k}:{v}</span>' for k,v in tallas.items())
    dif = (o.get("piezas_cortadas") or 0) - (o.get("piezas_programadas") or 0)
    dif_txt = " · <span style='color:#059669'>OK</span>" if dif >= 0 else f" · <span style='color:#dc2626'>Faltan {abs(dif)}</span>"

    body = f'''<div class="card">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.55rem">
            <div><h1 style="margin-bottom:.2rem">Orden: {o["numero_orden"]}</h1>
            <span class="badge badge-info">{o["estado_actual"]}</span>
            <span class="badge badge-warn">{o.get("tipo") or ""}</span></div>
            <div style="display:flex;gap:.4rem;flex-wrap:wrap">
            <a href="/ordenes" class="btn btn-outline">← Órdenes</a>
            {"<form method=\"POST\" action=\"/orden/eliminar/"+str(o["id"])+"\" onsubmit=\"return confirm('¿Eliminar esta orden? Esta acción no se puede deshacer.')\"><button type=\"submit\" class=\"btn btn-danger btn-sm\">🗑️ Eliminar</button></form>" if (session.get("area")=="Admin" or session.get("usuario")=="admin") else ""}
            </div>
        </div>
        <p style="margin-top:.5rem">{o.get("modelo") or "—"} / {o.get("color") or "—"} {th}</p>
        <details style="margin-top:.6rem"><summary style="cursor:pointer;font-weight:600">✏️ Modificar número de orden</summary>
        <form method="POST" style="margin-top:.5rem;max-width:320px">
            <input type="hidden" name="accion" value="numero">
            <label>Nuevo número de orden</label>
            <input name="numero_orden" required value="{o["numero_orden"]}">
            <button type="submit" class="btn btn-primary btn-sm">Guardar número</button>
        </form></details>
    </div>
    <div class="grid2">
    <div class="card"><h2>1. Corte</h2>
        <p>Programadas: <strong>{o.get("piezas_programadas") or 0}</strong> ·
           Cortadas: <strong>{o.get("piezas_cortadas") or 0}</strong>{dif_txt}</p>
        <p>Inicio: {o.get("fecha_inicio_corte") or "—"} · Fin: {o.get("fecha_final_corte") or "—"}</p>
        <p>Tampografía: {o.get("tampografia_lista") or "No"} ({o.get("fecha_tampografia") or "—"})</p>
        <details style="margin-top:.55rem"><summary style="cursor:pointer;font-weight:600">Editar Corte</summary>
        <form method="POST" style="margin-top:.55rem"><input type="hidden" name="accion" value="corte">
            <div class="form-row">
                <div><label>Programadas</label><input type="number" name="piezas_programadas" value="{o.get("piezas_programadas") or 0}"></div>
                <div><label>Cortadas</label><input type="number" name="piezas_cortadas" value="{o.get("piezas_cortadas") or 0}"></div>
            </div>
            <div class="form-row">
                <div><label>Inicio</label><input type="date" name="fecha_inicio_corte" value="{o.get("fecha_inicio_corte") or ""}"></div>
                <div><label>Final</label><input type="date" name="fecha_final_corte" value="{o.get("fecha_final_corte") or ""}"></div>
                <div><label>Tampografía</label><input type="date" name="fecha_tampografia" value="{o.get("fecha_tampografia") or ""}"></div>
            </div>
            <label>¿Tampografía lista?</label>
            <select name="tampografia_lista">
                <option value="No" {"selected" if o.get("tampografia_lista")=="No" else ""}>No</option>
                <option value="Si" {"selected" if o.get("tampografia_lista")=="Si" else ""}>Sí</option>
            </select>
            <button type="submit" class="btn btn-primary btn-sm">Guardar</button>
        </form></details>
    </div>
    <div class="card"><h2>2. Habilitado</h2>
        <p>Estado: <strong>{o.get("habilitado_estado") or "Pendiente"}</strong></p>
        <p>{o.get("habilitado_usuario") or ""} {o.get("habilitado_obs") or ""}</p>
        <details style="margin-top:.55rem"><summary style="cursor:pointer;font-weight:600">Registrar / Editar</summary>
        <form method="POST" style="margin-top:.55rem"><input type="hidden" name="accion" value="habilitado">
            <label>Estado</label>
            <select name="habilitado_estado"><option value="Completo">Completo</option><option value="Parcial" selected>Parcial</option></select>
            <label>Observaciones</label><textarea name="habilitado_obs" rows="2">{o.get("habilitado_obs") or ""}</textarea>
            <button type="submit" class="btn btn-primary btn-sm">Guardar</button>
        </form></details>
    </div>
    </div>
    <div class="card"><h2>3. Asignación a Maquila</h2>
        <p>Maquilero: <strong>{o.get("maquilero") or "—"}</strong></p>
        <p>Salida: {o.get("fecha_salida_maquila") or "—"} · Entrega: {o.get("fecha_entrega_maquila") or "—"}</p>
        <details style="margin-top:.55rem"><summary style="cursor:pointer;font-weight:600">Registrar / Editar</summary>
        <form method="POST" style="margin-top:.55rem"><input type="hidden" name="accion" value="maquila">
            <div class="form-row">
                <div><label>Maquilero</label><input name="maquilero" value="{o.get("maquilero") or ""}"></div>
                <div><label>Fecha Salida</label><input type="date" name="fecha_salida_maquila" value="{o.get("fecha_salida_maquila") or ""}"></div>
                <div><label>Fecha Entrega</label><input type="date" name="fecha_entrega_maquila" value="{o.get("fecha_entrega_maquila") or ""}"></div>
            </div>
            <label>Observaciones</label><textarea name="maquila_obs" rows="2">{o.get("maquila_obs") or ""}</textarea>
            <button type="submit" class="btn btn-primary btn-sm">Guardar</button>
        </form></details>
    </div>'''
    return page(f"Orden {o['numero_orden']}", body, session)



@app.route("/orden/eliminar/<int:orden_id>", methods=["POST"])
@login_required
@edit_required
def eliminar_orden(orden_id):
    # Solo admin puede eliminar
    if session.get("area") != "Admin" and session.get("usuario") != "admin":
        return page("No autorizado", '<div class="alert alert-err">Solo el administrador puede eliminar órdenes.</div><a href="/ordenes" class="btn btn-outline">Volver</a>', session)
    conn = get_db(); cur = conn.cursor()
    try:
        # Liberar punto si estaba ligado
        if USE_POSTGRES:
            cur.execute("UPDATE puntos SET orden_id=NULL, estado='Trazo Listo' WHERE orden_id=%s", (orden_id,))
            cur.execute("DELETE FROM ordenes WHERE id=%s", (orden_id,))
        else:
            cur.execute("UPDATE puntos SET orden_id=NULL, estado='Trazo Listo' WHERE orden_id=?", (orden_id,))
            cur.execute("DELETE FROM ordenes WHERE id=?", (orden_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return page("Error", f'<div class="alert alert-err">{e}</div>', session)
    conn.close()
    return redirect(url_for("lista_ordenes"))


@app.route("/agenda")
@login_required
def agenda():
    conn = get_db(); cur = dcur(conn)
    hoy = datetime.now().date()
    trad = {"Monday":"Lunes","Tuesday":"Martes","Wednesday":"Miércoles","Thursday":"Jueves",
            "Friday":"Viernes","Saturday":"Sábado","Sunday":"Domingo"}
    cards = ""
    for i in range(15):
        f = hoy + timedelta(days=i)
        fs = f.strftime("%Y-%m-%d")
        cur.execute(f"SELECT * FROM ordenes WHERE fecha_salida_maquila={ph()} ORDER BY numero_orden", (fs,))
        ords = cur.fetchall()
        n = len(ords)
        piezas = sum((o.get("piezas_cortadas") or o.get("piezas_programadas") or 0) for o in ords)
        hoy_b = ' <span class="badge badge-info">HOY</span>' if fs == hoy.strftime("%Y-%m-%d") else ""
        rows = "".join(f'''<tr><td><strong>{o["numero_orden"]}</strong></td>
            <td>{o.get("maquilero") or "—"}</td>
            <td>{o.get("piezas_cortadas") or o.get("piezas_programadas") or 0}</td>
            <td><a href="/orden/{o["id"]}" class="btn btn-outline btn-sm">Ver</a></td></tr>''' for o in ords)
        cards += f'''<div class="card" style="{"border:2px solid #3b82f6" if fs==hoy.strftime("%Y-%m-%d") else ""}">
            <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:.4rem;margin-bottom:.5rem">
                <h2 style="margin:0">{trad.get(f.strftime("%A"),"")} {f.strftime("%d/%m/%Y")}{hoy_b}</h2>
                <span>{n} orden(es) · {piezas} piezas</span>
            </div>
            {"<table><thead><tr><th>Orden</th><th>Maquilero</th><th>Piezas</th><th></th></tr></thead><tbody>"+rows+"</tbody></table>" if rows else "<p style='color:#94a3b8'>Sin envíos</p>"}
        </div>'''
    conn.close()
    body = f'''<div class="card"><h1>📅 Agenda de Salidas a Maquila</h1>
        <p style="color:#64748b">Próximos 15 días</p></div>{cards}'''
    return page("Agenda", body, session)


try:
    init_db()
except Exception as e:
    print("init:", e)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
