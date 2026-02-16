from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Producto, RoleProductAccess, Role
from app.extensions import db
from app.auth.decorators import permiso_required


roles_product_admin_bp = Blueprint(
    "roles_product_admin",
    __name__,
    url_prefix="/admin/roles-productos"
)


@roles_product_admin_bp.route("/", methods=["GET", "POST"])
@permiso_required("manage_roles")
def index():

    # 🔹 Roles dinámicos desde BD
    roles = Role.query.filter_by(activo=True).order_by(Role.code).all()

    if not roles:
        flash("No existen roles configurados.", "warning")
        return render_template(
            "admin_roles_product_access.html",
            roles=[],
            selected_role=None,
            productos=[],
            accesos={}
        )

    selected_role = request.args.get("role") or request.form.get("role") or roles[0].code

    productos = Producto.query.order_by(Producto.nombre).all()

    if request.method == "POST":

        # eliminar configuración previa
        RoleProductAccess.query.filter_by(role=selected_role).delete()

        for producto in productos:
            habilitado = request.form.get(f"producto_{producto.code}") == "on"

            db.session.add(RoleProductAccess(
                role=selected_role,
                producto_code=producto.code,
                habilitado=habilitado
            ))

        db.session.commit()
        flash("Permisos actualizados correctamente.", "success")

        return redirect(url_for("roles_product_admin.index", role=selected_role))

    # obtener accesos actuales
    accesos = RoleProductAccess.query.filter_by(role=selected_role).all()
    accesos_dict = {a.producto_code: a.habilitado for a in accesos}

    return render_template(
        "admin_roles_product_access.html",
        roles=roles,
        selected_role=selected_role,
        productos=productos,
        accesos=accesos_dict
    )
