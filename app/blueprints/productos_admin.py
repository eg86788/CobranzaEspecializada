from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.models import Producto
from app.extensions import db

productos_admin_bp = Blueprint(
    "productos_admin",
    __name__,
    url_prefix="/admin/productos"
)


@productos_admin_bp.route("/")
def lista():
    productos = Producto.query.order_by(Producto.nombre.asc()).all()
    return render_template("admin/productos/lista.html", productos=productos)


@productos_admin_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    if request.method == "POST":
        code = request.form.get("code", "").strip().lower()
        nombre = request.form.get("nombre", "").strip()
        descripcion = request.form.get("descripcion", "").strip()

        if not code or not nombre:
            flash("Code y nombre son obligatorios.", "warning")
            return redirect(url_for("productos_admin.nuevo"))

        if Producto.query.filter_by(code=code).first():
            flash("El code ya existe.", "danger")
            return redirect(url_for("productos_admin.nuevo"))

        producto = Producto(
            code=code,
            nombre=nombre,
            descripcion=descripcion
        )

        db.session.add(producto)
        db.session.commit()

        flash("Producto creado correctamente.", "success")
        return redirect(url_for("productos_admin.lista"))

    return render_template("admin/productos/nuevo.html")


@productos_admin_bp.route("/<int:id>/toggle")
def toggle(id):
    producto = Producto.query.get_or_404(id)
    producto.activo = not producto.activo
    db.session.commit()

    flash("Estado actualizado.", "info")
    return redirect(url_for("productos_admin.lista"))
