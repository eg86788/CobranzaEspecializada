from flask import Blueprint, render_template, request, redirect, url_for
from ..auth.decorators import role_required, permiso_required
from app.models import Producto, RoleProductAccess, TarifaComisionProducto
from app.extensions import db

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


# ==============================
# TARIFAS DE COMISIÓN POR PRODUCTO
# ==============================

@admin_bp.route("/tarifas-comision")
@permiso_required("manage_catalogs")
def admin_tarifas_comision():
    tarifas = TarifaComisionProducto.query.order_by(
        TarifaComisionProducto.id.desc()
    ).all()

    return render_template(
        "admin_tarifas_comision.html",
        tarifas=tarifas
    )


@admin_bp.route("/tarifas-comision/nueva", methods=["GET"])
@permiso_required("manage_catalogs")
def nueva_tarifa_comision():
    productos = Producto.query.filter_by(activo=True).all()
    return render_template(
        "admin_tarifa_comision_form.html",
        productos=productos,
        tarifa=None
    )


@admin_bp.route("/tarifas-comision/guardar", methods=["POST"])
@permiso_required("manage_catalogs")
def guardar_tarifa_comision():

    id = request.form.get("id")

    if id:
        tarifa = TarifaComisionProducto.query.get(id)
    else:
        tarifa = TarifaComisionProducto()

    tarifa.producto_id = request.form.get("producto_id")
    tarifa.tipo_comision = request.form.get("tipo_comision")
    tarifa.valor = request.form.get("valor")
    tarifa.moneda = request.form.get("moneda")
    tarifa.activo = True if request.form.get("activo") else False

    db.session.add(tarifa)
    db.session.commit()

    return redirect(url_for("admin.admin_tarifas_comision"))


@admin_bp.route("/tarifas-comision/editar/<int:id>")
@permiso_required("manage_catalogs")
def editar_tarifa_comision(id):
    tarifa = TarifaComisionProducto.query.get_or_404(id)
    productos = Producto.query.filter_by(activo=True).all()

    return render_template(
        "admin_tarifa_comision_form.html",
        tarifa=tarifa,
        productos=productos
    )


@admin_bp.route("/tarifas-comision/baja/<int:id>")
@permiso_required("manage_catalogs")
def baja_tarifa_comision(id):
    tarifa = TarifaComisionProducto.query.get_or_404(id)
    tarifa.activo = False
    db.session.commit()

    return redirect(url_for("admin.admin_tarifas_comision"))
