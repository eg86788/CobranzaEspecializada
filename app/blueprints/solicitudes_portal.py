from flask import Blueprint, render_template, session, redirect, url_for, flash, current_app
import os

# Usa utilidades de tu conector legacy
try:
    from ..db_legacy import fetchall, fetchone
except Exception:
    from app.db_legacy import fetchall, fetchone  # pragma: no cover

# Este blueprint mantiene el nombre que esperas en app/__init__.py
sol_portal = Blueprint("sol_portal", __name__, url_prefix="/solicitudes")

# Mínimo de firmantes requeridos (ajustable por ENV)
REQUIRED_FIRMANTES = int(os.getenv("FIRMANTES_MIN", "3"))


def _login_url():
    return url_for("admin.login") if "admin.login" in current_app.view_functions else "/admin/login"

# --- añade este helper arriba, cerca de tus helpers ---
def _is_admin_current() -> bool:
    # Ajusta a tu sesión real:
    role = (session.get("role") or session.get("user_role") or "").lower()
    return bool(
        session.get("is_admin") is True
        or role in ("admin", "superadmin", "administrator")
        or session.get("admin") is True
    )

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

# 🧩 Nueva ruta para crear una solicitud persistida
from app.services.solicitud_service import SolicitudService

@sol_portal.route("/crear/<producto>", methods=["GET"])
def crear_solicitud(producto):
    # Determinar el usuario actual
    # Ajusta según tus campos de sesión reales
    usuario = session.get("username") or session.get("user_name") or session.get("login") or "desconocido"

    # Crear solicitud en BD y obtenerla
    solicitud = SolicitudService.crear_solicitud(
        producto=producto,
        usuario=usuario
    )

    # Redirigir al primer step de tu flujo
    # Ajusta el endpoint frames.formulario_step según cómo lo vayas a implementar
    return redirect(
        url_for(
            "solicitudes_flow.step",
            solicitud_id=solicitud.id,
            step=1
        )
    )

from app.models import Solicitud

@sol_portal.route("/lista", methods=["GET"])
def lista():

    username = session.get("username") or session.get("user_name") or session.get("login")

    if not username:
        return redirect(_login_url())

    is_admin = _is_admin_current()

    if is_admin:
        solicitudes = (
            Solicitud.query
            .order_by(Solicitud.fecha_actualizacion.desc())
            .all()
        )
    else:
        solicitudes = (
            Solicitud.query
            .filter_by(usuario_creador=username)
            .order_by(Solicitud.fecha_actualizacion.desc())
            .all()
        )

    return render_template(
        ["solicitudes/lista.html", "lista.html"],
        solicitudes=solicitudes,
        is_admin=is_admin
    )

from app.models import Producto, RoleProductAccess


@sol_portal.route("/nueva", methods=["GET"])
def nueva():

    username = session.get("username")
    if not username:
        return redirect(_login_url())

    is_admin = _is_admin_current()
    role = (session.get("role") or "").lower()

    if is_admin:
        productos = Producto.query.filter_by(activo=True).all()
    else:
        accesos = RoleProductAccess.query.filter_by(
            role=role,
            habilitado=True
        ).all()

        codes = [a.producto_code for a in accesos]

        productos = (
            Producto.query
            .filter(Producto.code.in_(codes))
            .filter_by(activo=True)
            .all()
        )

    return render_template(
        "solicitudes/seleccionar_producto.html",
        productos=productos
    )
