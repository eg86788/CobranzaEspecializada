# app/blueprints/solicitudes_portal.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import psycopg2.extras
from ..db_legacy import conectar
from ..services.solicitudes_sef import cargar_solicitud_a_session, guardar_solicitud_desde_session
from ..blueprints.exportar import render_doc_by_slug
from weasyprint import HTML
from io import BytesIO
import zipfile
from datetime import datetime
from flask import send_file, current_app

sol_portal = Blueprint("sol_portal", __name__, url_prefix="/solicitudes")

def _ensure_user():
    if not session.get("role"):
        flash("Inicia sesión para continuar.", "warning")
        return False
    return True

@sol_portal.route("/lista")
def lista():
    if not _ensure_user():
        return redirect(url_for("auth_admin.login", next=request.path))

    q = (request.args.get("q") or "").strip()
    # Si created_by en tu DB es TEXT, usamos username. Si es INT, cambia a user_id.
    created_by = session.get("username") or "anon"

    where = ["created_by = %s"]
    params = [created_by]

    if q:
        where.append("""(
            CAST(numero_cliente AS TEXT) ILIKE %s OR
            razon_social ILIKE %s OR
            tipo_contrato ILIKE %s OR
            tipo_servicio ILIKE %s
        )""")
        like = f"%{q}%"
        params.extend([like, like, like, like])

    sql = f"""
        SELECT id, numero_cliente, razon_social, tipo_servicio, tipo_contrato, tipo_tramite,
               COALESCE(TO_CHAR(updated_at,'YYYY-MM-DD HH24:MI'), TO_CHAR(created_at,'YYYY-MM-DD HH24:MI')) AS actualizado
        FROM solicitudes
        WHERE {" AND ".join(where)}
        ORDER BY updated_at DESC NULLS LAST, created_at DESC
        LIMIT 500
    """
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        items = cur.fetchall()

    return render_template("solicitudes/lista.html", items=items, q=q)

@sol_portal.route("/<int:solicitud_id>/detalle")
def detalle(solicitud_id: int):
    if not _ensure_user():
        return redirect(url_for("auth_admin.login", next=request.path))
    try:
        cargar_solicitud_a_session(solicitud_id, session)
        flash("Solicitud cargada para edición.", "info")
        # te manda al frame finalizar (modo edición)
        return redirect(url_for("frames.finalizar"))
    except Exception as e:
        flash(f"Error al cargar: {e}", "danger")
        return redirect(url_for("sol_portal.lista"))

@sol_portal.route("/<int:solicitud_id>/exportar")
def exportar_zip(solicitud_id: int):
    if not _ensure_user():
        return redirect(url_for("auth_admin.login", next=request.path))
    # Carga la solicitud a sesión
    try:
        cargar_solicitud_a_session(solicitud_id, session)
    except Exception as e:
        flash(f"Error al cargar: {e}", "danger")
        return redirect(url_for("sol_portal.lista"))

    # Validar firmantes en session
    f = session.get("firmantes") or {}
    faltan = [k for k in ("apoderado_legal","nombre_autorizador","nombre_director_divisional",
                          "puesto_autorizador","puesto_director_divisional","fecha_firma") if not (f.get(k) or "").strip()]
    if faltan:
        flash("Faltan datos de firmantes. Entra a 'Ver' y completa para exportar.", "warning")
        return redirect(url_for("sol_portal.detalle", solicitud_id=solicitud_id))

    # Render como en exportar_pdf, pero aquí directo
    base_url = request.url_root
    f1 = session.get("frame1", {})
    fecha_impresion = datetime.now().strftime("%d/%m/%Y %H:%M")
    firmantes = session.get("firmantes", {})

    ctx = {
        "frame1": f1,
        "usuarios": session.get("usuarios", []),
        "cuentas": session.get("cuentas", []),
        "unidades": session.get("unidades", []),
        "contactos": session.get("contactos", []),
        "firmantes": firmantes,
        "apoderado_legal": firmantes.get("apoderado_legal",""),
        "nombre_autorizador": firmantes.get("nombre_autorizador",""),
        "nombre_director_divisional": firmantes.get("nombre_director_divisional",""),
        "puesto_autorizador": firmantes.get("puesto_autorizador",""),
        "puesto_director_divisional": firmantes.get("puesto_director_divisional",""),
        "fecha_impresion": fecha_impresion,
        "fecha_firma": firmantes.get("fecha_firma",""),
        "imprimir_pdf": True,
    }

    def _pdf(slug):
        html = render_doc_by_slug(slug, **ctx)
        return HTML(string=html, base_url=base_url).write_pdf()

    pdf_operativo = _pdf("finalizar")

    pdf_usd = None
    if firmantes.get("anexo_usd_14k") or session.get("anexo_usd_14k"):
        pdf_usd = _pdf("anexo_usd14k")

    pdf_trad = None
    if f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "CPAE TRADICIONAL":
        pdf_trad = _pdf("contrato_tradicional")

    pdf_ele = None
    if f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "SEF ELECTRÓNICO":
        pdf_ele = _pdf("contrato_electronico")

    pdf_rdc = None
    if session.get("rdc_reporte"):
        pdf_rdc = _pdf("reporte_rdc")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("02_Anexo_Operativo.pdf", pdf_operativo)
        if pdf_usd: zf.writestr("03_Anexo_USD14K.pdf", pdf_usd)
        if pdf_trad: zf.writestr("01_Contrato_SEF_Tradicional.pdf", pdf_trad)
        if pdf_ele: zf.writestr("01_Contrato_SEF_Electronico.pdf", pdf_ele)
        if pdf_rdc: zf.writestr("04_RDC.pdf", pdf_rdc)

    zip_buffer.seek(0)
    filename_zip = f"documentos_{f1.get('numero_cliente','NA')}_{datetime.now().strftime('%Y-%m-%d')}.zip"
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=filename_zip)
