from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app
import os

# Usa utilidades de tu conector legacy
try:
    from ..db_legacy import fetchall, fetchone
except Exception:
    from app.db_legacy import fetchall, fetchone  # pragma: no cover

# Nombre del blueprint que ya espera tu app/__init__.py
sol_portal = Blueprint("solicitudes_portal", __name__, url_prefix="/solicitudes")

# Mínimo de firmantes requeridos para habilitar exportación (editable por ENV)
REQUIRED_FIRMANTES = int(os.getenv("FIRMANTES_MIN", "3"))


def _login_url():
    """URL de login según exista el endpoint o no."""
    return url_for("admin.login") if "admin.login" in current_app.view_functions else "/admin/login"


def _resolve_user_id_from_username(username: str):
    """Busca el ID del usuario por username o email. Retorna int o None."""
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
    """Verifica existencia de tabla en information_schema."""
    sql = """
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = %s AND table_name = %s
        LIMIT 1
    """
    row = fetchone(sql, (schema, table))
    return bool(row)


def _firmantes_count_by_solicitud(table_name: str, solicitud_ids):
    """
    Devuelve dict { solicitud_id: count } leyendo de `table_name`.
    Construye placeholders dinámicos para IN (...).
    """
    if not solicitud_ids:
        return {}

    # Placeholders (%s, %s, ...)
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
    """
    Lista de solicitudes del usuario autenticado.
    - solicitudes.created_by es INTEGER (usamos user_id int).
    - Usamos updated_at para fecha de referencia.
    - Calculamos firmantes_completos si existe la tabla de firmantes.
    """
    user_id = session.get("user_id")
    username = session.get("username") or session.get("user_name") or session.get("login")

    # Si no hay user_id ni username, no hay sesión válida
    if not user_id and not username:
        return redirect(_login_url())

    # Resolver user_id cuando solo tenemos username
    if not user_id and username:
        resolved = _resolve_user_id_from_username(username)
        if resolved is None:
            flash("No fue posible resolver el usuario actual. Inicia sesión de nuevo.", "warning")
            session.pop("user_id", None)
            return redirect(_login_url())
        session["user_id"] = resolved
        user_id = resolved

    # Asegurar entero
    try:
        user_id = int(user_id)
    except Exception:
        flash("Sesión inconsistente: identificador de usuario inválido.", "danger")
        session.pop("user_id", None)
        return redirect(_login_url())

    # 1) Traer solicitudes (sin campos inexistentes)
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

    # 2) Preparar mapa por id
    ids = [int(s["id"]) for s in solicitudes if s.get("id") is not None]

    # 3) Determinar tabla de firmantes
    firmantes_table = None
    # Intento estándar: public.firmantes
    if _table_exists("public", "firmantes"):
        firmantes_table = "firmantes"
    # Alternativa común: public.solicitudes_firmantes
    elif _table_exists("public", "solicitudes_firmantes"):
        firmantes_table = "solicitudes_firmantes"

    # 4) Si existe alguna tabla de firmantes, contamos por solicitud
    counts = {}
    if firmantes_table and ids:
        counts = _firmantes_count_by_solicitud(firmantes_table, ids)

    # 5) Marcar bandera firmantes_completos (default True si no hay tabla → no bloquea exportación)
    for s in solicitudes:
        sid = int(s["id"])
        if firmantes_table:
            cnt = counts.get(sid, 0)
            s["firmantes_completos"] = (cnt >= REQUIRED_FIRMANTES)
            s["firmantes_count"] = cnt
        else:
            s["firmantes_completos"] = True
            s["firmantes_count"] = None

    return render_template("solicitudes/lista.html", solicitudes=solicitudes)
