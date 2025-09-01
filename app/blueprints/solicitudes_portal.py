from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app
import os

# Usa utilidades de tu conector legacy
try:
    from ..db_legacy import fetchall, fetchone
except Exception:
    from app.db_legacy import fetchall, fetchone  # pragma: no cover

# Este blueprint mantiene el nombre que esperas en app/__init__.py
sol_portal = Blueprint("solicitudes_portal", __name__, url_prefix="/solicitudes")

# Mínimo de firmantes requeridos (ajustable por ENV)
REQUIRED_FIRMANTES = int(os.getenv("FIRMANTES_MIN", "3"))


def _login_url():
    return url_for("admin.login") if "admin.login" in current_app.view_functions else "/admin/login"


def _resolve_user_id_from_username(username: str):
    if not username:
        return None
    sql = """
        SELECT id
        FROM admin_users
        WHERE (username = %s OR email = %s)
        ORDER BY id ASC
        LIMIT 1
    """
    row = fetchone(sql, (username, username))
    try:
        return int(row["id"]) if row and row.get("id") is not None else None
    except Exception:
        return None


def _table_exists(schema: str, table: str) -> bool:
    sql = """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        LIMIT 1
    """
    row = fetchone(sql, (schema, table))
    return bool(row)


def _firmantes_count_by_solicitud(table_name: str, solicitud_ids):
    if not solicitud_ids:
        return {}
    placeholders = ", ".join(["%s"] * len(solicitud_ids))
    sql = f"""
        SELECT solicitud_id, COUNT(*) AS cnt
        FROM {table_name}
        WHERE solicitud_id IN ({placeholders})
        GROUP BY solicitud_id
    """
    rows = fetchall(sql, tuple(solicitud_ids)) or []
    return {int(r["solicitud_id"]): int(r["cnt"]) for r in rows if r.get("solicitud_id") is not None}


@sol_portal.route("/lista", methods=["GET"])
def lista():
    user_id = session.get("user_id")
    username = session.get("username") or session.get("user_name") or session.get("login")

    if not user_id and not username:
        return redirect(_login_url())

    if not user_id and username:
        resolved = _resolve_user_id_from_username(username)
        if resolved is None:
            flash("No fue posible resolver el usuario actual. Inicia sesión de nuevo.", "warning")
            session.pop("user_id", None)
            return redirect(_login_url())
        session["user_id"] = resolved
        user_id = resolved

    try:
        user_id = int(user_id)
    except Exception:
        flash("Sesión inconsistente: identificador de usuario inválido.", "danger")
        session.pop("user_id", None)
        return redirect(_login_url())

    # Solicitudes del usuario (solo columnas que existen)
    sql = """
        SELECT
            s.id,
            s.updated_at,
            s.numero_cliente,
            s.numero_contrato,
            s.razon_social,
            s.tipo_tramite
        FROM solicitudes AS s
        WHERE s.created_by = %s
        ORDER BY s.updated_at DESC NULLS LAST, s.id DESC
    """
    solicitudes = fetchall(sql, (user_id,)) or []
    ids = [int(s["id"]) for s in solicitudes if s.get("id") is not None]

    # Tabla de firmantes (opcional)
    firmantes_table = None
    if _table_exists("public", "firmantes"):
        firmantes_table = "firmantes"
    elif _table_exists("public", "solicitudes_firmantes"):
        firmantes_table = "solicitudes_firmantes"

    counts = {}
    if firmantes_table and ids:
        counts = _firmantes_count_by_solicitud(firmantes_table, ids)

    for s in solicitudes:
        sid = int(s["id"])
        if firmantes_table:
            cnt = counts.get(sid, 0)
            s["firmantes_completos"] = (cnt >= REQUIRED_FIRMANTES)
            s["firmantes_count"] = cnt
        else:
            s["firmantes_completos"] = True
            s["firmantes_count"] = None

    # 🔑 Fallback de templates:
    #  - primero intenta templates/solicitudes/lista.html
    #  - luego templates/lista.html
    return render_template(
        ["solicitudes/lista.html", "lista.html"],
        solicitudes=solicitudes
    )
