# app/blueprints/auth_admin.py
from flask import Blueprint, render_template, redirect, url_for, session, flash, request
from werkzeug.security import check_password_hash
import psycopg2.extras
from ..db_legacy import conectar

auth_bp = Blueprint("auth_admin", __name__, url_prefix="/admin")

def get_user(username: str):
    """Devuelve un dict con id, username, fullname, password_hash, is_active, role
       o None si no existe/está inactivo."""
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, username, fullname, password_hash, is_active, role
            FROM admin_users
            WHERE username = %s AND is_active = TRUE
            """,
            (username,),
        )
        return cur.fetchone()

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()
        fullname = (request.form.get("fullname") or "").strip()

        user = get_user(username)  # ← buscamos por username

        if user and check_password_hash(user["password_hash"], password):
            # Sesión limpia
            session.clear()
            session.permanent = True
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user.get("role", "user")  # 'admin' o 'user'
            session["fullname"] = user.get("fullname")  # ← correcto


            # Soportar ?next= tanto en GET como POST
            next_url = request.values.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)

            # Redirección por rol
            if session["role"] == "admin":
                return redirect(url_for("admin_portal.dashboard"))
            else:
                return redirect(url_for("core.inicio_productos"))

        flash("Credenciales inválidas.", "danger")

    # GET o POST fallido → mostrar login
    return render_template("admin_login.html")

@auth_bp.route("/logout")
def logout():
    # Limpia la sesión
    session.clear()
    motivo = request.args.get("motivo", "manual")
    if motivo == "inactividad":
        flash("Tu sesión se cerró por inactividad.", "warning")
    else:
        flash("Sesión cerrada.", "info")
    return redirect(url_for("auth_admin.login"))

def admin_required() -> bool:
    return session.get("role") == "admin"

def usuario_required() -> bool:
    return session.get("role") == "user"


@auth_bp.route("/ping")
def ping():
    # No hace nada, pero renueva la cookie de sesión al ser llamado
    return ("", 204)
