from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Role
from app.extensions import db
from app.auth.decorators import permiso_required


roles_admin_bp = Blueprint(
    "roles_admin",
    __name__,
    url_prefix="/admin/roles"
)


@roles_admin_bp.route("/", methods=["GET", "POST"])
@permiso_required("manage_roles")
def index():

    if request.method == "POST":

        code = request.form.get("code")
        descripcion = request.form.get("descripcion")

        nuevo = Role(code=code, descripcion=descripcion)
        db.session.add(nuevo)
        db.session.commit()

        return redirect(url_for("roles_admin.index"))

    roles = Role.query.order_by(Role.code).all()

    return render_template(
        "admin_roles.html",
        roles=roles
    )


@roles_admin_bp.route("/<int:role_id>/delete", methods=["POST"])
@permiso_required("manage_roles")
def delete(role_id):

    role = Role.query.get_or_404(role_id)
    db.session.delete(role)
    db.session.commit()

    return redirect(url_for("roles_admin.index"))
