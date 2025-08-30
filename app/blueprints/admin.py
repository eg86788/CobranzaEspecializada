from flask import Blueprint, render_template
from ..auth.decorators import role_required, permiso_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/")
@role_required("admin")
def inicio():
    return render_template("admin_dashboard.html")

# Ejemplos de rutas protegidas por permiso granular:
@admin_bp.route("/catalogos")
@permiso_required("manage_catalogs")
def admin_catalogos():
    # renderiza tu UI de catálogos
    return render_template("admin_catalogos.html")

@admin_bp.route("/templates")
@permiso_required("manage_templates")
def admin_templates():
    return render_template("admin_templates_hub.html")

@admin_bp.route("/adhesiones")
@permiso_required("manage_adhesiones")
def admin_adhesiones():
    return render_template("admin_adhesiones.html")
