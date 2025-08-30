# app/blueprints/core.py

from flask import Blueprint, render_template, redirect, url_for, session

core_bp = Blueprint("core", __name__)

@core_bp.route("/productos")
def inicio_productos():
    return render_template("inicio_productos.html")

@core_bp.route("/frame1-nuevo")
def frame1_nuevo():
    # Limpieza selectiva (evita session.clear())
    for k in list(session.keys()):
        if k.startswith("frame") or k in {"usuarios", "cuentas", "unidades", "contactos"}:
            session.pop(k, None)
    return redirect(url_for("frames.frame1"))
