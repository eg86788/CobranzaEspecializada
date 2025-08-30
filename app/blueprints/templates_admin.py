from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask import current_app, session
from markupsafe import Markup
from datetime import datetime
import bleach
# intenta importar CSSSanitizer si existe en tu versión
try:
    from bleach.css_sanitizer import CSSSanitizer
except Exception:
    CSSSanitizer = None  # versiones viejas de bleach no lo tienen
import psycopg2.extras
from .auth_admin import admin_required
from flask import abort
from ..db_legacy import conectar  # ajusta el import a tu helper real

from flask import render_template_string, make_response, request
from weasyprint import HTML
import io
import html  # para decodificar entidades

templates_bp = Blueprint("templates_admin", __name__, url_prefix="/admin/templates")

from ..auth.decorators import permiso_required

@templates_bp.before_request
@permiso_required("manage_templates")
def _guard_templates():
    pass


# ---- Sanitizado HTML/CSS para plantillas (compatible con varias versiones de bleach) ----
import bleach


# intenta importar CSSSanitizer si existe en tu versión
try:
    from bleach.css_sanitizer import CSSSanitizer
except Exception:
    CSSSanitizer = None  # versiones viejas de bleach no lo tienen

# CSS base con la fuente Banamex
BANAMEX_CSS = """
<style>
@font-face {
  font-family: 'Banamex';
  src: url('/static/fonts/BanamexDisplay-Regular.ttf') format('truetype');
  font-weight: 400;
  font-style: normal;
}
@font-face {
  font-family: 'Banamex';
  src: url('/static/fonts/BanamexDisplay-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
}
body, p, td, th, div, span {
  font-family: 'Banamex', Arial, sans-serif;
  font-size: 11px;
}
strong, b {
  font-weight: 700;
}
table {
  border-collapse: collapse;
}
th, td {
  border: 1px solid #000;
}
</style>
"""

ALLOWED_TAGS = {
    "p","h1","h2","h3","h4","h5","h6",
    "strong","b","em","i","u","s","span","div","br","hr",
    "ul","ol","li","blockquote","pre","code","a","img",
    "table","thead","tbody","tfoot","tr","th","td","caption","colgroup","col"
}


ALLOWED_ATTRS = {
    "*": ["class","style"],
    "a": ["href","target","rel"],
    "img": ["src","alt","width","height"],
    "table": ["border","cellpadding","cellspacing","width","height","style","class"],
    "tr": ["style","class","align","valign"],
    "th": ["style","class","align","valign","colspan","rowspan","width","height"],
    "td": ["style","class","align","valign","colspan","rowspan","width","height"],
    "col": ["span","width","style","class"],
    "colgroup": ["span","width","style","class"],
    "caption": ["style","class"],
}

# Lista blanca de propiedades CSS que necesitamos (bordes incluidos)
_ALLOWED_CSS_PROPS = [
    # cajas / tipografía
    "margin","margin-top","margin-right","margin-bottom","margin-left",
    "padding","padding-top","padding-right","padding-bottom","padding-left",
    "width","height","max-width","min-width","max-height","min-height",
    "display","vertical-align","text-align","white-space","line-height",
    "font","font-family","font-size","font-style","font-weight",
    "color","background","background-color",
    # BORDES (¡clave para tus tablas!)
    "border","border-top","border-right","border-bottom","border-left",
    "border-color","border-style","border-width",
    "border-collapse","border-spacing",
    # tablas
    "caption-side","empty-cells",
    # weasyprint/impresión
    "page-break-before","page-break-after","page-break-inside"
]

# crea un css_sanitizer compatible según la firma disponible
CSS_ALLOWED = None
if CSSSanitizer:
    # algunas versiones usan allowed_css_properties / allowed_css_protocols
    try:
        CSS_ALLOWED = CSSSanitizer(
            allowed_css_properties=_ALLOWED_CSS_PROPS,
            allowed_css_protocols=["data","http","https"],
        )
    except TypeError:
        # otras usan allowed_protocols
        try:
            CSS_ALLOWED = CSSSanitizer(
                allowed_css_properties=_ALLOWED_CSS_PROPS,
                allowed_protocols=["data","http","https"],
            )
        except TypeError:
            # último recurso
            CSS_ALLOWED = CSSSanitizer()

def sanitize_html(html: str) -> str:
    kwargs = dict(
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRS,
        strip=True,
    )
    if CSS_ALLOWED:
        kwargs["css_sanitizer"] = CSS_ALLOWED
    return bleach.clean(html or "", **kwargs)


def fetchone(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p); return cur.fetchone()

def fetchall(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p); return cur.fetchall()

def execute(q, p=()):
    with conectar() as conn, conn.cursor() as cur:
        cur.execute(q, p); conn.commit()

def require_admin():
    # hazlo decente luego; por ahora protege con token simple
    token = request.args.get("token")
    return token and token == current_app.config.get("TEMPLATES_ADMIN_TOKEN", "letmein")

@templates_bp.before_request
def _guard():
    if not admin_required():
        return redirect(url_for("auth_admin.login"))

@templates_bp.route("/")
def list_templates():
    items = fetchall("""
      SELECT DISTINCT ON (slug) id, slug, name, version, is_active, updated_at
      FROM document_templates
      ORDER BY slug, version DESC
    """)
    return render_template("admin_templates_list.html", items=items)

@templates_bp.route("/new", methods=["GET","POST"])
def create_template():
    if request.method == "POST":
        slug = request.form["slug"].strip()
        name = request.form["name"].strip()
        content_html = sanitize_html(request.form["content_html"])
        css = request.form.get("css","")
        execute("""
          INSERT INTO document_templates (slug,name,content_html,css,version,is_active,updated_by,updated_at)
          VALUES (%s,%s,%s,%s,1,TRUE,%s,%s)
        """, (slug, name, content_html, css, "admin@local", datetime.utcnow()))
        flash("Plantilla creada.", "success")
        return redirect(url_for("templates_admin.list_templates", token=request.args.get("token")))
    return render_template("admin_templates_edit.html", tpl=None)

@templates_bp.route("/<slug>/edit", methods=["GET","POST"])
def edit_template(slug):
    tpl = fetchone("""
      SELECT * FROM document_templates
      WHERE slug=%s AND is_active=TRUE
      ORDER BY version DESC LIMIT 1
    """, (slug,))
    if not tpl: abort(404)

    if request.method == "POST":
        new_html = sanitize_html(request.form["content_html"])
        new_css = request.form.get("css","")
        # crear nueva versión y desactivar la anterior
        execute("""
          WITH prev AS (
            SELECT id, slug, name, version FROM document_templates
            WHERE id=%s
          )
          INSERT INTO document_templates (slug,name,content_html,css,version,is_active,updated_by,updated_at)
          SELECT slug, name, %s, %s, version+1, TRUE, %s, %s FROM prev;
        """, (tpl["id"], new_html, new_css, "admin@local", datetime.utcnow()))
        execute("UPDATE document_templates SET is_active=FALSE WHERE id=%s", (tpl["id"],))
        flash("Plantilla actualizada.", "success")
        return redirect(url_for("templates_admin.edit_template", slug=slug, token=request.args.get("token")))

    return render_template("admin_templates_edit.html", tpl=tpl)

# app/blueprints/templates_admin.py
from markupsafe import Markup
from flask import render_template_string
import html  # ← nuevo import

@templates_bp.route("/<slug>/preview")
def preview(slug):
    tpl = fetchone("""
      SELECT content_html, css FROM document_templates
      WHERE slug=%s AND is_active=TRUE
      ORDER BY version DESC LIMIT 1
    """, (slug,))
    if not tpl: abort(404)

    ctx = {
        "frame1": {"razon_social":"ACME S.A.", "numero_cliente":123,
                   "tipo_servicio":"DEPÓSITO ELECTRÓNICO","segmento":"PYME",
                   "numero_contrato":"-","tipo_tramite":"ALTA","tipo_contrato":"CPAE TRADICIONAL",
                   "tipo_cobro":"MENSUAL", "importe_maximo_dif":"-", "nombre_ejecutivo":"Prueba"},
        "usuarios": [], "cuentas": [], "unidades": [], "contactos": [],
        "firmantes": {"apoderado_legal":"Juan Pérez"}, "fecha_impresion":"01/01/2025 12:00",
        "imprimir_pdf": True
    }

    import html
    source = html.unescape(tpl["content_html"])
    html_out = render_template_string(source, **ctx)

    # 👇 CSS base (negritas y bordes) SIEMPRE presente en la vista previa
    base_css = """
    <style>
      b, strong { font-weight: 700 !important; }
      i, em { font-style: italic !important; }
      table { border-collapse: collapse; }
      th, td { border: 1px solid #000; }
    </style>
    """

    # CSS de la plantilla (si existe)
    custom_css = f"<style>{tpl['css']}</style>" if tpl["css"] else ""

    return Markup(base_css + custom_css + html_out)


from flask import make_response
from weasyprint import HTML, CSS
import io

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

    from flask import render_template_string
    html_rendered = render_template_string(tpl["content_html"], **ctx)

    # 👇 CSS base + CSS de la plantilla
    base_css = """
    <style>
      b, strong { font-weight: 700 !important; }
      i, em { font-style: italic !important; }
      table { border-collapse: collapse; }
      th, td { border: 1px solid #000; }
    </style>
    """
    custom_css = f"<style>{tpl['css']}</style>" if tpl["css"] else ""

    html_rendered = base_css + custom_css + html_rendered

    import io
    pdf_io = io.BytesIO()
    HTML(string=html_rendered, base_url=request.url_root).write_pdf(pdf_io)

    from flask import make_response
    response = make_response(pdf_io.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"inline; filename={slug}.pdf"
    return response

     
@templates_bp.route("/preview_live", methods=["POST"])
def preview_live():
    from flask import render_template_string, jsonify
    tpl = {
        "content_html": request.json.get("content_html", ""),
        "css": request.json.get("css", "")
    }
    ctx = {
        "frame1": {"razon_social": "ACME SA", "numero_cliente": "123456", "tipo_servicio": "DEPÓSITO ELECTRÓNICO"},
        "usuarios": [], "cuentas": [], "unidades": [], "contactos": [],
        "firmantes": {"apoderado_legal": "JUAN PÉREZ"}, "fecha_impresion": "27/08/2025",
        "fecha_firma": "2025-08-27"
    }
    html = render_template_string(tpl["content_html"], **ctx)
    if tpl["css"]:
        html = f"<style>{tpl['css']}</style>\n{html}"
    return html


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
    current = fetchone("SELECT id FROM document_templates WHERE slug=%s AND is_active=TRUE ORDER BY version DESC LIMIT 1", (slug,))
    execute("UPDATE document_templates SET is_active=FALSE WHERE id=%s", (current["id"],))
    execute("UPDATE document_templates SET is_active=TRUE WHERE id=%s", (tpl_id,))
    flash("Versión activada.", "success")
    return redirect(url_for("templates_admin.versions", slug=slug))

@templates_bp.route("/<slug>/revert/<int:tpl_id>", methods=["POST"])
def revert(slug, tpl_id):
    tpl = fetchone("SELECT slug, name, content_html, css, version FROM document_templates WHERE id=%s", (tpl_id,))
    execute("""
      INSERT INTO document_templates (slug,name,content_html,css,version,is_active,updated_by,updated_at)
      VALUES (%s,%s,%s,%s,%s,TRUE,%s,NOW())
    """, (tpl["slug"], tpl["name"], tpl["content_html"], tpl["css"], tpl["version"]+1, "admin@local"))
    # desactiva la anterior activa
    prev = fetchone("SELECT id FROM document_templates WHERE slug=%s AND is_active=TRUE ORDER BY version DESC LIMIT 1", (slug,))
    if prev: execute("UPDATE document_templates SET is_active=FALSE WHERE id=%s", (prev["id"],))
    flash("Revertido en una nueva versión activa.", "success")
    return redirect(url_for("templates_admin.versions", slug=slug))
