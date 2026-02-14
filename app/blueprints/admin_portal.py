# app/blueprints/admin_portal.py
from flask import Blueprint, render_template, redirect, url_for, flash, request, session

admin_portal = Blueprint("admin_portal", __name__, url_prefix="/admin")

# @admin_portal.before_request
# def guard():
#     # Guard simple sin importar auth_admin (evita ciclos)
#     if session.get("role") != "admin":
#         flash("Debes iniciar sesión de administrador.", "warning")
#         return redirect(url_for("auth_admin.login", next=request.path))
    

    # --- Guard de administrador muy simple (usa tu lógica real si ya la tienes) ---
@admin_portal.before_request
def _admin_only():
    if session.get("role") != "admin":
        flash("Acceso restringido a administradores.", "warning")
        return redirect(url_for("auth_admin.login"))    

    

@admin_portal.route("/panel")
def dashboard():
    return render_template("admin_panel.html")
