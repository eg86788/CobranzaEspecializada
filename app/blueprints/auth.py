from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from ..db_legacy import fetchone
from werkzeug.security import check_password_hash
from urllib.parse import urlparse

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = fetchone("SELECT id, email, password_hash, role, nombre FROM admin_users WHERE email=%s", (email,))
        if not user or not check_password_hash(user["password_hash"], password):
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for("auth.login"))

        # set session
        session["user_id"] = user["id"]
        session["user_email"] = user["email"]
        session["user_name"] = user.get("nombre") or user["email"]
        session["role"] = user["role"]

        # redirección por rol (o respeta ?next=)
        next_url = request.args.get("next")
        if next_url and urlparse(next_url).netloc == "":
            return redirect(next_url)

        if user["role"] == "admin":
            return redirect(url_for("admin.inicio"))  # dashboard admin
        else:
            return redirect(url_for("core.inicio_productos"))

    return render_template("auth_login.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
