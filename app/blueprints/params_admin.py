# app/blueprints/params_admin.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
import psycopg2.extras
from datetime import timedelta
from ..db_legacy import conectar

params_bp = Blueprint("params_admin", __name__, url_prefix="/admin/params")

# --- Helpers de acceso a parámetros ---
def get_param(key: str, default: str | None = None) -> str | None:
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT value FROM system_params WHERE key=%s", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

def set_param(key: str, value: str, updated_by: str | None = None):
    with conectar() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO system_params(key, value, updated_by, updated_at)
            VALUES (%s,%s,%s,now())
            ON CONFLICT (key) DO UPDATE
              SET value=EXCLUDED.value,
                  updated_by=EXCLUDED.updated_by,
                  updated_at=EXCLUDED.updated_at
        """, (key, value, updated_by or "admin"))
        conn.commit()

# --- Guard de administrador muy simple (usa tu lógica real si ya la tienes) ---
@params_bp.before_request
def _admin_only():
    if session.get("role") != "admin":
        flash("Acceso restringido a administradores.", "warning")
        return redirect(url_for("auth_admin.login"))

# --- Pantalla de edición del timeout ---
@params_bp.route("/", methods=["GET", "POST"])
def editar_timeout():
    # KEY única para este parámetro
    KEY = "session_timeout_minutes"

    if request.method == "POST":
        raw = (request.form.get("minutes") or "").strip()
        try:
            minutes = int(raw)
            if minutes < 1 or minutes > 720:
                raise ValueError()
        except ValueError:
            flash("Ingresa un número de minutos válido (1 a 720).", "danger")
            return redirect(url_for("params_admin.editar_timeout"))

        set_param(KEY, str(minutes), updated_by=session.get("username") or "admin")
        flash("Parámetro actualizado.", "success")
        return redirect(url_for("params_admin.editar_timeout"))

    # GET
    current_val = get_param(KEY, default="15")
    return render_template("admin_params_timeout.html", current_minutes=current_val)
