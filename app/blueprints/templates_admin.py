from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask import current_app, session, make_response
from markupsafe import Markup
from datetime import datetime
import psycopg2.extras
from weasyprint import HTML
import io

# Permisos / auth
from .auth_admin import admin_required
from ..auth.decorators import permiso_required

# Conector legacy
from ..db_legacy import conectar

# Jinja render en memoria
from flask import render_template_string

templates_bp = Blueprint("templates_admin", __name__, url_prefix="/admin/templates")

@templates_bp.before_request
@permiso_required("manage_templates")
def _guard_templates_perm():
    # Permiso granular
    pass

@templates_bp.before_request
def _guard_admin():
    # Guardado global (sesión admin)
    if not admin_required():
        return redirect(url_for("auth_admin.login"))

# ===== Utilidades DB =====
def fetchone(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchone()

def fetchall(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchall()

def execute(q, p=()):
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(q, p)
        conn.commit()

# ===== Sanitizador (anulado para respetar el HTML tal cual) =====
def sanitize_html(raw: str) -> str:
    # Passthrough: no tocar el HTML para preservar exactamente lo que el usuario pegó
    return raw or ""

# ===== Listado =====
@templates_bp.route("/")
def list_templates():
    items = fetchall("""
      SELECT DISTINCT ON (slug) id, slug, name, cascaron, version, is_active, updated_at
      FROM document_templates
      ORDER BY slug, version DESC
    """)
    return render_template("admin_templates_list.html", items=items)

# ===== Crear =====
@templates_bp.route("/new", methods=["GET","POST"])
def create_template():
    if request.method == "POST":
        slug = (request.form.get("slug") or "").strip()
        name = (request.form.get("name") or "").strip()
        cascaron = (request.form.get("cascaron") or "").strip()

        # ⚠️ Guardar TAL CUAL
        content_html = request.form.get("content_html") or ""
        css = request.form.get("css", "")  # se guarda por compatibilidad, pero no se usa al render

        if not slug or not name or not cascaron:
            flash("Slug, Nombre y Casocaron son obligatorios.", "warning")
            return redirect(url_for("templates_admin.create_template", token=request.args.get("token")))

        execute("""
          INSERT INTO document_templates (slug,name,cascaron,content_html,css,version,is_active,updated_by,updated_at)
          VALUES (%s,%s,%s,%s,%s,1,TRUE,%s,%s)
        """, (slug, name, cascaron, content_html, css, "admin@local", datetime.utcnow()))
        flash("Plantilla creada.", "success")
        return redirect(url_for("templates_admin.list_templates", token=request.args.get("token")))

    return render_template("admin_templates_edit.html", tpl=None)

# ===== Editar (nueva versión) =====
@templates_bp.route("/<slug>/edit", methods=["GET","POST"])
def edit_template(slug):
    tpl = fetchone("""
      SELECT * FROM document_templates
      WHERE slug=%s AND is_active=TRUE
      ORDER BY version DESC LIMIT 1
    """, (slug,))
    if not tpl:
        abort(404)

    if request.method == "POST":
        # ⚠️ Guardar TAL CUAL, sin sanitizar ni separar CSS
        new_html = request.form.get("content_html") or ""
        new_css = request.form.get("css", "")

        # Crear nueva versión activa y desactivar la anterior
        execute("""
          WITH prev AS (
            SELECT id, slug, name, cascaron, version FROM document_templates
            WHERE id=%s
          )
          INSERT INTO document_templates (slug,name, cascaron, content_html,css,version,is_active,updated_by,updated_at)
          SELECT slug, name, cascaron, %s, %s, version+1, TRUE, %s, %s FROM prev;
        """, (tpl["id"], new_html, new_css, "admin@local", datetime.utcnow()))
        execute("UPDATE document_templates SET is_active=FALSE WHERE id=%s", (tpl["id"],))
        flash("Plantilla actualizada.", "success")
        return redirect(url_for("templates_admin.edit_template", slug=slug, token=request.args.get("token")))

    return render_template("admin_templates_edit.html", tpl=tpl)

# ===== Vista previa desde DB (render Jinja tal cual) =====
@templates_bp.route("/<slug>/preview")
def preview(slug):
    tpl = fetchone("""
      SELECT content_html, css FROM document_templates
      WHERE slug=%s AND is_active=TRUE
      ORDER BY version DESC LIMIT 1
    """, (slug,))
    if not tpl:
        abort(404)

    # Contexto de ejemplo mínimo (ajusta si quieres más datos)
    ctx = {
        "frame1": {"razon_social":"ACME S.A.", "numero_cliente":123,
                   "tipo_servicio":"DEPÓSITO ELECTRÓNICO","segmento":"PYME",
                   "numero_contrato":"-","tipo_tramite":"ALTA","tipo_contrato":"CPAE TRADICIONAL",
                   "tipo_cobro":"MENSUAL", "importe_maximo_dif":"-", "nombre_ejecutivo":"Prueba"},
        "usuarios": [], "cuentas": [], "unidades": [], "contactos": [],
        "firmantes": {"apoderado_legal":"Juan Pérez"}, "fecha_impresion":"01/01/2025 12:00",
        "imprimir_pdf": True
    }

    # ⚠️ Renderizar EXACTAMENTE lo guardado
    html_out = render_template_string(tpl["content_html"], **ctx)

    # Si quisieras inyectar CSS adicional, lo harías aquí (pero lo dejamos apagado)
    # custom_css = f"<style>{tpl['css']}</style>" if tpl.get("css") else ""
    # return Markup(custom_css + html_out)

    return Markup(html_out)

# ===== Exportar PDF desde DB (tal cual) =====
@templates_bp.route("/<slug>/export")
def export_pdf(slug):
    tpl = fetchone("""
      SELECT content_html, css FROM document_templates
      WHERE slug=%s AND is_active=TRUE
      ORDER BY version DESC LIMIT 1
    """, (slug,))
    if not tpl:
        abort(404)

    ctx = {
        "frame1": {"razon_social":"ACME S.A.","numero_cliente":123,"tipo_servicio":"DEPÓSITO ELECTRÓNICO"},
        "usuarios": [], "cuentas": [], "unidades": [], "contactos": [],
        "firmantes": {"apoderado_legal":"Juan Pérez"},
        "fecha_impresion":"01/01/2025 12:00"
    }

    # ⚠️ Render tal cual sin CSS extra
    html_rendered = render_template_string(tpl["content_html"], **ctx)

    pdf_io = io.BytesIO()
    HTML(string=html_rendered, base_url=request.url_root).write_pdf(pdf_io)

    response = make_response(pdf_io.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename={slug}.pdf"
    return response

# ===== Vista previa en vivo desde el editor (sin sanitizar, sin envolver) =====
@templates_bp.route("/preview_live", methods=["POST"])
def preview_live():
    data = request.get_json(silent=True) or {}
    content_html = data.get("content_html") or ""

    # Contexto de prueba (coincide con export/preview)
    ctx = {
        "frame1": {"razon_social": "ACME SA", "numero_cliente": "123456", "tipo_servicio": "DEPÓSITO ELECTRÓNICO"},
        "usuarios": [], "cuentas": [], "unidades": [], "contactos": [],
        "firmantes": {"apoderado_legal": "JUAN PÉREZ"},
        "fecha_impresion": "27/08/2025",
        "fecha_firma": "2025-08-27",
        "imprimir_pdf": True,
    }

    # ⚠️ NADA de sanitize/bleach. Render directo:
    html_out = render_template_string(content_html, **ctx)
    resp = make_response(html_out)
    resp.mimetype = "text/html"
    return resp

# ===== Versiones =====
@templates_bp.route("/<slug>/versions")
def versions(slug):
    items = fetchall("""
      SELECT id, version, is_active, updated_by, updated_at
      FROM document_templates
      WHERE slug=%s
      ORDER BY version DESC
    """, (slug,))
    return render_template("admin_templates_versions.html", slug=slug, items=items)

@templates_bp.route("/<slug>/activate/<int:tpl_id>", methods=["POST"])
def activate(slug, tpl_id):
    current = fetchone("""
        SELECT id FROM document_templates
        WHERE slug=%s AND is_active=TRUE
        ORDER BY version DESC LIMIT 1
    """, (slug,))
    if current:
        execute("UPDATE document_templates SET is_active=FALSE WHERE id=%s", (current["id"],))
    execute("UPDATE document_templates SET is_active=TRUE WHERE id=%s", (tpl_id,))
    flash("Versión activada.", "success")
    return redirect(url_for("templates_admin.versions", slug=slug))

@templates_bp.route("/<slug>/revert/<int:tpl_id>", methods=["POST"])
def revert(slug, tpl_id):
    tpl = fetchone("SELECT slug, name, cascaron, content_html, css, version FROM document_templates WHERE id=%s", (tpl_id,))
    if not tpl:
        abort(404)
    execute("""
      INSERT INTO document_templates (slug,name,cascaron,content_html,css,version,is_active,updated_by,updated_at)
      VALUES (%s,%s,%s,%s,%s,TRUE,%s,NOW())
    """, (tpl["slug"], tpl["name"], tpl["content_html"], tpl["css"], tpl["version"]+1, "admin@local"))
    # Desactiva la versión activa anterior
    prev = fetchone("""
        SELECT id FROM document_templates
        WHERE slug=%s AND is_active=TRUE
        ORDER BY version DESC LIMIT 1
    """, (slug,))
    if prev:
        execute("UPDATE document_templates SET is_active=FALSE WHERE id=%s", (prev["id"],))
    flash("Revertido en una nueva versión activa.", "success")
    return redirect(url_for("templates_admin.versions", slug=slug))
