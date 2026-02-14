# app/blueprints/catalogos.py
# ABM de catálogos simples (CPAE, ETV, Estados, Municipios) con una estructura configurable.

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..db_legacy import fetchall, fetchone, execute

catalogos_bp = Blueprint("catalogos", __name__)

CATALOGOS = {
    "cpae": {"tabla": "catalogo_cpae", "campo": "descripcion"},
    "etv": {"tabla": "catalogo_etv", "campo": "descripcion"},
    "estados": {"tabla": "catalogo_estados", "campo": "nombre"},
    "municipios": {"tabla": "catalogo_municipios", "campo": "nombre"},
}

# def guard():
#     # Guard simple sin importar auth_admin (evita ciclos)
#     if session.get("role") != "admin":
#         flash("Debes iniciar sesión de administrador.", "warning")
#         return redirect(url_for("auth_admin.login", next=request.path))
    
    # --- Guard de administrador muy simple (usa tu lógica real si ya la tienes) ---
@catalogos_bp.before_request
def _admin_only():
    if session.get("role") != "admin":
        flash("Acceso restringido a administradores.", "warning")
        return redirect(url_for("auth_admin.login"))
    
@catalogos_bp.route("/admin/catalogos", methods=["GET"])
def ver_catalogos():
    return render_template("catalogos.html", catalogos=CATALOGOS.keys())

@catalogos_bp.route("/admin/catalogo/<catalogo>", methods=["GET", "POST"])
def administrar_catalogo(catalogo):
    if catalogo not in CATALOGOS:
        flash("Catálogo no válido.", "danger")
        return redirect(url_for("catalogos.ver_catalogos"))

    tabla = CATALOGOS[catalogo]["tabla"]
    campo = CATALOGOS[catalogo]["campo"]

    if request.method == "POST":
        nuevo = request.form.get("nuevo", "").strip()
        if nuevo:
            execute(f"INSERT INTO {tabla} ({campo}) VALUES (%s)", (nuevo,))
            flash("Elemento agregado correctamente.", "success")
        else:
            flash("El valor no puede estar vacío.", "danger")
        return redirect(url_for("catalogos.administrar_catalogo", catalogo=catalogo))

    items = fetchall(f"SELECT id, {campo} AS valor FROM {tabla} ORDER BY id")
    return render_template("administrar_catalogo.html", catalogo=catalogo, items=items, campo=campo)

@catalogos_bp.route("/admin/catalogo/<catalogo>/editar/<int:item_id>", methods=["GET", "POST"])
def editar_catalogo(catalogo, item_id):
    if catalogo not in CATALOGOS:
        flash("Catálogo no válido.", "danger")
        return redirect(url_for("catalogos.ver_catalogos"))

    tabla = CATALOGOS[catalogo]["tabla"]
    campo = CATALOGOS[catalogo]["campo"]

    if request.method == "POST":
        nuevo_valor = request.form.get("nuevo_valor", "").strip()
        if nuevo_valor:
            execute(f"UPDATE {tabla} SET {campo}=%s WHERE id=%s", (nuevo_valor, item_id))
            flash("Elemento editado correctamente.", "success")
        else:
            flash("El valor no puede estar vacío.", "danger")
        return redirect(url_for("catalogos.administrar_catalogo", catalogo=catalogo))

    row = fetchone(f"SELECT {campo} AS valor FROM {tabla} WHERE id=%s", (item_id,))
    if row is None:
        flash("Elemento no encontrado.", "danger")
        return redirect(url_for("catalogos.administrar_catalogo", catalogo=catalogo))
    return render_template("editar_catalogo.html", catalogo=catalogo, item_id=item_id, valor_actual=row["valor"])

@catalogos_bp.route("/admin/catalogo/<catalogo>/eliminar/<int:item_id>")
def eliminar_catalogo(catalogo, item_id):
    if catalogo not in CATALOGOS:
        flash("Catálogo no válido.", "danger")
        return redirect(url_for("catalogos.ver_catalogos"))

    tabla = CATALOGOS[catalogo]["tabla"]
    execute(f"DELETE FROM {tabla} WHERE id=%s", (item_id,))
    flash("Elemento eliminado.", "warning")
    return redirect(url_for("catalogos.administrar_catalogo", catalogo=catalogo))
