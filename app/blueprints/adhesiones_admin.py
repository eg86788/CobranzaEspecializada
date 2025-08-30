from flask import Blueprint, render_template, request, redirect, url_for, flash
import psycopg2.extras
from ..db_legacy import conectar
from .auth_admin import admin_required
from datetime import datetime

adh_bp = Blueprint("adh_admin", __name__, url_prefix="/admin/adhesiones")

@adh_bp.before_request
def guard():
    if not admin_required():
        return redirect(url_for("auth_admin.login"))

def q_all():
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM catalogo_adhesiones ORDER BY clave, vigente_desde DESC")
        return cur.fetchall()

@adh_bp.route("/")
def list_adh():
    return render_template("adh_list.html", items=q_all())

@adh_bp.route("/new", methods=["GET","POST"])
def new_adh():
    if request.method == "POST":
        clave  = request.form["clave"].strip()
        numero = request.form["numero"].strip()
        vdesde = datetime.strptime(request.form["vigente_desde"], "%Y-%m-%d").date()
        vhasta = request.form.get("vigente_hasta")
        vhasta = datetime.strptime(vhasta, "%Y-%m-%d").date() if vhasta else None
        with conectar() as conn, conn.cursor() as cur:
            cur.execute("""INSERT INTO catalogo_adhesiones
                (clave, numero, vigente_desde, vigente_hasta, activo, updated_by, updated_at)
                VALUES (%s,%s,%s,%s,TRUE,%s,NOW())""",
                (clave, numero, vdesde, vhasta, "admin@local"))
            conn.commit()
        flash("Registro creado.", "success")
        return redirect(url_for("adh_admin.list_adh"))
    return render_template("adh_edit.html", item=None)

@adh_bp.route("/<int:item_id>/edit", methods=["GET","POST"])
def edit_adh(item_id):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT * FROM catalogo_adhesiones WHERE id=%s", (item_id,))
        item = cur.fetchone()
    if not item:
        flash("No encontrado.", "warning")
        return redirect(url_for("adh_admin.list_adh"))

    if request.method == "POST":
      from datetime import datetime
      clave  = request.form["clave"].strip()
      numero = request.form["numero"].strip()
      vdesde = datetime.strptime(request.form["vigente_desde"], "%Y-%m-%d").date()
      vhasta = request.form.get("vigente_hasta")
      vhasta = datetime.strptime(vhasta, "%Y-%m-%d").date() if vhasta else None
      activo = bool(request.form.get("activo"))

      with conectar() as conn, conn.cursor() as cur:
        cur.execute("""UPDATE catalogo_adhesiones SET
            clave=%s, numero=%s, vigente_desde=%s, vigente_hasta=%s, activo=%s, updated_at=NOW()
            WHERE id=%s""",
            (clave, numero, vdesde, vhasta, activo, item_id))
        conn.commit()
      flash("Actualizado.", "success")
      return redirect(url_for("adh_admin.list_adh"))

    return render_template("adh_edit.html", item=item)
