# app/blueprints/config_campos_admin.py
# -----------------------------------------------------------------------------
# CRUD Admin para la tabla config_campos (visibilidad/obligatoriedad por frame/campo)
# Solo accesible para usuarios con role "admin" en sesión (session["role"] == "admin")
# -----------------------------------------------------------------------------

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import json
import logging

# Conectores BD (usa tu módulo db_legacy, igual que frames.py)
try:
    from ..db_legacy import fetchall, fetchone, conectar
except Exception:   # pragma: no cover
    from app.db_legacy import fetchall, fetchone, conectar  # pragma: no cover

log = logging.getLogger(__name__)

config_campos_admin_bp = Blueprint(
    "config_campos_admin",
    __name__,
    url_prefix="/admin/config-campos"
)

# ---------------------------------------------------------------------
# Guard de administrador: reutiliza tu lógica basada en session["role"]
# ---------------------------------------------------------------------
@config_campos_admin_bp.before_request
def _admin_only():
    # Reutiliza tu guard existente: solo admins
    if session.get("role") != "admin":
        flash("Acceso restringido a administradores.", "warning")
        return redirect(url_for("auth_admin.login"))

# ----------------------------- Helpers ---------------------------------------
def _clean_bool(v):
    return str(v).strip().lower() in ("1", "true", "t", "yes", "si", "on")

def _load_conditions(raw):
    """Valida que conditions sea JSON (lista u objeto); si vacío -> lista []"""
    txt = (raw or "").strip()
    if not txt:
        return []
    try:
        val = json.loads(txt)
        return val
    except Exception as e:
        raise ValueError(f"Conditions debe ser JSON válido: {e}")

# ----------------------------- Rutas -----------------------------------------

@config_campos_admin_bp.route("/", methods=["GET"])
@config_campos_admin_bp.route("/listar", methods=["GET"])
def listar():
    """Lista de configuraciones con orden lógico."""
    try:
        rows = fetchall("""
            SELECT id, frame, field_name, visible_default, required_default,
                   disabled_default, conditions, grupo, orden, updated_at
            FROM config_campos
            ORDER BY frame, COALESCE(grupo, ''), orden, field_name
        """) or []
    except Exception as e:
        log.exception("Error cargando lista de config_campos")
        flash(f"No fue posible cargar la lista: {e}", "danger")
        rows = []

    return render_template("admin/config_campos_list.html", rows=rows)

@config_campos_admin_bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    if request.method == "POST":
        try:
            frame = (request.form.get("frame") or "").strip()
            field_name = (request.form.get("field_name") or "").strip()
            visible_default = _clean_bool(request.form.get("visible_default"))
            required_default = _clean_bool(request.form.get("required_default"))
            disabled_default = _clean_bool(request.form.get("disabled_default"))
            conditions = _load_conditions(request.form.get("conditions"))
            grupo = (request.form.get("grupo") or "").strip() or None
            orden = int((request.form.get("orden") or "0").strip() or 0)

            if not frame or not field_name:
                raise ValueError("Frame y Field Name son obligatorios.")

            with conectar() as conn, conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO config_campos (
                        frame, field_name, visible_default, required_default, disabled_default,
                        conditions, grupo, orden, updated_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now())
                """, (frame, field_name, visible_default, required_default, disabled_default,
                      json.dumps(conditions), grupo, orden))
            flash("Campo creado correctamente.", "success")
            return redirect(url_for("config_campos_admin.listar"))
        except ValueError as ve:
            flash(str(ve), "warning")
        except Exception as e:
            log.exception("Error creando config de campo")
            flash(f"Error al crear: {e}", "danger")

    return render_template("admin/config_campos_form.html", mode="new", row=None)

@config_campos_admin_bp.route("/<int:row_id>/editar", methods=["GET", "POST"])
def editar(row_id):
    row = fetchone("SELECT * FROM config_campos WHERE id = %s", (row_id,))
    if not row:
        flash("No se encontró el registro solicitado.", "warning")
        return redirect(url_for("config_campos_admin.listar"))

    if request.method == "POST":
        try:
            frame = (request.form.get("frame") or "").strip()
            field_name = (request.form.get("field_name") or "").strip()
            visible_default = _clean_bool(request.form.get("visible_default"))
            required_default = _clean_bool(request.form.get("required_default"))
            disabled_default = _clean_bool(request.form.get("disabled_default"))
            conditions = _load_conditions(request.form.get("conditions"))
            grupo = (request.form.get("grupo") or "").strip() or None
            orden = int((request.form.get("orden") or "0").strip() or 0)

            if not frame or not field_name:
                raise ValueError("Frame y Field Name son obligatorios.")

            with conectar() as conn, conn.cursor() as cur:
                cur.execute("""
                    UPDATE config_campos SET
                        frame = %s,
                        field_name = %s,
                        visible_default = %s,
                        required_default = %s,
                        disabled_default = %s,
                        conditions = %s,
                        grupo = %s,
                        orden = %s,
                        updated_at = now()
                    WHERE id = %s
                """, (frame, field_name, visible_default, required_default, disabled_default,
                      json.dumps(conditions), grupo, orden, row_id))
            flash("Campo actualizado correctamente.", "success")
            return redirect(url_for("config_campos_admin.listar"))

        except ValueError as ve:
            flash(str(ve), "warning")
        except Exception as e:
            log.exception("Error actualizando config de campo")
            flash(f"Error al actualizar: {e}", "danger")

    # Prepara conditions como texto formateado para el textarea
    try:
        conditions_txt = json.dumps(row.get("conditions") or [], ensure_ascii=False, indent=2)
    except Exception:
        conditions_txt = (row.get("conditions") or "[]")
    row["conditions_txt"] = conditions_txt

    return render_template("admin/config_campos_form.html", mode="edit", row=row)

@config_campos_admin_bp.route("/<int:row_id>/eliminar", methods=["POST"])
def eliminar(row_id):
    try:
        with conectar() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM config_campos WHERE id = %s", (row_id,))
        flash("Registro eliminado.", "info")
    except Exception as e:
        log.exception("Error eliminando config de campo")
        flash(f"No fue posible eliminar: {e}", "danger")
    return redirect(url_for("config_campos_admin.listar"))
