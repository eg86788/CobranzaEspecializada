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
from flask import request, redirect, url_for
from app.models import Producto, RoleProductAccess
from app.extensions import db


@admin_bp.route("/catalogos/asignacion-productos", methods=["GET", "POST"])
@permiso_required("manage_catalogs")
def admin_asignacion_productos():

    if request.method == "POST":

        role = request.form.get("role")

        # Desactivar todo para ese rol
        RoleProductAccess.query.filter_by(role=role).update(
            {"habilitado": False}
        )

        productos = request.form.getlist("productos")

        for code in productos:
            acceso = RoleProductAccess.query.filter_by(
                role=role,
                producto_code=code
            ).first()

            if acceso:
                acceso.habilitado = True
            else:
                nuevo = RoleProductAccess(
                    role=role,
                    producto_code=code,
                    habilitado=True
                )
                db.session.add(nuevo)

        db.session.commit()

        return redirect(url_for("admin.admin_asignacion_productos"))

    roles = ["admin", "user"]
    productos = Producto.query.filter_by(activo=True).all()
    accesos = RoleProductAccess.query.all()

    return render_template(
        "admin_asignacion_productos.html",
        roles=roles,
        productos=productos,
        accesos=accesos
    )
