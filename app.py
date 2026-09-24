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
            CREATE TABLE IF NOT EXISTS notificaciones (
                id SERIAL PRIMARY KEY,
                orden_id INT,
                numero_orden TEXT,
                mensaje TEXT,
                usuario TEXT,
                leida INT DEFAULT 0,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tendidos (
                id SERIAL PRIMARY KEY,
                orden_id INT,
                persona1 TEXT,
                persona2 TEXT,
                fecha_inicio TEXT,
                hora_inicio TEXT,
                fecha_fin TEXT,
                hora_fin TEXT,
                bloques_base INT DEFAULT 0,
                bloques_entretela INT DEFAULT 0,
                bloques_combinacion INT DEFAULT 0,
                observaciones TEXT,
                registrado_por TEXT,
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS ubicacion TEXT DEFAULT 'Taller'",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS piezas_enviadas INT DEFAULT 0",
            "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS piezas_entregadas INT DEFAULT 0",
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
            CREATE TABLE IF NOT EXISTS notificaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER,
                numero_orden TEXT,
                mensaje TEXT,
                usuario TEXT,
                leida INTEGER DEFAULT 0,
                fecha TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS tendidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                orden_id INTEGER,
                persona1 TEXT,
                persona2 TEXT,
                fecha_inicio TEXT,
                hora_inicio TEXT,
                fecha_fin TEXT,
                hora_fin TEXT,
                bloques_base INTEGER DEFAULT 0,
                bloques_entretela INTEGER DEFAULT 0,
                bloques_combinacion INTEGER DEFAULT 0,
                observaciones TEXT,
                registrado_por TEXT,
                fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP
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
    
    # Asegurar usuarios y contraseñas estandar
    try:
        usuarios_std = [
            ("admin", "admin123", "Administrador", "Admin"),
            ("programa", "programa123", "Programa", "Programa"),
            ("trazo", "trazo123", "Trazo", "Trazo"),
            ("corte", "corte123", "Corte", "Corte"),
            ("gerente", "gerente123", "Gerente", "Gerente"),
            ("habilitado", "habilitado123", "Habilitado", "Habilitado"),
            ("DISEÑO", "DISEÑO123", "Diseño", "Diseño"),
            ("ADUANA", "ADUANA123", "Aduana", "Aduana"),
        ]
        for u, pw, nom, area in usuarios_std:
            hpw = hashlib.sha256(pw.encode()).hexdigest()
            if USE_POSTGRES:
                cur.execute("SELECT id FROM usuarios WHERE usuario=%s", (u,))
                row = cur.fetchone()
                if row:
                    cur.execute("UPDATE usuarios SET password_hash=%s, nombre=%s, area=%s, activo=1 WHERE usuario=%s",
                                (hpw, nom, area, u))
                else:
                    cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area,activo) VALUES (%s,%s,%s,%s,1)",
                                (u, hpw, nom, area))
            else:
                cur.execute("SELECT id FROM usuarios WHERE usuario=?", (u,))
                row = cur.fetchone()
                if row:
                    cur.execute("UPDATE usuarios SET password_hash=?, nombre=?, area=?, activo=1 WHERE usuario=?",
                                (hpw, nom, area, u))
                else:
                    cur.execute("INSERT INTO usuarios (usuario,password_hash,nombre,area,activo) VALUES (?,?,?,?,1)",
                                (u, hpw, nom, area))
        conn.commit()
    except Exception as e:
        print("ensure users:", e)

    try:
        if USE_POSTGRES:
            cur.execute("ALTER TABLE tendidos ADD COLUMN IF NOT EXISTS bloques_json TEXT DEFAULT '[]'")
        else:
            try:
                cur.execute("ALTER TABLE tendidos ADD COLUMN bloques_json TEXT DEFAULT '[]'")
            except Exception:
                pass
        conn.commit()
    except Exception as e:
        print("bloques_json col:", e)

    print("✓ DB lista")



def hp(p): return hashlib.sha256(p.encode()).hexdigest()




def badge_estado(est):
    m = {"En_Tendido":("badge-pend","En tendido"),"En_Corte":("badge-pend","En corte"),"Listo_Taller":("badge-info","Listo en taller"),
         "Enviado_Maquila":("badge-warn","Enviado a maquila"),"Entregado_Parcial":("badge-warn","Entrega parcial"),
         "Terminado":("badge-ok","Terminado"),"Corte":("badge-pend","En corte"),
         "En_Maquila":("badge-warn","En maquila"),"Habilitado":("badge-info","Habilitado")}
    cls, label = m.get(est or "", ("badge-info", est or "-"))
    return '<span class="badge %s">%s</span>' % (cls, label)

def badge_ubicacion(ubi):
    if (ubi or "Taller") == "Maquila":
        return '<span class="badge badge-warn">En maquila</span>'
    return '<span class="badge badge-info">En taller de corte</span>'

def week_range_lun_vie(ref=None):
    d = ref or datetime.now().date()
    lun = d - timedelta(days=d.weekday())
    return lun, lun + timedelta(days=4)

def month_range(ref=None):
    d = ref or datetime.now().date()
    ini = d.replace(day=1)
    if d.month == 12:
        fin = d.replace(year=d.year+1, month=1, day=1) - timedelta(days=1)
    else:
        fin = d.replace(month=d.month+1, day=1) - timedelta(days=1)
    return ini, fin


def crear_notificacion(orden_id, numero_orden, mensaje, usuario=None):
    try:
        conn = get_db(); cur = conn.cursor()
        user = usuario or (session.get("nombre") if session else None) or "Sistema"
        if USE_POSTGRES:
            cur.execute("INSERT INTO notificaciones (orden_id,numero_orden,mensaje,usuario) VALUES (%s,%s,%s,%s)",
                        (orden_id, str(numero_orden or ""), mensaje, user))
        else:
            cur.execute("INSERT INTO notificaciones (orden_id,numero_orden,mensaje,usuario) VALUES (?,?,?,?)",
                        (orden_id, str(numero_orden or ""), mensaje, user))
        conn.commit(); conn.close()
    except Exception as e:
        print("notif error:", e)

def count_notificaciones():
    try:
        conn = get_db(); cur = dcur(conn)
        cur.execute("SELECT COUNT(*) as c FROM notificaciones WHERE leida=0")
        row = cur.fetchone(); conn.close()
        return int(row["c"] if isinstance(row, dict) else row[0] or 0)
    except Exception:
        return 0

def list_notificaciones(limit=20):
    try:
        conn = get_db(); cur = dcur(conn)
        if USE_POSTGRES:
            cur.execute("SELECT * FROM notificaciones ORDER BY id DESC LIMIT %s", (int(limit),))
        else:
            cur.execute("SELECT * FROM notificaciones ORDER BY id DESC LIMIT ?", (int(limit),))
        rows = cur.fetchall(); conn.close()
        return rows
    except Exception as e:
        print("list notif", e)
        return []



def parse_num(val):
    """Extrae numero de strings como '2.5 m' o '12'."""
    if val is None:
        return 0.0
    s = str(val).strip().replace(",", ".")
    num = ""
    for ch in s:
        if ch.isdigit() or ch == ".":
            num += ch
        elif num:
            break
    try:
        return float(num) if num else 0.0
    except Exception:
        return 0.0

def metros_bloque(b):
    """Metros de tela = largo x cantidad de lienzos."""
    return parse_num(b.get("largo")) * parse_num(b.get("lienzos"))

def bloques_from_tendido(t):
    try:
        return json.loads(t.get("bloques_json") or "[]")
    except Exception:
        return []

def total_metros_tendido(t):
    return sum(metros_bloque(b) for b in bloques_from_tendido(t))


def horas_laborables_dia(fecha_str):
    """Horas netas del dia segun horario: Lun 8-18 (-1h) = 9; Mar-Vie 8-17:30 (-1h) = 8.5; Sab/Dom 0."""
    try:
        d = datetime.strptime(fecha_str[:10], "%Y-%m-%d").date()
    except Exception:
        return 0.0
    wd = d.weekday()  # 0=lun
    if wd == 0:
        return 9.0
    if 1 <= wd <= 4:
        return 8.5
    return 0.0

def horas_laborables_rango(fi, ff):
    total = 0.0
    try:
        a = datetime.strptime(fi[:10], "%Y-%m-%d").date()
        b = datetime.strptime(ff[:10], "%Y-%m-%d").date()
    except Exception:
        return 0.0
    cur = a
    while cur <= b:
        total += horas_laborables_dia(cur.strftime("%Y-%m-%d"))
        cur = cur + timedelta(days=1)
    return total


def _ventanas_laborables(d):
    """Lista de (inicio, fin) datetime del dia laborable (sin comida 14-15).
    Lun: 8-14 y 15-18. Mar-Vie: 8-14 y 15-17:30. Sab/Dom: vacio.
    """
    wd = d.weekday()
    if wd == 0:  # lunes
        return [
            (datetime(d.year, d.month, d.day, 8, 0), datetime(d.year, d.month, d.day, 14, 0)),
            (datetime(d.year, d.month, d.day, 15, 0), datetime(d.year, d.month, d.day, 18, 0)),
        ]
    if 1 <= wd <= 4:  # mar-vie
        return [
            (datetime(d.year, d.month, d.day, 8, 0), datetime(d.year, d.month, d.day, 14, 0)),
            (datetime(d.year, d.month, d.day, 15, 0), datetime(d.year, d.month, d.day, 17, 30)),
        ]
    return []

def _parse_hm(h):
    """Normaliza hora a HH:MM."""
    if not h:
        return None
    s = str(h).strip()
    parts = s.replace(".", ":").split(":")
    try:
        hh = int(parts[0])
        mm = int(parts[1]) if len(parts) > 1 else 0
        return "%02d:%02d" % (hh, mm)
    except Exception:
        return None

def minutos_tendido(fi, hi, ff, hf):
    """Minutos REALES en jornada (sin noche ni comida 14-15).
    Cruce de dias: corta a fin de jornada y reanuda 8:00.
    """
    try:
        if not fi or not ff:
            return None
        hi_n = _parse_hm(hi) or "08:00"
        hf_n = _parse_hm(hf)
        if not hf_n:
            return None  # sin hora fin = incompleto, no contar
        a = datetime.strptime(str(fi)[:10] + " " + hi_n, "%Y-%m-%d %H:%M")
        b = datetime.strptime(str(ff)[:10] + " " + hf_n, "%Y-%m-%d %H:%M")
        if b <= a:
            return None
        total = 0.0
        day = a.date()
        end_day = b.date()
        while day <= end_day:
            for w0, w1 in _ventanas_laborables(day):
                start = max(a, w0)
                finish = min(b, w1)
                if finish > start:
                    total += (finish - start).total_seconds() / 60.0
            day = day + timedelta(days=1)
        mins = int(round(total))
        # tope de seguridad: no mas de horas laborables del rango calendario
        max_h = horas_laborables_rango(str(fi)[:10], str(ff)[:10])
        if max_h > 0 and mins > max_h * 60 + 1:
            mins = int(round(max_h * 60))
        return mins if mins >= 0 else None
    except Exception as e:
        print("minutos_tendido:", e)
        return None


def minutos_tendido_calendario(fi, hi, ff, hf):
    """Minutos corridos (reloj) — solo referencia."""
    try:
        if not fi or not ff:
            return None
        hi = (hi or "00:00")[:5]
        hf = (hf or "00:00")[:5]
        a = datetime.strptime(str(fi)[:10] + " " + hi, "%Y-%m-%d %H:%M")
        b = datetime.strptime(str(ff)[:10] + " " + hf, "%Y-%m-%d %H:%M")
        mins = int((b - a).total_seconds() / 60)
        return mins if mins >= 0 else None
    except Exception:
        return None



def is_aduana():
    area = (session.get("area") or "").lower()
    usuario = (session.get("usuario") or "").lower()
    return "aduana" in area or usuario == "aduana"

def can_edit_checklist_aduana():
    if is_aduana():
        return True
    return can_edit()

def can_edit():
    """Diseño y Aduana: no edicion general (Aduana solo checklist de salida)."""
    area = (session.get("area") or "").lower()
    usuario = (session.get("usuario") or "").lower()
    if area in ("diseño", "diseno", "aduana") or usuario in ("diseño", "diseno", "aduana"):
        return False
    return True



def edit_required(f):
    @wraps(f)
    def d(*a, **k):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if not can_edit():
            return page("Solo lectura",
                '<div class="alert alert-err">Tu usuario solo puede consultar (o confirmar Checklist si eres Aduana).</div>'
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
.bell-wrap{position:relative;display:inline-block;margin-left:.9rem;vertical-align:middle}.bell-btn{background:transparent;border:none;color:#fff;font-size:1.2rem;cursor:pointer;padding:.15rem .35rem}.bell-badge{position:absolute;top:-5px;right:-8px;background:#ef4444;color:#fff;font-size:.65rem;font-weight:700;border-radius:999px;min-width:16px;height:16px;line-height:16px;text-align:center;padding:0 4px}.bell-drop{display:none;position:absolute;right:0;top:2.1rem;background:#fff;color:#1e293b;width:340px;max-height:380px;overflow:auto;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,.18);z-index:200;border:1px solid #e2e8f0;text-align:left}.bell-drop.open{display:block}.bell-item{padding:.65rem .85rem;border-bottom:1px solid #f1f5f9;font-size:.8rem}.bell-item.unread{background:#eff6ff}.bell-item a{color:#1e40af;text-decoration:none;font-weight:600}.bell-time{color:#94a3b8;font-size:.7rem;margin-top:.15rem}.bell-head{padding:.55rem .85rem;font-weight:600;font-size:.82rem;border-bottom:1px solid #e2e8f0;display:flex;justify-content:space-between}
"""

def page(title, body, user=None):
    nav = ""
    if user:
        ncount = count_notificaciones()
        badge = ('<span class="bell-badge">' + str(ncount) + '</span>') if ncount else ""
        items = list_notificaciones(12)
        drop_html = '<div class="bell-head"><span>Alertas</span><a href="/notificaciones/leer-todas" style="font-size:.75rem;color:#3b82f6">Marcar todas leidas</a></div>'
        if not items:
            drop_html += '<div class="bell-item" style="color:#94a3b8">Sin notificaciones</div>'
        else:
            for n in items:
                unread = " unread" if not n.get("leida") else ""
                oid = n.get("orden_id") or ""
                num = n.get("numero_orden") or ""
                msg = n.get("mensaje") or ""
                usr = n.get("usuario") or ""
                fecha = str(n.get("fecha") or "")[:16]
                link = ('<a href="/orden/' + str(oid) + '">Orden ' + str(num) + '</a>') if oid else ("Orden " + str(num))
                drop_html += (
                    '<div class="bell-item' + unread + '">' + link + "<br>" + msg
                    + '<div class="bell-time">' + usr + " · " + fecha + "</div></div>"
                )
        bell = (
            '<div class="bell-wrap">'
            '<button type="button" class="bell-btn" onclick="var d=document.getElementById(\'bellDrop\');d.classList.toggle(\'open\')" title="Notificaciones">🔔'
            + badge + "</button>"
            '<div class="bell-drop" id="bellDrop">' + drop_html + "</div></div>"
        )
        links_edit = (
            '<a href="/">Inicio</a><a href="/programas">Programas</a>'
            '<a href="/ordenes">Ordenes</a><a href="/orden/especial">+ Especial</a>'
            '<a href="/agenda">Agenda</a><a href="/estadisticas">Estadisticas</a><a href="/productividad">Productividad</a><a href="/checklist">Checklist</a><a href="/checklist">Checklist</a>'
        )
        links_ro = (
            '<a href="/">Inicio</a><a href="/programas">Programas</a>'
            '<a href="/ordenes">Ordenes</a>'
            '<a href="/agenda">Agenda</a><a href="/estadisticas">Estadisticas</a><a href="/productividad">Productividad</a><a href="/checklist">Checklist</a><a href="/checklist">Checklist</a>'
            ' <span style="margin-left:.8rem;font-size:.8rem;opacity:.85">(Solo lectura)</span>'
        )
        links = links_edit if can_edit() else links_ro
        nav = (
            '<div class="nav"><div><strong>Sistema de Produccion</strong> ' + links + "</div>"
            '<div style="display:flex;align-items:center;gap:.3rem">' + bell + " "
            + str(user.get("nombre", "")) + " (" + str(user.get("area", "")) + ') '
            + '<a href="/logout">Salir</a></div></div>'
        )
    return (
        '<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>" + str(title) + "</title><style>" + CSS + "</style></head><body>"
        + nav + '<div class="container">' + body + "</div>"
        "<script>document.addEventListener('click',function(e){var w=document.querySelector('.bell-wrap');"
        "var d=document.getElementById('bellDrop');if(!w||!d)return;if(!w.contains(e.target))d.classList.remove('open');});</script>"
        "</body></html>"
    )


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



@app.route("/notificaciones/leer-todas")
@login_required
def notificaciones_leer_todas():
    conn = get_db(); cur = conn.cursor()
    try:
        cur.execute("UPDATE notificaciones SET leida=1 WHERE leida=0")
        conn.commit()
    except Exception as e:
        print(e)
    conn.close()
    return redirect(request.referrer or url_for("index"))

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
            crear_notificacion(oid, num, "Nueva orden creada desde programa")
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
            crear_notificacion(oid, num, "Nueva orden creada desde programa")
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
    modelo_f = (request.args.get("modelo") or "").strip()
    color_f = (request.args.get("color") or "").strip()
    maq_f = (request.args.get("maquilero") or "").strip()
    estado_f = (request.args.get("estado") or "").strip()
    conn = get_db(); cur = dcur(conn)
    sql = "SELECT * FROM ordenes WHERE 1=1"
    params = []
    if modelo_f:
        if USE_POSTGRES:
            sql += " AND modelo ILIKE " + ph()
            params.append("%" + modelo_f + "%")
        else:
            sql += " AND lower(modelo) LIKE " + ph()
            params.append("%" + modelo_f.lower() + "%")
    if color_f:
        if USE_POSTGRES:
            sql += " AND color ILIKE " + ph()
            params.append("%" + color_f + "%")
        else:
            sql += " AND lower(color) LIKE " + ph()
            params.append("%" + color_f.lower() + "%")
    if maq_f:
        if USE_POSTGRES:
            sql += " AND maquilero ILIKE " + ph()
            params.append("%" + maq_f + "%")
        else:
            sql += " AND lower(maquilero) LIKE " + ph()
            params.append("%" + maq_f.lower() + "%")
    if estado_f:
        sql += " AND estado_actual = " + ph()
        params.append(estado_f)
    sql += " ORDER BY id DESC"
    if params:
        cur.execute(sql, tuple(params))
    else:
        cur.execute(sql)
    ordenes = cur.fetchall()
    # options for selects
    cur.execute("SELECT DISTINCT modelo FROM ordenes WHERE modelo IS NOT NULL AND modelo != '' ORDER BY modelo")
    modelos = [r["modelo"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT color FROM ordenes WHERE color IS NOT NULL AND color != '' ORDER BY color")
    colores = [r["color"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
    cur.execute("SELECT DISTINCT maquilero FROM ordenes WHERE maquilero IS NOT NULL AND maquilero != '' ORDER BY maquilero")
    maquileros = [r["maquilero"] if isinstance(r, dict) else r[0] for r in cur.fetchall()]
    conn.close()
    def opt(lista, sel):
        h = '<option value="">Todos</option>'
        for v in lista:
            s = " selected" if str(v) == str(sel) else ""
            h += '<option value="%s"%s>%s</option>' % (v, s, v)
        return h
    estados = ["En_Tendido","En_Corte","Listo_Taller","Enviado_Maquila","Entregado_Parcial","Terminado","Corte","Habilitado","En_Maquila"]
    est_opts = '<option value="">Todos</option>' + "".join(
        '<option value="%s"%s>%s</option>' % (e, " selected" if e==estado_f else "", e) for e in estados)
    rows = ""
    for o in ordenes:
        rows += (
            "<tr><td><strong>" + str(o["numero_orden"]) + "</strong></td>"
            "<td>" + str(o.get("tipo") or "-") + "</td>"
            "<td>" + str(o.get("modelo") or "-") + " / " + str(o.get("color") or "") + "</td>"
            "<td>" + str(o.get("maquilero") or "-") + "</td>"
            "<td>" + str(o.get("piezas_programadas") or 0) + "</td>"
            "<td>" + str(o.get("piezas_cortadas") or 0) + "</td>"
            "<td>" + badge_ubicacion(o.get("ubicacion")) + "</td>"
            "<td>" + badge_estado(o.get("estado_actual")) + "</td>"
            '<td><a href="/orden/' + str(o["id"]) + '" class="btn btn-outline btn-sm">Ver</a></td></tr>'
        )
    btn = '<a href="/orden/especial" class="btn btn-warning">+ Especial</a>' if can_edit() else ""
    body = (
        '<div class="card"><div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:.55rem">'
        '<h1 style="margin:0">Ordenes</h1>' + btn + '</div></div>'
        '<div class="card"><h2>Filtros</h2>'
        '<form method="GET" class="form-row">'
        '<div><label>Modelo</label><select name="modelo">' + opt(modelos, modelo_f) + '</select></div>'
        '<div><label>Color</label><select name="color">' + opt(colores, color_f) + '</select></div>'
        '<div><label>Maquilero</label><select name="maquilero">' + opt(maquileros, maq_f) + '</select></div>'
        '<div><label>Estado</label><select name="estado">' + est_opts + '</select></div>'
        '<div style="align-self:flex-end"><button type="submit" class="btn btn-primary">Filtrar</button> '
        '<a href="/ordenes" class="btn btn-outline">Limpiar</a></div></form>'
        '<p style="color:#64748b;margin-top:.5rem">' + str(len(ordenes)) + ' resultado(s)</p></div>'
        '<div class="card">'
        + (('<table><thead><tr><th>Orden</th><th>Tipo</th><th>Modelo</th><th>Maquilero</th><th>Prog.</th><th>Cortadas</th><th>Ubicacion</th><th>Estado</th><th></th></tr></thead><tbody>' + rows + '</tbody></table>') if rows else '<p style="color:#64748b">Sin ordenes con esos filtros.</p>')
        + '</div>'
    )
    return page("Ordenes", body, session)


@app.route("/orden/<int:orden_id>", methods=["GET","POST"])
@login_required
def ver_orden(orden_id):
    conn = get_db(); cur = dcur(conn)
    cur.execute(f"SELECT * FROM ordenes WHERE id={ph()}", (orden_id,))
    o = cur.fetchone()
    tendidos = []
    try:
        cur.execute(f"SELECT * FROM tendidos WHERE orden_id={ph()} ORDER BY id", (orden_id,))
        tendidos = cur.fetchall() or []
    except Exception:
        tendidos = []
    conn.close()
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
            p_prog = int(request.form.get("piezas_programadas") or 0)
            p_cort = int(request.form.get("piezas_cortadas") or 0)
            f_ini = request.form.get("fecha_inicio_corte","").strip()
            f_fin = request.form.get("fecha_final_corte","").strip()
            f_tamp = request.form.get("fecha_tampografia","").strip()
            tamp = request.form.get("tampografia_lista","No")
            # Al registrar corte sale de En_Tendido
            estado = "Listo_Taller" if (f_fin and p_cort > 0) else "En_Corte"
            if USE_POSTGRES:
                cur.execute("""UPDATE ordenes SET piezas_programadas=%s,piezas_cortadas=%s,fecha_inicio_corte=%s,
                    fecha_final_corte=%s,fecha_tampografia=%s,tampografia_lista=%s,estado_actual=%s WHERE id=%s""",
                    (p_prog,p_cort,f_ini,f_fin,f_tamp,tamp,estado,orden_id))
            else:
                cur.execute("""UPDATE ordenes SET piezas_programadas=?,piezas_cortadas=?,fecha_inicio_corte=?,
                    fecha_final_corte=?,fecha_tampografia=?,tampografia_lista=?,estado_actual=? WHERE id=?""",
                    (p_prog,p_cort,f_ini,f_fin,f_tamp,tamp,estado,orden_id))

        elif accion == "habilitado":
            if USE_POSTGRES:
                cur.execute("UPDATE ordenes SET habilitado_estado=%s,habilitado_usuario=%s,habilitado_obs=%s,estado_actual='Habilitado' WHERE id=%s",
                            (request.form.get("habilitado_estado","Parcial"), user, request.form.get("habilitado_obs","").strip(), orden_id))
            else:
                cur.execute("UPDATE ordenes SET habilitado_estado=?,habilitado_usuario=?,habilitado_obs=?,estado_actual='Habilitado' WHERE id=?",
                            (request.form.get("habilitado_estado","Parcial"), user, request.form.get("habilitado_obs","").strip(), orden_id))
        elif accion == "maquila":
            maq = request.form.get("maquilero","").strip()
            f_sal = request.form.get("fecha_salida_maquila","").strip()
            f_ent = request.form.get("fecha_entrega_maquila","").strip()
            p_env = int(request.form.get("piezas_enviadas") or 0)
            p_ent = int(request.form.get("piezas_entregadas") or 0)
            obs = request.form.get("maquila_obs","").strip()
            marcar = request.form.get("marcar_enviado")
            guardar_prog = request.form.get("guardar_programacion")
            # 1) Solo programar: maquilero + fecha salida, SIGUE EN TALLER
            if guardar_prog == "1" or (not marcar and not f_ent and p_ent == 0):
                estado = o.get("estado_actual") or "Listo_Taller"
                if estado in ("Enviado_Maquila", "Terminado", "Entregado_Parcial"):
                    # no bajar de maquila si ya estaba enviada, solo actualizar datos
                    ubi = o.get("ubicacion") or "Maquila"
                else:
                    ubi = "Taller"
                    if estado not in ("Listo_Taller", "En_Corte", "Corte", "Habilitado", "En_Tendido"):
                        estado = "Listo_Taller"
                if USE_POSTGRES:
                    cur.execute("""UPDATE ordenes SET maquilero=%s, fecha_salida_maquila=%s, piezas_enviadas=%s,
                        maquila_usuario=%s, maquila_obs=%s, ubicacion=%s, estado_actual=%s WHERE id=%s""",
                        (maq, f_sal, p_env, user, obs, ubi, estado, orden_id))
                else:
                    cur.execute("""UPDATE ordenes SET maquilero=?, fecha_salida_maquila=?, piezas_enviadas=?,
                        maquila_usuario=?, maquila_obs=?, ubicacion=?, estado_actual=? WHERE id=?""",
                        (maq, f_sal, p_env, user, obs, ubi, estado, orden_id))
            elif marcar == "1":
                estado = "Enviado_Maquila"
                ubi = "Maquila"
                if not f_sal:
                    f_sal = datetime.now().strftime("%Y-%m-%d")
                if USE_POSTGRES:
                    cur.execute("""UPDATE ordenes SET maquilero=%s,fecha_salida_maquila=%s,fecha_entrega_maquila=%s,
                        piezas_enviadas=%s,piezas_entregadas=%s,maquila_usuario=%s,maquila_obs=%s,
                        estado_actual=%s,ubicacion=%s WHERE id=%s""",
                        (maq,f_sal,f_ent or None,p_env,p_ent,user,obs,estado,ubi,orden_id))
                else:
                    cur.execute("""UPDATE ordenes SET maquilero=?,fecha_salida_maquila=?,fecha_entrega_maquila=?,
                        piezas_enviadas=?,piezas_entregadas=?,maquila_usuario=?,maquila_obs=?,
                        estado_actual=?,ubicacion=? WHERE id=?""",
                        (maq,f_sal,f_ent or None,p_env,p_ent,user,obs,estado,ubi,orden_id))
            else:
                # Entrega (parcial o total)
                prev = 0
                try:
                    prev = int(o.get("piezas_entregadas") or 0)
                except Exception:
                    prev = 0
                total_ent = prev + p_ent if request.form.get("modo_entrega") == "sumar" else p_ent
                p_env_ref = p_env or int(o.get("piezas_enviadas") or o.get("piezas_cortadas") or 0)
                if total_ent >= p_env_ref and p_env_ref > 0:
                    estado = "Terminado"
                else:
                    estado = "Entregado_Parcial"
                ubi = "Maquila"
                p_ent = total_ent
                if USE_POSTGRES:
                    cur.execute("""UPDATE ordenes SET maquilero=%s,fecha_salida_maquila=%s,fecha_entrega_maquila=%s,
                        piezas_enviadas=%s,piezas_entregadas=%s,maquila_usuario=%s,maquila_obs=%s,
                        estado_actual=%s,ubicacion=%s WHERE id=%s""",
                        (maq,f_sal,f_ent or None,p_env,p_ent,user,obs,estado,ubi,orden_id))
                else:
                    cur.execute("""UPDATE ordenes SET maquilero=?,fecha_salida_maquila=?,fecha_entrega_maquila=?,
                        piezas_enviadas=?,piezas_entregadas=?,maquila_usuario=?,maquila_obs=?,
                        estado_actual=?,ubicacion=? WHERE id=?""",
                        (maq,f_sal,f_ent or None,p_env,p_ent,user,obs,estado,ubi,orden_id))
        
        elif accion == "tendido":
            p1 = request.form.get("persona1","").strip()
            p2 = request.form.get("persona2","").strip()
            fi = request.form.get("fecha_inicio","").strip()
            hi = request.form.get("hora_inicio","").strip()
            ff = request.form.get("fecha_fin","").strip() or None
            hf = request.form.get("hora_fin","").strip() or None
            obs = request.form.get("tendido_obs","").strip()
            tid = (request.form.get("tendido_id") or "").strip()
            telas = request.form.getlist("bloque_tela[]")
            colores = request.form.getlist("bloque_color[]")
            lienzos = request.form.getlist("bloque_lienzos[]")
            largos = request.form.getlist("bloque_largo[]")
            bloques = []
            for i in range(len(telas)):
                if not (telas[i] or "").strip():
                    continue
                bloques.append({
                    "tela": telas[i].strip(),
                    "color": (colores[i] if i < len(colores) else "").strip(),
                    "lienzos": (lienzos[i] if i < len(lienzos) else "").strip(),
                    "largo": (largos[i] if i < len(largos) else "").strip(),
                })
            bj = json.dumps(bloques, ensure_ascii=False)
            # Asegurar tabla y columna en la BD (por si el deploy anterior no las creo)
            try:
                if USE_POSTGRES:
                    cur.execute("""CREATE TABLE IF NOT EXISTS tendidos (
                        id SERIAL PRIMARY KEY, orden_id INT, persona1 TEXT, persona2 TEXT,
                        fecha_inicio TEXT, hora_inicio TEXT, fecha_fin TEXT, hora_fin TEXT,
                        bloques_base INT DEFAULT 0, bloques_entretela INT DEFAULT 0, bloques_combinacion INT DEFAULT 0,
                        observaciones TEXT, registrado_por TEXT, bloques_json TEXT DEFAULT '[]',
                        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
                    cur.execute("ALTER TABLE tendidos ADD COLUMN IF NOT EXISTS bloques_json TEXT DEFAULT '[]'")
                else:
                    cur.execute("""CREATE TABLE IF NOT EXISTS tendidos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, orden_id INTEGER, persona1 TEXT, persona2 TEXT,
                        fecha_inicio TEXT, hora_inicio TEXT, fecha_fin TEXT, hora_fin TEXT,
                        bloques_base INTEGER DEFAULT 0, bloques_entretela INTEGER DEFAULT 0, bloques_combinacion INTEGER DEFAULT 0,
                        observaciones TEXT, registrado_por TEXT, bloques_json TEXT DEFAULT '[]',
                        fecha_registro TEXT DEFAULT CURRENT_TIMESTAMP)""")
                    try:
                        cur.execute("ALTER TABLE tendidos ADD COLUMN bloques_json TEXT DEFAULT '[]'")
                    except Exception:
                        pass
            except Exception as e:
                print("ensure tendidos:", e)
            completo = bool(ff and hf)
            if USE_POSTGRES:
                if tid and str(tid).isdigit():
                    cur.execute("""UPDATE tendidos SET persona1=%s, persona2=%s, fecha_inicio=%s, hora_inicio=%s,
                        fecha_fin=%s, hora_fin=%s, observaciones=%s, bloques_json=%s
                        WHERE id=%s AND orden_id=%s""",
                        (p1, p2, fi, hi, ff, hf, obs, bj, int(tid), orden_id))
                else:
                    cur.execute("""INSERT INTO tendidos
                        (orden_id, persona1, persona2, fecha_inicio, hora_inicio, fecha_fin, hora_fin,
                         observaciones, registrado_por, bloques_json)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (orden_id, p1, p2, fi, hi, ff, hf, obs, user, bj))
            else:
                if tid and str(tid).isdigit():
                    cur.execute("""UPDATE tendidos SET persona1=?, persona2=?, fecha_inicio=?, hora_inicio=?,
                        fecha_fin=?, hora_fin=?, observaciones=?, bloques_json=?
                        WHERE id=? AND orden_id=?""",
                        (p1, p2, fi, hi, ff, hf, obs, bj, int(tid), orden_id))
                else:
                    cur.execute("""INSERT INTO tendidos
                        (orden_id, persona1, persona2, fecha_inicio, hora_inicio, fecha_fin, hora_fin,
                         observaciones, registrado_por, bloques_json)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (orden_id, p1, p2, fi, hi, ff, hf, obs, user, bj))
            if not completo:
                if USE_POSTGRES:
                    cur.execute("UPDATE ordenes SET estado_actual='En_Tendido' WHERE id=%s", (orden_id,))
                else:
                    cur.execute("UPDATE ordenes SET estado_actual='En_Tendido' WHERE id=?", (orden_id,))

        elif accion == "listo_taller":
            if USE_POSTGRES:
                cur.execute("UPDATE ordenes SET estado_actual='Listo_Taller',ubicacion='Taller' WHERE id=%s", (orden_id,))
            else:
                cur.execute("UPDATE ordenes SET estado_actual='Listo_Taller',ubicacion='Taller' WHERE id=?", (orden_id,))
        conn.commit(); conn.close()
        # Alerta campanita
        try:
            msgs = {
                "numero": "Se modifico el numero de orden",
                "corte": "Se actualizaron datos de corte",
                "habilitado": "Se actualizo habilitado",
                "maquila": "Se actualizo maquila / envio / entrega",
                "listo_taller": "Orden marcada lista en taller",
                "tendido": "Se guardo o edito un tendido",
            }
            msg = msgs.get(accion, "Se modifico la orden")
            if accion == "maquila" and request.form.get("marcar_enviado") == "1":
                msg = "Orden ENVIADA a maquila"
            elif accion == "maquila" and request.form.get("guardar_programacion") == "1":
                msg = "Programacion de envio a maquila guardada (sigue en taller)"
            crear_notificacion(orden_id, o.get("numero_orden"), msg)
        except Exception as e:
            print("notif:", e)
        return redirect(url_for("ver_orden", orden_id=orden_id))

    



    # --- Tendido HTML ---
    tendido_rows = ""
    for t in (tendidos or []):
        mins = minutos_tendido(t.get("fecha_inicio"), t.get("hora_inicio"), t.get("fecha_fin"), t.get("hora_fin"))
        pareja = (t.get("persona1") or "-") + " + " + (t.get("persona2") or "-")
        try:
            bl = json.loads(t.get("bloques_json") or "[]")
        except Exception:
            bl = []
        bl_txt = ""
        if bl:
            bl_txt = "<ul style='margin:0;padding-left:1.1rem;font-size:.8rem'>"
            sum_m = 0.0
            for b in bl:
                m = metros_bloque(b)
                sum_m += m
                bl_txt += "<li><strong>" + str(b.get("tela") or "") + "</strong> / " + str(b.get("color") or "")
                bl_txt += " · " + str(b.get("lienzos") or "") + " lienzos · largo " + str(b.get("largo") or "")
                bl_txt += " → <strong>" + ("%.1f" % m) + " m</strong></li>"
            bl_txt += "</ul><div style='font-size:.8rem;margin-top:.2rem'>Total: <strong>" + ("%.1f" % sum_m) + " m</strong></div>"
        else:
            bl_txt = "<span style='color:#94a3b8'>—</span>"
        pendiente = not (t.get("fecha_fin") and t.get("hora_fin"))
        est_t = '<span class="badge badge-pend">En proceso</span>' if pendiente else '<span class="badge badge-ok">Completo</span>'
        edit_btn = ""
        if can_edit():
            # data for edit via query params on same form - use link with id
            edit_btn = '<a class="btn btn-outline btn-sm" href="?editar_tendido=' + str(t.get("id")) + '#tendido">Editar</a>'
        tendido_rows += (
            "<tr><td>" + pareja + "</td>"
            "<td>" + str(t.get("fecha_inicio") or "") + " " + str(t.get("hora_inicio") or "") + "</td>"
            "<td>" + (str(t.get("fecha_fin") or "") + " " + str(t.get("hora_fin") or "") if not pendiente else "<em>Pendiente</em>") + "</td>"
            "<td><strong>" + (str(mins) + " min" if mins is not None else "-") + "</strong></td>"
            "<td>" + bl_txt + "</td><td>" + est_t + "</td>"
            "<td>" + str(t.get("observaciones") or "") + " " + edit_btn + "</td></tr>"
        )
    tendido_table = (
        ('<table><thead><tr><th>Pareja</th><th>Inicio</th><th>Fin</th><th>Duracion</th><th>Bloques</th><th>Estado</th><th></th></tr></thead><tbody>'
         + tendido_rows + "</tbody></table>") if tendido_rows else '<p style="color:#94a3b8">Sin tendidos registrados.</p>'
    )
    # form values if editing
    edit_id = (request.args.get("editar_tendido") or "").strip()
    et = None
    for t in (tendidos or []):
        if str(t.get("id")) == str(edit_id):
            et = t
            break
    try:
        edit_bloques = json.loads(et.get("bloques_json") or "[]") if et else []
    except Exception:
        edit_bloques = []
    form_tendido = ""
    if can_edit():
        v_p1 = (et.get("persona1") if et else "") or ""
        v_p2 = (et.get("persona2") if et else "") or ""
        v_fi = (et.get("fecha_inicio") if et else "") or ""
        v_hi = (et.get("hora_inicio") if et else "") or ""
        v_ff = (et.get("fecha_fin") if et else "") or ""
        v_hf = (et.get("hora_fin") if et else "") or ""
        v_obs = (et.get("observaciones") if et else "") or ""
        v_tid = str(et.get("id")) if et else ""
        titulo_form = "Editar tendido #" + v_tid if et else "Registrar tendido (se puede guardar sin hora de fin)"
        # prefill blocks JS
        prefill = ""
        if edit_bloques:
            for b in edit_bloques:
                prefill += "addBloqueTendido(%s,%s,%s,%s);" % (
                    json.dumps(b.get("tela") or ""),
                    json.dumps(b.get("color") or ""),
                    json.dumps(str(b.get("lienzos") or "")),
                    json.dumps(str(b.get("largo") or "")),
                )
        else:
            prefill = "addBloqueTendido('','','','');"
        form_tendido = (
            '<details style="margin-top:.6rem" open id="tendido"><summary style="cursor:pointer;font-weight:600">' + titulo_form + '</summary>'
            '<form method="POST" style="margin-top:.55rem" id="formTendido"><input type="hidden" name="accion" value="tendido">'
            '<input type="hidden" name="tendido_id" value="' + v_tid + '">'
            '<div class="form-row">'
            '<div><label>Persona 1 *</label><input name="persona1" required value="' + v_p1 + '" placeholder="Nombre"></div>'
            '<div><label>Persona 2 *</label><input name="persona2" required value="' + v_p2 + '" placeholder="Nombre"></div></div>'
            '<div class="form-row">'
            '<div><label>Fecha inicio *</label><input type="date" name="fecha_inicio" required value="' + v_fi + '"></div>'
            '<div><label>Hora inicio *</label><input type="time" name="hora_inicio" required value="' + v_hi + '"></div>'
            '<div><label>Fecha fin (opcional)</label><input type="date" name="fecha_fin" value="' + v_ff + '"></div>'
            '<div><label>Hora fin (opcional)</label><input type="time" name="hora_fin" value="' + v_hf + '"></div></div>'
            '<p style="font-size:.8rem;color:#64748b;margin-bottom:.5rem">Si no pones fin, la orden queda en estado <strong>En tendido</strong> y puedes seguir agregando bloques.</p>'
            '<h3 style="font-size:.95rem;margin:0.5rem 0 0.4rem">Bloques</h3>'
            '<div id="bloquesTendido"></div>'
            '<button type="button" class="btn btn-outline btn-sm" onclick="addBloqueTendido(\'\',\'\',\'\',\'\')" style="margin-bottom:.7rem">+ Agregar bloque</button>'
            '<label>Observaciones</label><textarea name="tendido_obs" rows="2">' + v_obs + '</textarea>'
            '<button type="submit" class="btn btn-primary btn-sm">Guardar tendido</button>'
            + (' <a href="/orden/' + str(orden_id) + '" class="btn btn-outline btn-sm">Cancelar edicion</a>' if et else '')
            + '</form></details>'
            '<script>'
            'function addBloqueTendido(tela,color,lienzos,largo){'
            'var c=document.getElementById("bloquesTendido");'
            'var d=document.createElement("div");'
            'd.className="card"; d.style="padding:.7rem;background:#f8fafc;margin-bottom:.45rem";'
            'tela=tela||"";color=color||"";lienzos=lienzos||"";largo=largo||"";'
            'd.innerHTML=`<div class="form-row">'
            + '<div><label>Tela</label><input name="bloque_tela[]" value="${tela}" placeholder="Base, Entretela, Combinacion"></div>'
            + '<div><label>Color</label><input name="bloque_color[]" value="${color}"></div>'
            + '<div><label>Cantidad de lienzos</label><input type="number" name="bloque_lienzos[]" min="0" value="${lienzos}"></div>'
            + '<div><label>Largo del bloque</label><input name="bloque_largo[]" value="${largo}" placeholder="Ej. 2.5 m"></div>'
            + '</div><button type="button" class="btn btn-outline btn-sm" onclick="this.parentNode.remove()">Quitar</button>`;'
            'c.appendChild(d);}'
            + prefill +
            '</script>'
        )
    seccion_tendido = (
        '<div class="card"><h2>1b. Tendido (antes de cortar)</h2>'
        '<p style="color:#64748b;font-size:.85rem;margin-bottom:.5rem">Puedes guardar incompleto (sin hora fin). Varios registros por orden. Editable.</p>'
        + tendido_table + form_tendido + "</div>"
    )

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
    ''' + seccion_tendido + f'''<div class="card"><h2>2. Habilitado</h2>
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
    <div class="card"><h2>3. Maquila (envio y entrega)</h2>
        <p>{badge_ubicacion(o.get("ubicacion"))} {badge_estado(o.get("estado_actual"))}</p>
        <p>Maquilero: <strong>{o.get("maquilero") or "—"}</strong></p>
        <p>Salida: {o.get("fecha_salida_maquila") or "—"} · Piezas enviadas: <strong>{o.get("piezas_enviadas") or 0}</strong></p>
        <p>Entrega: {o.get("fecha_entrega_maquila") or "—"} · Piezas entregadas: <strong>{o.get("piezas_entregadas") or 0}</strong></p>
        {"<div class=\"alert alert-ok\">Proceso terminado: maquilero entrego todo</div>" if o.get("estado_actual")=="Terminado" else ""}
        {"<div class=\"alert alert-err\">Entrega parcial: faltan piezas</div>" if o.get("estado_actual")=="Entregado_Parcial" else ""}
        <p style="font-size:.85rem;color:#64748b;margin:.4rem 0">Ubicacion actual: <strong>{"En taller de corte" if (o.get("ubicacion") or "Taller")=="Taller" else "En maquila"}</strong>
        {" · Programado: " + str(o.get("maquilero") or "") + " / " + str(o.get("fecha_salida_maquila") or "") if o.get("maquilero") or o.get("fecha_salida_maquila") else ""}</p>
        <details style="margin-top:.55rem" open><summary style="cursor:pointer;font-weight:600">Gestionar maquila / envio</summary>
        <form method="POST" style="margin-top:.55rem"><input type="hidden" name="accion" value="maquila">
            <p style="font-size:.82rem;color:#64748b;margin-bottom:.5rem"><strong>1. Programar</strong> (guarda maquilero y fecha sin sacar del taller)</p>
            <div class="form-row">
                <div><label>Maquilero</label><input name="maquilero" value="{o.get("maquilero") or ""}" placeholder="Nombre del maquilero"></div>
                <div><label>Fecha de salida prevista</label><input type="date" name="fecha_salida_maquila" value="{o.get("fecha_salida_maquila") or ""}"></div>
                <div><label>Piezas a enviar</label><input type="number" name="piezas_enviadas" value="{o.get("piezas_enviadas") or o.get("piezas_cortadas") or 0}"></div>
            </div>
            <label>Observaciones</label><textarea name="maquila_obs" rows="2">{o.get("maquila_obs") or ""}</textarea>
            <button type="submit" name="guardar_programacion" value="1" class="btn btn-primary btn-sm" style="margin-bottom:.8rem">Guardar programacion (sigue en taller)</button>
            <hr style="border:none;border-top:1px solid #e2e8f0;margin:.8rem 0">
            <p style="font-size:.82rem;color:#64748b;margin-bottom:.5rem"><strong>2. Enviar a maquila</strong> (cambia ubicacion a maquila)</p>
            <button type="submit" name="marcar_enviado" value="1" class="btn btn-warning btn-sm"
                onclick="return confirm('¿Confirmar que YA SALIO a maquila?')">Marcar como ENVIADO a maquila</button>
            <hr style="border:none;border-top:1px solid #e2e8f0;margin:.8rem 0">
            <p style="font-size:.82rem;color:#64748b;margin-bottom:.5rem"><strong>3. Entrega del maquilero</strong></p>
            <div class="form-row">
                <div><label>Fecha entrega</label><input type="date" name="fecha_entrega_maquila" value="{o.get("fecha_entrega_maquila") or ""}"></div>
                <div><label>Piezas entregadas ahora</label><input type="number" name="piezas_entregadas" value="0" min="0"></div>
            </div>
            <input type="hidden" name="modo_entrega" value="sumar">
            <button type="submit" class="btn btn-success btn-sm">Registrar entrega (puede ser parcial)</button>
        </form></details>
        {"<form method=\"POST\" style=\"margin-top:.5rem\"><input type=\"hidden\" name=\"accion\" value=\"listo_taller\"><button type=\"submit\" class=\"btn btn-outline btn-sm\">Marcar listo en taller</button></form>" if (o.get("ubicacion") or "Taller")=="Taller" and o.get("estado_actual") not in ("Terminado","Enviado_Maquila") else ""}
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


@app.route("/estadisticas")
@login_required
def estadisticas():
    tendido_prod, tendido_pers, tendido_tela, tendido_dia = [], [], [], []
    conn = get_db(); cur = dcur(conn)
    lun, vie = week_range_lun_vie()
    mini, mfin = month_range()
    lun_s, vie_s = lun.strftime("%Y-%m-%d"), vie.strftime("%Y-%m-%d")
    mini_s, mfin_s = mini.strftime("%Y-%m-%d"), mfin.strftime("%Y-%m-%d")
    q = "SELECT COALESCE(SUM(piezas_cortadas),0) as pzas, COUNT(*) as n FROM ordenes WHERE fecha_final_corte>=" + ph() + " AND fecha_final_corte<=" + ph()
    cur.execute(q, (lun_s, vie_s))
    row = cur.fetchone()
    corte_sem_p = int(row["pzas"] if isinstance(row, dict) else row[0] or 0)
    corte_sem_n = int(row["n"] if isinstance(row, dict) else row[1] or 0)
    cur.execute(q, (mini_s, mfin_s))
    row = cur.fetchone()
    corte_mes_p = int(row["pzas"] if isinstance(row, dict) else row[0] or 0)
    corte_mes_n = int(row["n"] if isinstance(row, dict) else row[1] or 0)
    cur.execute("""SELECT maquilero, COUNT(*) as ordenes,
        COALESCE(SUM(COALESCE(piezas_enviadas, piezas_cortadas)),0) as enviadas,
        COALESCE(SUM(piezas_entregadas),0) as entregadas
        FROM ordenes WHERE maquilero IS NOT NULL AND maquilero != ''
        AND COALESCE(estado_actual,'') != 'Terminado'
        GROUP BY maquilero ORDER BY ordenes DESC""")
    activos = cur.fetchall()
    q2 = "SELECT maquilero, COUNT(*) as ordenes, COALESCE(SUM(piezas_entregadas),0) as pzas FROM ordenes WHERE fecha_entrega_maquila>=" + ph() + " AND fecha_entrega_maquila<=" + ph() + " AND maquilero IS NOT NULL AND maquilero != '' GROUP BY maquilero ORDER BY pzas DESC"
    cur.execute(q2, (lun_s, vie_s)); ent_sem = cur.fetchall()
    cur.execute(q2, (mini_s, mfin_s)); ent_mes = cur.fetchall()
    # By modelo / color
    cur.execute("""SELECT COALESCE(modelo,'(sin modelo)') as modelo, COUNT(*) as n,
        COALESCE(SUM(piezas_cortadas),0) as pzas FROM ordenes GROUP BY modelo ORDER BY pzas DESC LIMIT 15""")
    por_modelo = cur.fetchall()
    cur.execute("""SELECT COALESCE(color,'(sin color)') as color, COUNT(*) as n,
        COALESCE(SUM(piezas_cortadas),0) as pzas FROM ordenes GROUP BY color ORDER BY pzas DESC LIMIT 15""")
    por_color = cur.fetchall()
    cur.execute("""SELECT COALESCE(estado_actual,'(sin estado)') as est, COUNT(*) as n FROM ordenes GROUP BY estado_actual ORDER BY n DESC""")
    por_estado = cur.fetchall()
    

    try:
        cur.execute("SELECT * FROM tendidos ORDER BY id DESC LIMIT 500")
        all_t = cur.fetchall() or []
        pairs, persons = {}, {}
        por_tela = {}
        por_dia = {}
        for t in all_t:
            p1 = (t.get("persona1") or "").strip()
            p2 = (t.get("persona2") or "").strip()
            mins = minutos_tendido(t.get("fecha_inicio"), t.get("hora_inicio"), t.get("fecha_fin"), t.get("hora_fin"))
            bls = bloques_from_tendido(t)
            tot_bloques = len(bls)
            tot_metros = sum(metros_bloque(b) for b in bls)
            dia = (t.get("fecha_inicio") or "")[:10] or "sin fecha"
            if dia not in por_dia:
                por_dia[dia] = {"metros": 0.0, "bloques": 0, "n": 0, "mins": 0}
            por_dia[dia]["metros"] += tot_metros
            por_dia[dia]["bloques"] += tot_bloques
            por_dia[dia]["n"] += 1
            if mins is not None and mins > 0:
                por_dia[dia]["mins"] += mins
            for b in bls:
                tela = (b.get("tela") or "Sin tela").strip() or "Sin tela"
                color = (b.get("color") or "").strip()
                key_tela = tela + ((" / " + color) if color else "")
                m = metros_bloque(b)
                if key_tela not in por_tela:
                    por_tela[key_tela] = {"metros": 0.0, "bloques": 0, "lienzos": 0.0}
                por_tela[key_tela]["metros"] += m
                por_tela[key_tela]["bloques"] += 1
                por_tela[key_tela]["lienzos"] += parse_num(b.get("lienzos"))
            key = " + ".join(sorted([p for p in [p1, p2] if p]))
            if key:
                pairs.setdefault(key, {"mins": 0, "bloques": 0, "n": 0, "metros": 0.0})
                if mins is not None and mins > 0:
                    pairs[key]["mins"] += mins
                pairs[key]["bloques"] += tot_bloques
                pairs[key]["metros"] += tot_metros
                pairs[key]["n"] += 1
            for p in [p1, p2]:
                if not p:
                    continue
                persons.setdefault(p, {"mins": 0, "bloques": 0, "n": 0, "metros": 0.0})
                if mins is not None and mins > 0:
                    persons[p]["mins"] += mins
                persons[p]["bloques"] += tot_bloques
                persons[p]["metros"] += tot_metros
                persons[p]["n"] += 1
        tendido_prod = sorted(pairs.items(), key=lambda x: x[1].get("metros", 0), reverse=True)
        tendido_pers = sorted(persons.items(), key=lambda x: x[1].get("metros", 0), reverse=True)
        tendido_tela = sorted(por_tela.items(), key=lambda x: x[1]["metros"], reverse=True)
        tendido_dia = sorted(por_dia.items(), key=lambda x: x[0], reverse=True)
    except Exception as e:
        print("tendido stats", e)
        tendido_prod, tendido_pers, tendido_tela, tendido_dia = [], [], [], []

    conn.close()

    def gv(x, k, i=0):
        return x[k] if isinstance(x, dict) else x[i]

    labels_maq = [str(gv(x,"maquilero",0)) for x in activos]
    data_maq_ord = [int(gv(x,"ordenes",1) or 0) for x in activos]
    data_maq_env = [int(gv(x,"enviadas",2) or 0) for x in activos]
    data_maq_ent = [int(gv(x,"entregadas",3) or 0) for x in activos]
    labels_mod = [str(gv(x,"modelo",0)) for x in por_modelo]
    data_mod = [int(gv(x,"pzas",2) or 0) for x in por_modelo]
    labels_col = [str(gv(x,"color",0)) for x in por_color]
    data_col = [int(gv(x,"pzas",2) or 0) for x in por_color]
    labels_est = [str(gv(x,"est",0)) for x in por_estado]
    data_est = [int(gv(x,"n",1) or 0) for x in por_estado]
    labels_ent_sem = [str(gv(x,"maquilero",0)) for x in ent_sem]
    data_ent_sem = [int(gv(x,"pzas",2) or 0) for x in ent_sem]

    def rows_act(lista):
        if not lista: return "<tr><td colspan=4>Sin datos</td></tr>"
        r = ""
        for x in lista:
            env = int(gv(x,"enviadas",2) or 0); ent = int(gv(x,"entregadas",3) or 0)
            r += '<tr><td><strong>%s</strong></td><td>%s</td><td>%s</td><td>%s</td><td style="color:#d97706">%s</td></tr>' % (
                gv(x,"maquilero",0), gv(x,"ordenes",1), env, ent, env-ent)
        return r
    def rows_ent(lista):
        if not lista: return "<tr><td colspan=3>Sin datos</td></tr>"
        return "".join("<tr><td><strong>%s</strong></td><td>%s</td><td>%s</td></tr>" % (gv(x,"maquilero",0), gv(x,"ordenes",1), gv(x,"pzas",2)) for x in lista)

    chart_js = """
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script>
const c1=document.getElementById('cMaq');
if(c1){new Chart(c1,{type:'bar',data:{labels:%s,datasets:[
{label:'Ordenes activas',data:%s,backgroundColor:'#3b82f6'},
{label:'Piezas enviadas',data:%s,backgroundColor:'#f59e0b'},
{label:'Piezas entregadas',data:%s,backgroundColor:'#10b981'}
]},options:{responsive:true,plugins:{title:{display:true,text:'Maquileros activos'}}}});}
const c2=document.getElementById('cMod');
if(c2){new Chart(c2,{type:'bar',data:{labels:%s,datasets:[{label:'Piezas cortadas',data:%s,backgroundColor:'#6366f1'}]},
options:{indexAxis:'y',responsive:true,plugins:{title:{display:true,text:'Por modelo'}}}});}
const c3=document.getElementById('cCol');
if(c3){new Chart(c3,{type:'doughnut',data:{labels:%s,datasets:[{data:%s,backgroundColor:['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6','#f97316']}]},
options:{responsive:true,plugins:{title:{display:true,text:'Por color'}}}});}
const c4=document.getElementById('cEst');
if(c4){new Chart(c4,{type:'pie',data:{labels:%s,datasets:[{data:%s,backgroundColor:['#fef3c7','#dbeafe','#ffedd5','#fde68a','#d1fae5','#e0e7ff']}]},
options:{responsive:true,plugins:{title:{display:true,text:'Ordenes por estado'}}}});}
const c5=document.getElementById('cEnt');
if(c5){new Chart(c5,{type:'bar',data:{labels:%s,datasets:[{label:'Piezas entregadas semana',data:%s,backgroundColor:'#059669'}]},
options:{responsive:true,plugins:{title:{display:true,text:'Entregas semana (lun-vie)'}}}});}
const c6=document.getElementById('cCorte');
if(c6){new Chart(c6,{type:'bar',data:{labels:['Esta semana','Este mes'],datasets:[{label:'Piezas cortadas',data:[%s,%s],backgroundColor:['#3b82f6','#1e40af']}]},
options:{responsive:true,plugins:{title:{display:true,text:'Produccion de corte'}}}});}
</script>
""" % (
        json.dumps(labels_maq, ensure_ascii=False), json.dumps(data_maq_ord), json.dumps(data_maq_env), json.dumps(data_maq_ent),
        json.dumps(labels_mod, ensure_ascii=False), json.dumps(data_mod),
        json.dumps(labels_col, ensure_ascii=False), json.dumps(data_col),
        json.dumps(labels_est, ensure_ascii=False), json.dumps(data_est),
        json.dumps(labels_ent_sem, ensure_ascii=False), json.dumps(data_ent_sem),
        corte_sem_p, corte_mes_p
    )

    body = (
        '<div class="card"><h1>Estadisticas descriptivas</h1>'
        '<p style="color:#64748b">Semana laboral: ' + lun.strftime("%d/%m") + " - " + vie.strftime("%d/%m/%Y") + " (lun-vie) | Mes: " + mini.strftime("%m/%Y") + "</p></div>"
        '<div class="card"><h2>Produccion de corte</h2>'
        '<p><strong>' + str(corte_sem_p) + "</strong> piezas esta semana (" + str(corte_sem_n) + " ordenes) · "
        "<strong>" + str(corte_mes_p) + "</strong> piezas este mes (" + str(corte_mes_n) + " ordenes)</p>"
        '<div style="max-width:480px;margin:1rem auto"><canvas id="cCorte"></canvas></div></div>'
        '<div class="card"><h2>Graficos</h2>'
        '<div style="display:grid;grid-template-columns:1fr 1fr;gap:1.2rem">'
        '<div><canvas id="cMaq"></canvas></div><div><canvas id="cMod"></canvas></div>'
        '<div><canvas id="cCol"></canvas></div><div><canvas id="cEst"></canvas></div>'
        '<div style="grid-column:1/-1;max-width:640px;margin:0 auto"><canvas id="cEnt"></canvas></div>'
        '</div></div>'
        '<div class="card"><h2>Maquileros activos (no terminados)</h2>'
        '<table><thead><tr><th>Maquilero</th><th>Ordenes</th><th>Enviadas</th><th>Entregadas</th><th>Pendientes</th></tr></thead><tbody>'
        + rows_act(activos) + "</tbody></table></div>"
        '<div class="card"><h2>Entregas esta semana</h2>'
        '<table><thead><tr><th>Maquilero</th><th>Ordenes</th><th>Piezas</th></tr></thead><tbody>'
        + rows_ent(ent_sem) + "</tbody></table></div>"
        '<div class="card"><h2>Entregas este mes</h2>'
        '<table><thead><tr><th>Maquilero</th><th>Ordenes</th><th>Piezas</th></tr></thead><tbody>'
        + rows_ent(ent_mes) + "</tbody></table></div>"
        + '<div class="card"><h2>Tiempo de tendido — parejas</h2>'
        + '<table><thead><tr><th>Pareja</th><th>Tendidos</th><th>Bloques</th><th>Metros tela</th><th>Minutos</th><th>Horas</th></tr></thead><tbody>'
        + ("".join("<tr><td><strong>%s</strong></td><td>%s</td><td>%s</td><td>%.1f</td><td>%s</td><td>%.1f</td></tr>" % (
            k, v["n"], v.get("bloques",0), v.get("metros",0), v["mins"], (v["mins"] / 60.0 if v["mins"] else 0)
          ) for k, v in tendido_prod) if tendido_prod else "<tr><td colspan=4>Sin datos de tendido</td></tr>")
        + "</tbody></table></div>"
        + '<div class="card"><h2>Tiempo de tendido — por persona</h2>'
        + '<table><thead><tr><th>Persona</th><th>Tendidos</th><th>Bloques</th><th>Metros tela</th><th>Minutos</th><th>Horas</th></tr></thead><tbody>'
        + ("".join("<tr><td><strong>%s</strong></td><td>%s</td><td>%s</td><td>%.1f</td><td>%s</td><td>%.1f</td></tr>" % (
            k, v["n"], v.get("bloques",0), v.get("metros",0), v["mins"], (v["mins"] / 60.0 if v["mins"] else 0)
          ) for k, v in tendido_pers) if tendido_pers else "<tr><td colspan=4>Sin datos</td></tr>")
        + "</tbody></table></div>"
        + '<div class="card"><h2>Metros de tela por tipo (largo x lienzos)</h2>'
        + '<p style="color:#64748b;font-size:.85rem;margin-bottom:.5rem">Formula: metros = largo del bloque × cantidad de lienzos. Se suma por tela/color.</p>'
        + '<table><thead><tr><th>Tela / Color</th><th>Bloques</th><th>Lienzos</th><th>Metros totales</th></tr></thead><tbody>'
        + ("".join("<tr><td><strong>%s</strong></td><td>%s</td><td>%.0f</td><td><strong>%.1f m</strong></td></tr>" % (
            k, v["bloques"], v.get("lienzos",0), v["metros"]
          ) for k, v in tendido_tela) if tendido_tela else "<tr><td colspan=4>Sin datos de bloques</td></tr>")
        + "</tbody></table></div>"
        + '<div class="card"><h2>Metros tendidos por dia</h2>'
        + '<table><thead><tr><th>Fecha</th><th>Tendidos</th><th>Bloques</th><th>Metros</th><th>Minutos</th></tr></thead><tbody>'
        + ("".join("<tr><td><strong>%s</strong></td><td>%s</td><td>%s</td><td><strong>%.1f m</strong></td><td>%s</td></tr>" % (
            k, v["n"], v["bloques"], v["metros"], v.get("mins",0)
          ) for k, v in tendido_dia) if tendido_dia else "<tr><td colspan=5>Sin datos</td></tr>")
        + "</tbody></table></div>"
        + chart_js
    )
    return page("Estadisticas", body, session)



@app.route("/productividad")
@login_required
def productividad():
    """Productividad personal: solo horas laborables; piezas e informe de ordenes."""
    periodo = (request.args.get("periodo") or "semana").strip()
    fecha_ref = (request.args.get("fecha") or datetime.now().strftime("%Y-%m-%d")).strip()
    try:
        ref = datetime.strptime(fecha_ref[:10], "%Y-%m-%d").date()
    except Exception:
        ref = datetime.now().date()
        fecha_ref = ref.strftime("%Y-%m-%d")

    if periodo == "dia":
        fi, ff = ref, ref
        titulo_per = "Dia " + ref.strftime("%d/%m/%Y")
    elif periodo == "mes":
        fi, ff = month_range(ref)
        titulo_per = "Mes " + ref.strftime("%m/%Y")
    else:
        periodo = "semana"
        fi, ff = week_range_lun_vie(ref)
        titulo_per = "Semana " + fi.strftime("%d/%m") + " - " + ff.strftime("%d/%m/%Y")

    fi_s, ff_s = fi.strftime("%Y-%m-%d"), ff.strftime("%Y-%m-%d")
    horas_disp = horas_laborables_rango(fi_s, ff_s)

    conn = get_db(); cur = dcur(conn)
    try:
        cur.execute(
            "SELECT t.*, o.numero_orden, o.modelo, o.color, o.piezas_cortadas, o.fecha_final_corte, "
            "o.fecha_tampografia, o.tampografia_lista "
            "FROM tendidos t LEFT JOIN ordenes o ON o.id = t.orden_id "
            "WHERE t.fecha_inicio IS NOT NULL AND t.fecha_inicio >= " + ph() + " AND t.fecha_inicio <= " + ph() +
            " ORDER BY t.fecha_inicio, t.id",
            (fi_s, ff_s)
        )
        tendidos = cur.fetchall() or []
    except Exception as e:
        print("prod tendidos", e)
        tendidos = []

    try:
        cur.execute(
            "SELECT * FROM ordenes WHERE fecha_final_corte IS NOT NULL AND fecha_final_corte != '' "
            "AND fecha_final_corte >= " + ph() + " AND fecha_final_corte <= " + ph() + " ORDER BY fecha_final_corte, numero_orden",
            (fi_s, ff_s)
        )
        cortes = cur.fetchall() or []
    except Exception as e:
        print("prod cortes", e)
        cortes = []

    try:
        cur.execute(
            "SELECT * FROM ordenes WHERE fecha_tampografia IS NOT NULL AND fecha_tampografia != '' "
            "AND fecha_tampografia >= " + ph() + " AND fecha_tampografia <= " + ph(),
            (fi_s, ff_s)
        )
        tampos = cur.fetchall() or []
    except Exception:
        tampos = []
    conn.close()

    personas = {}

    def ensure(p):
        if p not in personas:
            personas[p] = {
                "tendidos": 0, "bloques": 0, "metros": 0.0, "mins": 0,
                "ordenes_tendido": set(), "piezas_corte": 0.0, "ordenes_corte": set(),
                "detalle": []
            }
        return personas[p]

    for t in tendidos:
        p1 = (t.get("persona1") or "").strip()
        p2 = (t.get("persona2") or "").strip()
        mins = minutos_tendido(t.get("fecha_inicio"), t.get("hora_inicio"), t.get("fecha_fin"), t.get("hora_fin"))
        mins_cal = minutos_tendido_calendario(t.get("fecha_inicio"), t.get("hora_inicio"), t.get("fecha_fin"), t.get("hora_fin"))
        bls = bloques_from_tendido(t)
        metros = sum(metros_bloque(b) for b in bls)
        n_bl = len(bls)
        oid = t.get("orden_id")
        num = t.get("numero_orden") or ("#" + str(oid or ""))
        modelo = t.get("modelo") or ""
        pzas = int(t.get("piezas_cortadas") or 0)
        dia = (t.get("fecha_inicio") or "")[:10]
        pair = [p for p in [p1, p2] if p]
        for p in pair:
            st = ensure(p)
            st["tendidos"] += 1
            st["bloques"] += n_bl
            st["metros"] += metros
            if mins is not None and mins > 0:
                st["mins"] += mins
            if oid:
                st["ordenes_tendido"].add(oid)
            # piezas: solo una vez por orden por persona
            if pzas > 0 and oid and oid not in st["ordenes_corte"]:
                share = pzas / max(len(pair), 1)
                st["piezas_corte"] += share
                st["ordenes_corte"].add(oid)
            st["detalle"].append({
                "dia": dia, "orden": num, "modelo": modelo,
                "mins": mins or 0, "mins_cal": mins_cal or 0,
                "metros": metros, "bloques": n_bl,
                "piezas": (pzas / max(len(pair), 1)) if (pzas and oid) else 0,
                "inicio": str(t.get("hora_inicio") or ""),
                "fin": str(t.get("hora_fin") or ""),
                "fi": str(t.get("fecha_inicio") or "")[:10],
                "ff": str(t.get("fecha_fin") or "")[:10],
            })

    total_piezas_corte = sum(int(c.get("piezas_cortadas") or 0) for c in cortes)
    total_ordenes_corte = len(cortes)
    total_tampos = len(tampos)
    total_metros = sum(st["metros"] for st in personas.values())
    # horas reportadas: cada tendido se suma a 2 personas, no duplicar en total area
    total_mins_tendidos = 0
    seen_tid = set()
    for t in tendidos:
        tid = t.get("id")
        if tid in seen_tid:
            continue
        seen_tid.add(tid)
        m = minutos_tendido(t.get("fecha_inicio"), t.get("hora_inicio"), t.get("fecha_fin"), t.get("hora_fin"))
        if m:
            total_mins_tendidos += m

    # Piezas por dia
    piezas_dia = {}
    for c in cortes:
        d = (c.get("fecha_final_corte") or "")[:10]
        if not d:
            continue
        piezas_dia.setdefault(d, {"ordenes": 0, "piezas": 0})
        piezas_dia[d]["ordenes"] += 1
        piezas_dia[d]["piezas"] += int(c.get("piezas_cortadas") or 0)
    piezas_dia_list = sorted(piezas_dia.items(), key=lambda x: x[0], reverse=True)

    lista = sorted(personas.items(), key=lambda x: x[1]["metros"], reverse=True)

    tabs = ""
    for key, label in [("dia", "Dia"), ("semana", "Semana"), ("mes", "Mes")]:
        cls = "btn-primary" if periodo == key else "btn-outline"
        tabs += '<a class="btn %s btn-sm" href="/productividad?periodo=%s&fecha=%s">%s</a> ' % (cls, key, fecha_ref, label)

    rows = ""
    for nombre, st in lista:
        horas_rep = st["mins"] / 60.0
        pct = (horas_rep / horas_disp * 100) if horas_disp > 0 else 0
        rows += (
            "<tr>"
            "<td><strong><a href=\"/productividad?periodo=%s&fecha=%s&persona=%s\">%s</a></strong></td>"
            "<td>%s</td><td>%s</td><td>%.1f m</td><td>%.1f h</td>"
            "<td>%s</td><td>%.0f</td><td>%.0f%%</td>"
            "</tr>"
        ) % (
            periodo, fecha_ref, nombre.replace(" ", "%20"), nombre,
            st["tendidos"], st["bloques"], st["metros"], horas_rep,
            len(st["ordenes_tendido"]), st["piezas_corte"], min(pct, 999)
        )
    if not rows:
        rows = '<tr><td colspan="8">Sin registros de tendido en este periodo.</td></tr>'

    persona_q = (request.args.get("persona") or "").strip()
    detalle_html = ""
    if persona_q and persona_q in personas:
        st = personas[persona_q]
        drows = ""
        for d in sorted(st["detalle"], key=lambda x: (x["dia"], x["orden"]), reverse=True):
            nota = ""
            if d["mins"] == 0 and not d["fin"]:
                nota = " <em style='color:#94a3b8'>(sin hora fin)</em>"
            elif d["mins_cal"] and d["mins"] and d["mins_cal"] > d["mins"] + 30:
                nota = " <span style='color:#64748b;font-size:.75rem'>(reloj %s min → laboral %s min)</span>" % (d["mins_cal"], d["mins"])
            drows += (
                "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%.1f m</td>"
                "<td><strong>%s min</strong>%s</td><td>%.0f</td></tr>"
            ) % (
                d["dia"], d["orden"], d.get("modelo") or "—", d["bloques"], d["metros"],
                d["mins"], nota, d["piezas"]
            )
        detalle_html = (
            '<div class="card"><h2>Detalle: ' + persona_q + ' — ' + titulo_per + '</h2>'
            '<p>Tendidos: <strong>%s</strong> · Bloques: <strong>%s</strong> · Metros: <strong>%.1f m</strong> · '
            'Horas laborables reportadas: <strong>%.1f h</strong> · Ordenes: <strong>%s</strong> · '
            'Piezas corte (1 vez por orden): <strong>%.0f</strong></p>'
            '<table><thead><tr><th>Fecha</th><th>Orden</th><th>Modelo</th><th>Bloques</th><th>Metros</th><th>Minutos laborales</th><th>Piezas*</th></tr></thead>'
            '<tbody>%s</tbody></table>'
            '<p style="font-size:.8rem;color:#64748b;margin-top:.5rem">Minutos = solo jornada (Lun 8-14/15-18, Mar-Vie 8-14/15-17:30). '
            'No cuenta noche ni comida. Piezas solo se cuentan una vez por orden.</p>'
            '<a href="/productividad?periodo=%s&fecha=%s" class="btn btn-outline btn-sm">Cerrar detalle</a></div>'
        ) % (
            st["tendidos"], st["bloques"], st["metros"], st["mins"]/60.0,
            len(st["ordenes_tendido"]), st["piezas_corte"], drows, periodo, fecha_ref
        )

    # Tabla piezas por dia
    pd_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td><strong>%s</strong></td></tr>" % (d, v["ordenes"], v["piezas"])
        for d, v in piezas_dia_list
    ) or "<tr><td colspan=3>Sin cortes con fecha final en el periodo</td></tr>"

    # Informe ordenes modelo piezas
    ord_rows = ""
    for c in cortes:
        ord_rows += (
            "<tr><td>%s</td><td><strong>%s</strong></td><td>%s</td><td>%s</td>"
            "<td>%s</td><td><strong>%s</strong></td>"
            '<td><a href="/orden/%s" class="btn btn-outline btn-sm">Ver</a></td></tr>'
        ) % (
            (c.get("fecha_final_corte") or "")[:10],
            c.get("numero_orden") or "",
            c.get("modelo") or "—",
            c.get("color") or "—",
            c.get("piezas_programadas") or 0,
            c.get("piezas_cortadas") or 0,
            c.get("id")
        )
    if not ord_rows:
        ord_rows = "<tr><td colspan=7>Sin ordenes cortadas en el periodo</td></tr>"

    body = (
        '<div class="card"><h1>Productividad del personal</h1>'
        '<p style="color:#64748b">Horas = solo tiempo de jornada real (sin noche ni comida). '
        'Lun 8:00-18:00 (9h) · Mar-Vie 8:00-17:30 (8.5h)</p>'
        '<div style="margin:.6rem 0;display:flex;flex-wrap:wrap;gap:.4rem;align-items:center">' + tabs +
        '<form method="GET" style="display:inline-flex;gap:.4rem;align-items:center;margin-left:.5rem">'
        '<input type="hidden" name="periodo" value="' + periodo + '">'
        '<label style="margin:0">Fecha ref.</label>'
        '<input type="date" name="fecha" value="' + fecha_ref + '" style="margin:0;width:auto">'
        '<button type="submit" class="btn btn-outline btn-sm">Ver</button></form></div>'
        '<p><strong>' + titulo_per + '</strong> · Horas laborables del periodo: <strong>%.1f h</strong></p></div>'
        % horas_disp
        +
        '<div class="card"><h2>Resumen del area</h2>'
        '<div style="display:flex;flex-wrap:wrap;gap:1rem">'
        '<div class="stat"><div class="n">%.1f m</div><div class="l">Metros tendidos</div></div>'
        '<div class="stat"><div class="n">%.1f h</div><div class="l">Horas tendido (suma tendidos)</div></div>'
        '<div class="stat"><div class="n">%s</div><div class="l">Ordenes cortadas</div></div>'
        '<div class="stat"><div class="n">%s</div><div class="l">Piezas cortadas</div></div>'
        '<div class="stat"><div class="n">%s</div><div class="l">Tampografias</div></div>'
        '</div></div>'
        % (total_metros, total_mins_tendidos/60.0, total_ordenes_corte, total_piezas_corte, total_tampos)
        +
        '<div class="card"><h2>Piezas de corte por dia</h2>'
        '<table><thead><tr><th>Fecha</th><th>Ordenes</th><th>Piezas cortadas</th></tr></thead>'
        '<tbody>' + pd_rows + '</tbody></table></div>'
        +
        '<div class="card"><h2>Informe de ordenes cortadas (modelo y piezas)</h2>'
        '<table><thead><tr><th>Fecha fin corte</th><th>Orden</th><th>Modelo</th><th>Color</th>'
        '<th>Prog.</th><th>Cortadas</th><th></th></tr></thead><tbody>' + ord_rows + '</tbody></table></div>'
        +
        '<div class="card"><h2>Desempeno por persona</h2>'
        '<p style="font-size:.85rem;color:#64748b;margin-bottom:.5rem">'
        'Horas = solo jornada laboral. Piezas de una orden se cuentan una sola vez por persona (no se duplican si hay varios tendidos).</p>'
        '<table><thead><tr>'
        '<th>Persona</th><th>Tendidos</th><th>Bloques</th><th>Metros</th><th>Horas lab.</th>'
        '<th>Ordenes</th><th>Piezas*</th><th>% jornada</th>'
        '</tr></thead><tbody>' + rows + '</tbody></table></div>'
        + detalle_html
    )
    return page("Productividad", body, session)




@app.route("/checklist/confirmar/<int:orden_id>", methods=["POST"])
@login_required
def checklist_confirmar(orden_id):
    if not can_edit_checklist_aduana():
        return page("No autorizado", '<div class="alert alert-err">No tienes permiso para confirmar checklist.</div>'
                    '<a href="/checklist" class="btn btn-outline">Volver</a>', session)
    user = session.get("nombre") or session.get("usuario")
    muestra = request.form.get("muestra_maestra", "No")
    entrega_ok = request.form.get("aduana_entrega_ok", "No")
    fecha_ent = request.form.get("aduana_fecha_entrega", "").strip()
    pasos_ok = request.form.get("aduana_pasos_ok", "No")
    obs = request.form.get("aduana_obs", "").strip()
    if entrega_ok == "Si" and not fecha_ent:
        fecha_ent = datetime.now().strftime("%Y-%m-%d")
    conn = get_db(); cur = conn.cursor()
    try:
        # ensure columns
        if USE_POSTGRES:
            for sql in [
                "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS muestra_maestra TEXT DEFAULT 'No'",
                "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS aduana_entrega_ok TEXT DEFAULT 'No'",
                "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS aduana_fecha_entrega TEXT",
                "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS aduana_pasos_ok TEXT DEFAULT 'No'",
                "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS aduana_usuario TEXT",
                "ALTER TABLE ordenes ADD COLUMN IF NOT EXISTS aduana_obs TEXT",
            ]:
                try:
                    cur.execute(sql)
                except Exception:
                    pass
            cur.execute("""UPDATE ordenes SET muestra_maestra=%s, aduana_entrega_ok=%s, aduana_fecha_entrega=%s,
                aduana_pasos_ok=%s, aduana_usuario=%s, aduana_obs=%s WHERE id=%s""",
                (muestra, entrega_ok, fecha_ent or None, pasos_ok, user, obs, orden_id))
        else:
            for col in ["muestra_maestra", "aduana_entrega_ok", "aduana_fecha_entrega", "aduana_pasos_ok", "aduana_usuario", "aduana_obs"]:
                try:
                    cur.execute("ALTER TABLE ordenes ADD COLUMN %s TEXT" % col)
                except Exception:
                    pass
            cur.execute("""UPDATE ordenes SET muestra_maestra=?, aduana_entrega_ok=?, aduana_fecha_entrega=?,
                aduana_pasos_ok=?, aduana_usuario=?, aduana_obs=? WHERE id=?""",
                (muestra, entrega_ok, fecha_ent or None, pasos_ok, user, obs, orden_id))
        conn.commit()
        try:
            cur2 = dcur(conn) if False else None
        except Exception:
            pass
        # notificacion
        try:
            conn2 = get_db(); cur2 = dcur(conn2)
            cur2.execute("SELECT numero_orden FROM ordenes WHERE id=" + ph(), (orden_id,))
            row = cur2.fetchone()
            num = row["numero_orden"] if row and isinstance(row, dict) else (row[0] if row else orden_id)
            conn2.close()
            crear_notificacion(orden_id, num, "Aduana confirmo checklist (entrega/muestra/pasos)")
        except Exception as e:
            print("notif aduana", e)
    except Exception as e:
        conn.rollback()
        conn.close()
        return page("Error", '<div class="alert alert-err">' + str(e) + '</div><a href="/checklist" class="btn btn-outline">Volver</a>', session)
    conn.close()
    ref = request.form.get("redirect") or request.referrer or "/checklist"
    return redirect(ref)


@app.route("/checklist")
@login_required
def checklist():
    """Checklist de procesos; filtro por estado y por fecha de agenda (salida a maquila)."""
    filtro = (request.args.get("filtro") or "pendientes").strip()
    q = (request.args.get("q") or "").strip()
    fecha_agenda = (request.args.get("fecha_agenda") or "").strip()  # YYYY-MM-DD or vacio = todas
    vista_agenda = (request.args.get("vista") or "").strip()  # hoy | manana | 7dias | vacio

    hoy = datetime.now().date()
    trad = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sabado", "Sunday": "Domingo"
    }

    # Resolver rango / fecha desde vista rapida
    fechas_set = None  # None = no filtrar por agenda; set de strings YYYY-MM-DD
    if vista_agenda == "hoy":
        fecha_agenda = hoy.strftime("%Y-%m-%d")
        fechas_set = {fecha_agenda}
    elif vista_agenda == "manana":
        man = hoy + timedelta(days=1)
        fecha_agenda = man.strftime("%Y-%m-%d")
        fechas_set = {fecha_agenda}
    elif vista_agenda == "7dias":
        fechas_set = {(hoy + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(8)}
        fecha_agenda = ""
    elif fecha_agenda:
        fechas_set = {fecha_agenda[:10]}

    conn = get_db(); cur = dcur(conn)
    try:
        if fechas_set and len(fechas_set) == 1:
            fs = list(fechas_set)[0]
            cur.execute(
                "SELECT * FROM ordenes WHERE fecha_salida_maquila = " + ph() + " ORDER BY numero_orden",
                (fs,)
            )
        elif fechas_set and len(fechas_set) > 1:
            # proximos dias: traer todas y filtrar en python (compatible sqlite/pg)
            cur.execute("SELECT * FROM ordenes ORDER BY fecha_salida_maquila NULLS LAST, id DESC LIMIT 800" if USE_POSTGRES else
                        "SELECT * FROM ordenes ORDER BY id DESC LIMIT 800")
            ordenes = cur.fetchall() or []
            ordenes = [o for o in ordenes if (o.get("fecha_salida_maquila") or "")[:10] in fechas_set]
            # skip re-fetch
            cur.execute("SELECT 1")  # noop keep flow
        else:
            cur.execute("SELECT * FROM ordenes ORDER BY id DESC LIMIT 500")
            ordenes = None
        if fechas_set is None or len(fechas_set) == 1:
            ordenes = cur.fetchall() or []
        elif ordenes is None:
            ordenes = cur.fetchall() or []
    except Exception as e:
        print("checklist ordenes", e)
        try:
            cur.execute("SELECT * FROM ordenes ORDER BY id DESC LIMIT 500")
            ordenes = cur.fetchall() or []
            if fechas_set:
                ordenes = [o for o in ordenes if (o.get("fecha_salida_maquila") or "")[:10] in fechas_set]
        except Exception as e2:
            print(e2)
            ordenes = []

    tend_map = {}
    try:
        cur.execute("SELECT * FROM tendidos ORDER BY id")
        for t in (cur.fetchall() or []):
            oid = t.get("orden_id")
            if oid is not None:
                tend_map.setdefault(oid, []).append(t)
    except Exception as e:
        print("checklist tendidos", e)
    conn.close()

    def ok_icon(yes):
        return '<span style="color:#059669;font-weight:700">✓</span>' if yes else '<span style="color:#cbd5e1">○</span>'

    def fmt_fecha(*vals):
        for v in vals:
            if v:
                s = str(v).strip()[:16]
                if s:
                    return s
        return "—"

    rows = ""
    n_pend = n_ok = n_all = 0
    for o in ordenes:
        oid = o.get("id")
        num = o.get("numero_orden") or ""
        modelo = o.get("modelo") or "—"
        color = o.get("color") or "—"
        maq = o.get("maquilero") or "—"
        f_sal_raw = (o.get("fecha_salida_maquila") or "").strip()[:10]

        if fechas_set and f_sal_raw not in fechas_set:
            continue

        if q:
            blob = (" ".join([str(num), str(modelo), str(color), str(maq), f_sal_raw])).lower()
            if q.lower() not in blob:
                continue

        ts = tend_map.get(oid) or []
        tiene_tendido = len(ts) > 0
        tendido_completo = any((t.get("fecha_fin") and t.get("hora_fin")) for t in ts)
        f_tend = "—"
        if ts:
            t0 = ts[0]
            f_tend = fmt_fecha((str(t0.get("fecha_inicio") or "")[:10] + " " + str(t0.get("hora_inicio") or "")).strip())
            if tendido_completo:
                for t in reversed(ts):
                    if t.get("fecha_fin") and t.get("hora_fin"):
                        f_tend = fmt_fecha(str(t.get("fecha_inicio") or "")[:10] + " " + str(t.get("hora_inicio") or "")) + " → " + fmt_fecha(str(t.get("fecha_fin") or "")[:10] + " " + str(t.get("hora_fin") or ""))
                        break

        p_cort = int(o.get("piezas_cortadas") or 0)
        f_fin_c = (o.get("fecha_final_corte") or "").strip()
        f_ini_c = (o.get("fecha_inicio_corte") or "").strip()
        corte_ok = bool(f_fin_c) or p_cort > 0
        f_corte = fmt_fecha(f_fin_c, f_ini_c)
        if f_ini_c and f_fin_c and f_ini_c != f_fin_c:
            f_corte = f_ini_c + " → " + f_fin_c

        hab = (o.get("habilitado_estado") or "").strip()
        hab_ok = hab.lower() in ("completo", "parcial", "si", "sí") or bool(hab)
        f_hab = hab + ((" · " + str(o.get("habilitado_usuario") or "")) if o.get("habilitado_usuario") else "") if hab else "—"

        tamp = (o.get("tampografia_lista") or "").strip()
        f_tamp = (o.get("fecha_tampografia") or "").strip()
        tamp_ok = tamp.lower() in ("si", "sí", "yes", "lista", "completo") or bool(f_tamp)
        f_tamp_show = fmt_fecha(f_tamp) if f_tamp else (("Lista" if tamp_ok else "—") if tamp else "—")

        f_sal = (o.get("fecha_salida_maquila") or "").strip()
        ubi = (o.get("ubicacion") or "Taller")
        enviado = (o.get("estado_actual") or "") in ("Enviado_Maquila", "Entregado_Parcial", "Terminado") or ubi == "Maquila"
        salida_ok = enviado and bool(f_sal or maq != "—")
        prog_ok = bool(maq != "—" and f_sal)
        f_salida = fmt_fecha(f_sal)
        if maq != "—":
            f_salida = (f_salida if f_salida != "—" else "Programado") + " · " + maq

        
        # Aduana / muestra maestra
        muestra = (o.get("muestra_maestra") or "No").strip()
        muestra_ok = muestra.lower() in ("si", "sí", "yes")
        adu_ent = (o.get("aduana_entrega_ok") or "No").strip()
        adu_ent_ok = adu_ent.lower() in ("si", "sí", "yes")
        adu_pasos = (o.get("aduana_pasos_ok") or "No").strip()
        adu_pasos_ok = adu_pasos.lower() in ("si", "sí", "yes")
        adu_fecha = (o.get("aduana_fecha_entrega") or "").strip()
        adu_user = (o.get("aduana_usuario") or "").strip()
        adu_obs = (o.get("aduana_obs") or "").strip()
        f_muestra = "Si · lleva muestra" if muestra_ok else "No"
        f_aduana = ""
        if adu_ent_ok:
            f_aduana += "Entregado"
            if adu_fecha:
                f_aduana += " " + adu_fecha
        else:
            f_aduana += "Sin entrega"
        if adu_pasos_ok:
            f_aduana += " · Pasos OK"
        if adu_user:
            f_aduana += " · " + adu_user
        # Formulario aduana
        form_adu = ""
        if can_edit_checklist_aduana():
            qs = request.query_string.decode() if request.query_string else ""
            redir = "/checklist" + (("?" + qs) if qs else "")
            form_adu = (
                '<form method="POST" action="/checklist/confirmar/%s" style="margin-top:.35rem;text-align:left;font-size:.72rem">'
                '<input type="hidden" name="redirect" value="%s">'
                '<label style="font-size:.7rem">Muestra maestra</label>'
                '<select name="muestra_maestra" style="margin-bottom:.25rem;padding:.2rem;font-size:.72rem">'
                '<option value="No"%s>No</option><option value="Si"%s>Si, se lleva</option></select>'
                '<label style="font-size:.7rem">Entregado a maquilero</label>'
                '<select name="aduana_entrega_ok" style="margin-bottom:.25rem;padding:.2rem;font-size:.72rem">'
                '<option value="No"%s>No</option><option value="Si"%s>Si</option></select>'
                '<label style="font-size:.7rem">Fecha entrega</label>'
                '<input type="date" name="aduana_fecha_entrega" value="%s" style="margin-bottom:.25rem;padding:.2rem;font-size:.72rem">'
                '<label style="font-size:.7rem">Todos los pasos OK</label>'
                '<select name="aduana_pasos_ok" style="margin-bottom:.25rem;padding:.2rem;font-size:.72rem">'
                '<option value="No"%s>No</option><option value="Si"%s>Si</option></select>'
                '<input name="aduana_obs" value="%s" placeholder="Obs." style="margin-bottom:.25rem;padding:.2rem;font-size:.72rem">'
                '<button type="submit" class="btn btn-primary btn-sm" style="font-size:.7rem;padding:.2rem .45rem">Confirmar</button></form>'
            ) % (
                oid, redir,
                "" if muestra_ok else " selected", " selected" if muestra_ok else "",
                "" if adu_ent_ok else " selected", " selected" if adu_ent_ok else "",
                adu_fecha,
                "" if adu_pasos_ok else " selected", " selected" if adu_pasos_ok else "",
                adu_obs.replace('"', "&quot;"),
            )

        checks = [corte_ok, hab_ok, tamp_ok, prog_ok]
        if tiene_tendido:
            checks.insert(0, tendido_completo)
        else:
            checks.insert(0, True)
        completo = all(checks)
        n_all += 1
        if completo:
            n_ok += 1
        else:
            n_pend += 1

        if filtro == "pendientes" and completo:
            continue
        if filtro == "completas" and not completo:
            continue

        estado_row = '<span class="badge badge-ok">Listo entrega</span>' if completo else '<span class="badge badge-pend">Pendiente</span>'
        agenda_badge = ""
        if f_sal_raw:
            try:
                fd = datetime.strptime(f_sal_raw, "%Y-%m-%d").date()
                nom = trad.get(fd.strftime("%A"), fd.strftime("%A"))
                if fd == hoy:
                    agenda_badge = ' <span class="badge badge-info">HOY</span>'
                elif fd == hoy + timedelta(days=1):
                    agenda_badge = ' <span class="badge badge-warn">MANANA</span>'
            except Exception:
                nom = ""
            agenda_badge = (agenda_badge or "") + (' <small style="color:#64748b">' + f_sal_raw + "</small>")

        rows += (
            "<tr>"
            '<td><strong><a href="/orden/%s">%s</a></strong>%s</td>'
            "<td>%s<br><small style='color:#64748b'>%s</small></td>"
            "<td>%s</td>"
            "<td style='text-align:center'>%s<br><small>%s</small></td>"
            "<td style='text-align:center'>%s<br><small>%s</small></td>"
            "<td style='text-align:center'>%s<br><small>%s</small></td>"
            "<td style='text-align:center'>%s<br><small>%s</small></td>"
            "<td style='text-align:center'>%s<br><small>%s</small></td>"
            "<td style='text-align:center'>%s<br><small>%s</small></td>"
            "<td style='text-align:center;min-width:140px'>%s<br><small>%s</small></td>"
            "<td>%s</td>"
            "</tr>"
        ) % (
            oid, num, agenda_badge,
            modelo, color,
            maq if maq != "—" else "<span style='color:#94a3b8'>—</span>",
            ok_icon(tendido_completo if tiene_tendido else False) if tiene_tendido else '<span style="color:#94a3b8">—</span>',
            f_tend if tiene_tendido else "Sin registro",
            ok_icon(corte_ok), f_corte + ((" · %s pzas" % p_cort) if p_cort else ""),
            ok_icon(hab_ok), f_hab,
            ok_icon(tamp_ok), f_tamp_show,
            ok_icon(salida_ok or prog_ok), f_salida,
            ok_icon(muestra_ok), f_muestra,
            ok_icon(adu_ent_ok and adu_pasos_ok), f_aduana + form_adu,
            estado_row,
        )

    # Tabs estado
    qs_base = "&fecha_agenda=" + (fecha_agenda or "") + "&vista=" + (vista_agenda or "") + "&q=" + q
    tabs = ""
    for key, label in [("pendientes", "Pendientes"), ("completas", "Listas entrega"), ("todas", "Todas")]:
        cls = "btn-primary" if filtro == key else "btn-outline"
        tabs += '<a class="btn %s btn-sm" href="/checklist?filtro=%s%s">%s</a> ' % (cls, key, qs_base, label)

    # Tabs agenda
    def abtn(vista, label, active):
        cls = "btn-primary" if active else "btn-outline"
        return '<a class="btn %s btn-sm" href="/checklist?filtro=%s&vista=%s&q=%s">%s</a> ' % (cls, filtro, vista, q, label)

    agenda_tabs = (
        abtn("", "Toda la agenda", not vista_agenda and not fecha_agenda)
        + abtn("hoy", "Hoy en agenda", vista_agenda == "hoy")
        + abtn("manana", "Manana", vista_agenda == "manana")
        + abtn("7dias", "Proximos 7 dias", vista_agenda == "7dias")
    )

    # Mini calendario proximos 7 dias con conteo
    mini = ""
    # need counts - simple from ordenes all with fecha
    conn2 = get_db(); cur2 = dcur(conn2)
    try:
        cur2.execute("SELECT fecha_salida_maquila FROM ordenes WHERE fecha_salida_maquila IS NOT NULL AND fecha_salida_maquila != ''")
        all_f = cur2.fetchall() or []
    except Exception:
        all_f = []
    conn2.close()
    count_by = {}
    for r in all_f:
        fs = (r.get("fecha_salida_maquila") if isinstance(r, dict) else r[0]) or ""
        fs = str(fs)[:10]
        if fs:
            count_by[fs] = count_by.get(fs, 0) + 1

    for i in range(8):
        d = hoy + timedelta(days=i)
        ds = d.strftime("%Y-%m-%d")
        n = count_by.get(ds, 0)
        nom = trad.get(d.strftime("%A"), "")[:3]
        active = (fecha_agenda == ds) or (vista_agenda == "hoy" and i == 0) or (vista_agenda == "manana" and i == 1)
        border = "border:2px solid #3b82f6;" if active else "border:1px solid #e2e8f0;"
        mini += (
            '<a href="/checklist?filtro=%s&fecha_agenda=%s&q=%s" style="display:inline-block;text-align:center;padding:.45rem .55rem;margin:.2rem;border-radius:8px;text-decoration:none;color:#1e293b;background:#fff;%s min-width:64px">'
            '<div style="font-size:.7rem;color:#64748b">%s</div>'
            '<div style="font-weight:700">%s</div>'
            '<div style="font-size:.72rem;color:%s">%s ord</div></a>'
        ) % (filtro, ds, q, border, nom, d.strftime("%d/%m"), "#059669" if n else "#94a3b8", n)

    titulo_agenda = "Todas las ordenes"
    if vista_agenda == "hoy" or fecha_agenda == hoy.strftime("%Y-%m-%d"):
        titulo_agenda = "Programadas para HOY (" + hoy.strftime("%d/%m/%Y") + ")"
    elif vista_agenda == "manana":
        titulo_agenda = "Programadas para manana"
    elif vista_agenda == "7dias":
        titulo_agenda = "Programadas en los proximos 7 dias"
    elif fecha_agenda:
        titulo_agenda = "Programadas el " + fecha_agenda

    body = (
        '<div class="card"><h1>Checklist de procesos</h1>'
        '<p style="color:#64748b">Filtra por lo programado en la <a href="/agenda">Agenda</a> (fecha de salida a maquila) '
        'y confirma tendido, corte, habilitado, tampografia y salida.</p>'
        '<div style="margin:.5rem 0"><strong>Por estado:</strong> ' + tabs + "</div>"
        '<div style="margin:.5rem 0"><strong>Por agenda:</strong> ' + agenda_tabs + "</div>"
        '<div style="margin:.6rem 0">' + mini + "</div>"
        '<form method="GET" style="display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-top:.5rem">'
        '<input type="hidden" name="filtro" value="' + filtro + '">'
        '<label style="margin:0">Fecha agenda</label>'
        '<input type="date" name="fecha_agenda" value="' + (fecha_agenda or "") + '" style="margin:0;width:auto">'
        '<input name="q" value="' + q + '" placeholder="Orden, modelo, maquilero" style="margin:0;min-width:160px">'
        '<button type="submit" class="btn btn-primary btn-sm">Filtrar</button> '
        '<a href="/checklist" class="btn btn-outline btn-sm">Limpiar</a></form>'
        '<p style="margin-top:.7rem"><strong>' + titulo_agenda + '</strong> · '
        'Pendientes: <strong>%s</strong> · Listas: <strong>%s</strong> · En vista: <strong>%s</strong></p></div>'
        % (n_pend, n_ok, n_all)
        +
        '<div class="card" style="overflow-x:auto">'
        '<table style="font-size:.8rem"><thead><tr>'
        '<th>Orden / Fecha agenda</th><th>Modelo / Color</th><th>Maquilero</th>'
        '<th>Tendido</th><th>Corte</th><th>Habilitado</th><th>Tampografia</th><th>Salida maquila</th><th>Muestra maestra</th><th>Aduana</th><th>Estado</th>'
        '</tr></thead><tbody>'
        + (rows or '<tr><td colspan="11">No hay ordenes programadas con este filtro. Revisa la Agenda o limpia el filtro de fecha.</td></tr>')
        + '</tbody></table>'
        '<p style="font-size:.78rem;color:#64748b;margin-top:.8rem">'
        '✓ = listo · ○ = pendiente · La fecha de agenda es la <strong>fecha de salida a maquila</strong> programada.</p></div>'
    )
    return page("Checklist", body, session)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
