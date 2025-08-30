from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from datetime import datetime, date, timedelta
import psycopg2.extras
from ..db_legacy import conectar

# (Opcional) sanitizar texto libre
import bleach
ALLOWED_TAGS = ["p","br","ul","ol","li","strong","em","b","i","u","span","div"]
ALLOWED_ATTRS = {"*": ["class","style"]}

def clean_html(s):
    return bleach.clean(s or "", tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

minutas_bp = Blueprint("minutas", __name__, url_prefix="/admin/minutas")

def fetchall(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchall()

def fetchone(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchone()

def execute(q, p=()):
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(q, p)
        conn.commit()

# ---------------------------
# LISTA (con recordatorios)
# ---------------------------
@minutas_bp.route("/")
def lista():
    items = fetchall("""
        SELECT id, fecha_reunion, asunto, created_at
        FROM meeting_minutes
        ORDER BY created_at DESC
        LIMIT 200
    """)
    # Compromisos próximos (7 días) que NO estén cerrados
    proximos = fetchall("""
        SELECT mc.id, mc.descripcion, mc.responsable, mc.eta, mm.id AS minuta_id, mm.asunto
        FROM meeting_commitments mc
        JOIN meeting_minutes mm ON mm.id = mc.meeting_id
        WHERE mc.estatus <> 'CERRADO'
          AND mc.eta IS NOT NULL
          AND mc.eta <= %s
        ORDER BY mc.eta ASC
        LIMIT 10
    """, (date.today() + timedelta(days=7),))
    return render_template("minutas_list.html", items=items, proximos=proximos)

# ---------------------------
# VER (detalle de una minuta)
# ---------------------------
@minutas_bp.route("/<int:minuta_id>")
def ver(minuta_id):
    minuta = fetchone("""
        SELECT id, fecha_reunion, asunto, notas, acuerdos, created_at
        FROM meeting_minutes
        WHERE id=%s
    """, (minuta_id,))
    if not minuta:
        abort(404)

    asistentes = fetchall("""
        SELECT nombre, cargo
        FROM meeting_attendees
        WHERE meeting_id=%s
        ORDER BY id
    """, (minuta_id,))

    compromisos = fetchall("""
        SELECT id, descripcion, responsable, eta, estatus
        FROM meeting_commitments
        WHERE meeting_id=%s
        ORDER BY id
    """, (minuta_id,))

    return render_template("minutas_view.html",
                           minuta=minuta,
                           asistentes=asistentes,
                           compromisos=compromisos)

# ---------------------------
# NUEVA
# ---------------------------
@minutas_bp.route("/nueva", methods=["GET","POST"])
def nueva():
    if request.method == "POST":
        # Cabecera
        fecha_reunion = request.form.get("fecha_reunion","").strip()
        asunto = request.form.get("asunto","").strip()
        notas = clean_html(request.form.get("notas",""))
        acuerdos = clean_html(request.form.get("acuerdos",""))

        if not fecha_reunion or not asunto:
            flash("Fecha y Asunto son obligatorios.", "warning")
            return redirect(url_for("minutas.nueva"))

        # Insert minuta
        minuta = fetchone("""
            INSERT INTO meeting_minutes (fecha_reunion, asunto, notas, acuerdos)
            VALUES (%s,%s,%s,%s)
            RETURNING id
        """, (fecha_reunion, asunto, notas, acuerdos))

        meeting_id = minuta["id"]

        # Asistentes
        asistentes_nombres = request.form.getlist("asistentes_nombre[]")
        asistentes_cargos = request.form.getlist("asistentes_cargo[]")
        for nombre, cargo in zip(asistentes_nombres, asistentes_cargos):
            nombre = (nombre or "").strip()
            cargo = (cargo or "").strip()
            if nombre:
                execute("""
                    INSERT INTO meeting_attendees (meeting_id, nombre, cargo)
                    VALUES (%s,%s,%s)
                """, (meeting_id, nombre, cargo))

        # Compromisos
        comp_desc = request.form.getlist("comp_desc[]")
        comp_resp = request.form.getlist("comp_resp[]")
        comp_eta  = request.form.getlist("comp_eta[]")
        for d, r, e in zip(comp_desc, comp_resp, comp_eta):
            d = (d or "").strip()
            r = (r or "").strip()
            e = (e or "").strip()
            if d and r:
                execute("""
                    INSERT INTO meeting_commitments (meeting_id, descripcion, responsable, eta)
                    VALUES (%s,%s,%s,%s)
                """, (meeting_id, d, r, e if e else None))

        flash("Minuta guardada.", "success")
        return redirect(url_for("minutas.ver", minuta_id=meeting_id))

    hoy = datetime.now().strftime("%Y-%m-%d")
    return render_template("minutas_form.html", hoy=hoy, minuta=None,
                           asistentes=[], compromisos=[])

# ---------------------------
# EDITAR
# ---------------------------
@minutas_bp.route("/<int:minuta_id>/editar", methods=["GET","POST"])
def editar(minuta_id):
    minuta = fetchone("""
        SELECT id, fecha_reunion, asunto, notas, acuerdos
        FROM meeting_minutes
        WHERE id=%s
    """, (minuta_id,))
    if not minuta:
        abort(404)

    if request.method == "POST":
        fecha_reunion = request.form.get("fecha_reunion","").strip()
        asunto = request.form.get("asunto","").strip()
        notas = clean_html(request.form.get("notas",""))
        acuerdos = clean_html(request.form.get("acuerdos",""))

        if not fecha_reunion or not asunto:
            flash("Fecha y Asunto son obligatorios.", "warning")
            return redirect(url_for("minutas.editar", minuta_id=minuta_id))

        execute("""
            UPDATE meeting_minutes
               SET fecha_reunion=%s,
                   asunto=%s,
                   notas=%s,
                   acuerdos=%s
             WHERE id=%s
        """, (fecha_reunion, asunto, notas, acuerdos, minuta_id))

        # Reemplazamos asistentes y compromisos (más simple)
        execute("DELETE FROM meeting_attendees WHERE meeting_id=%s", (minuta_id,))
        execute("DELETE FROM meeting_commitments WHERE meeting_id=%s", (minuta_id,))

        asistentes_nombres = request.form.getlist("asistentes_nombre[]")
        asistentes_cargos = request.form.getlist("asistentes_cargo[]")
        for nombre, cargo in zip(asistentes_nombres, asistentes_cargos):
            nombre = (nombre or "").strip()
            cargo = (cargo or "").strip()
            if nombre:
                execute("""
                    INSERT INTO meeting_attendees (meeting_id, nombre, cargo)
                    VALUES (%s,%s,%s)
                """, (minuta_id, nombre, cargo))

        comp_desc = request.form.getlist("comp_desc[]")
        comp_resp = request.form.getlist("comp_resp[]")
        comp_eta  = request.form.getlist("comp_eta[]")
        comp_status = request.form.getlist("comp_status[]")  # viene del select en el form
        for d, r, e, st in zip(comp_desc, comp_resp, comp_eta, comp_status):
            d = (d or "").strip()
            r = (r or "").strip()
            e = (e or "").strip()
            st = (st or "PENDIENTE").strip().upper()
            if d and r:
                execute("""
                    INSERT INTO meeting_commitments (meeting_id, descripcion, responsable, eta, estatus)
                    VALUES (%s,%s,%s,%s,%s)
                """, (minuta_id, d, r, e if e else None, st))

        flash("Minuta actualizada.", "success")
        return redirect(url_for("minutas.ver", minuta_id=minuta_id))

    asistentes = fetchall("""
        SELECT nombre, cargo
        FROM meeting_attendees
        WHERE meeting_id=%s
        ORDER BY id
    """, (minuta_id,))
    compromisos = fetchall("""
        SELECT descripcion, responsable, eta, estatus
        FROM meeting_commitments
        WHERE meeting_id=%s
        ORDER BY id
    """, (minuta_id,))
    return render_template("minutas_form.html", hoy=minuta["fecha_reunion"],
                           minuta=minuta, asistentes=asistentes, compromisos=compromisos)

# ---------------------------
# ELIMINAR
# ---------------------------
@minutas_bp.route("/<int:minuta_id>/eliminar", methods=["POST"])
def eliminar(minuta_id):
    # borrado en cascada por FK
    execute("DELETE FROM meeting_minutes WHERE id=%s", (minuta_id,))
    flash("Minuta eliminada.", "success")
    return redirect(url_for("minutas.lista"))

# ---------------------------
# CAMBIAR ESTATUS COMPROMISO (rápido)
# ---------------------------
@minutas_bp.route("/compromisos/<int:comp_id>/estatus", methods=["POST"])
def compromiso_estatus(comp_id):
    nuevo = (request.form.get("estatus","PENDIENTE")).upper()
    if nuevo not in ("PENDIENTE","EN PROCESO","CERRADO"):
        nuevo = "PENDIENTE"
    execute("UPDATE meeting_commitments SET estatus=%s WHERE id=%s", (nuevo, comp_id))
    flash("Estatus de compromiso actualizado.", "success")
    # regresar a la referencia
    ref = request.headers.get("Referer") or url_for("minutas.lista")
    return redirect(ref)

# ---------------------------
# PDF (WeasyPrint)
# ---------------------------
@minutas_bp.route("/<int:minuta_id>/pdf")
def pdf(minuta_id):
    from weasyprint import HTML
    from flask import make_response

    minuta = fetchone("""
        SELECT id, fecha_reunion, asunto, notas, acuerdos, created_at
        FROM meeting_minutes
        WHERE id=%s
    """, (minuta_id,))
    if not minuta:
        abort(404)

    asistentes = fetchall("""
        SELECT nombre, cargo
        FROM meeting_attendees
        WHERE meeting_id=%s
        ORDER BY id
    """, (minuta_id,))

    compromisos = fetchall("""
        SELECT id, descripcion, responsable, eta, estatus
        FROM meeting_commitments
        WHERE meeting_id=%s
        ORDER BY id
    """, (minuta_id,))

    html_rendered = render_template("minutas_pdf.html",
                                    minuta=minuta, asistentes=asistentes, compromisos=compromisos)
    pdf_bytes = HTML(string=html_rendered, base_url=request.url_root).write_pdf()
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = f"inline; filename=minuta_{minuta_id}.pdf"
    return resp
