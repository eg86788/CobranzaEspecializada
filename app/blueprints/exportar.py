# app/blueprints/exportar.py
from flask import Blueprint, request, session, render_template, render_template_string, redirect, url_for, send_file, flash
from datetime import datetime
from weasyprint import HTML
from io import BytesIO
import psycopg2.extras, zipfile
from app.services.adhesion import numero_adhesion
from ..db_legacy import conectar

# NUEVO: importar el servicio de guardado
from app.services.solicitudes_sef import guardar_solicitud_desde_session

exportar_bp = Blueprint("exportar", __name__)

def render_doc_by_slug(slug: str, **ctx) -> str:
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT content_html, css
            FROM document_templates
            WHERE slug=%s AND is_active=TRUE
            ORDER BY version DESC LIMIT 1
        """, (slug,))
        tpl = cur.fetchone()
    if tpl:
        html = render_template_string(tpl["content_html"], **ctx)
        if tpl.get("css"):
            html = f"<style>{tpl['css']}</style>\n{html}"
        return html
    return render_template(f"{slug}.html", **ctx)

@exportar_bp.route("/exportar_pdf", methods=["GET", "POST"])
def exportar_pdf():
    # ---- helper local: normaliza fecha a YYYY-MM-DD con fallback hoy ----
    def normaliza_fecha(value: str | None) -> str:
        value = (value or "").strip()
        if not value:
            return datetime.now().strftime("%Y-%m-%d")
        if "/" in value:
            try:
                return datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                return datetime.now().strftime("%Y-%m-%d")
        try:
            datetime.strptime(value, "%Y-%m-%d")
            return value
        except ValueError:
            return datetime.now().strftime("%Y-%m-%d")

    # ----------------- POST: guarda datos del form en sesión -----------------
    if request.method == "POST":
        fecha_norm = normaliza_fecha(request.form.get("fecha_firma"))
        session["firmantes"] = {
            "apoderado_legal": (request.form.get("apoderado_legal") or "").strip(),
            "nombre_autorizador": (request.form.get("nombre_autorizador") or "").strip(),
            "nombre_director_divisional": (request.form.get("nombre_director_divisional") or "").strip(),
            "puesto_autorizador": (request.form.get("puesto_autorizador") or "").strip(),
            "puesto_director_divisional": (request.form.get("puesto_director_divisional") or "").strip(),
            "fecha_firma": fecha_norm,
        }
        session["anexo_usd_14k"] = bool(request.form.get("anexo_usd_14k"))

        f1 = session.get("frame1", {}) or {}
        session["contrato_tradicional"] = f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "CPAE TRADICIONAL"
        session["contrato_electronico"] = f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "SEF ELECTRÓNICO"
        session.modified = True

        # Si NO es confirmar, seguimos el flujo normal: GET genera los PDFs
        return redirect(url_for("exportar.exportar_pdf"))

    # ----------------- GET: valida y construye contextos -----------------
    if not session.get("frame1"):
        flash("Faltan datos de la solicitud.", "warning")
        return redirect(url_for("frames.frame1"))

    f1 = session.get("frame1", {})
    firmantes = session.get("firmantes", {}) or {}
    fecha_firma_raw = normaliza_fecha(firmantes.get("fecha_firma"))
    firmantes["fecha_firma"] = fecha_firma_raw
    session["firmantes"] = firmantes
    session.modified = True

    fecha_impresion = datetime.now().strftime("%d/%m/%Y %H:%M")

    # mapea tu contrato a clave (si quieres usar adhesiones)
    clave = "SEF_TRADICIONAL" if f1.get("tipo_contrato") == "CPAE TRADICIONAL" else (
            "SEF_ELECTRONICO" if f1.get("tipo_contrato") == "SEF ELECTRÓNICO" else None)
    adh_num = numero_adhesion(clave, fecha_firma_raw) if clave else None

    ctx_operativo = {
        "frame1": f1,
        "usuarios": session.get("usuarios", []),
        "cuentas": session.get("cuentas", []),
        "unidades": session.get("unidades", []),
        "contactos": session.get("contactos", []),
        "apoderado_legal": firmantes.get("apoderado_legal", ""),
        "nombre_autorizador": firmantes.get("nombre_autorizador", ""),
        "nombre_director_divisional": firmantes.get("nombre_director_divisional", ""),
        "puesto_autorizador": firmantes.get("puesto_autorizador", ""),
        "puesto_director_divisional": firmantes.get("puesto_director_divisional", ""),
        "imprimir_pdf": True,
        "fecha_impresion": fecha_impresion,
        "firmantes": firmantes,
        "fecha_firma": fecha_firma_raw,
        # "adhesion_numero": adh_num,
    }

    ctx_usd = {
        "frame1": f1,
        "firmantes": firmantes,
        "apoderado_legal": firmantes.get("apoderado_legal", ""),
        "nombre_autorizador": firmantes.get("nombre_autorizador", ""),
        "nombre_director_divisional": firmantes.get("nombre_director_divisional", ""),
        "fecha_impresion": fecha_impresion,
        "fecha_firma": fecha_firma_raw,
        "imprimir_pdf": True,
        # "adhesion_numero": adh_num,
    }

    # Render y PDFs
    html_operativo = render_doc_by_slug("finalizar", **ctx_operativo)
    pdf_operativo = HTML(string=html_operativo, base_url=request.url_root).write_pdf()

    pdf_usd = None
    if session.get("anexo_usd_14k"):
        html_usd = render_doc_by_slug("anexo_usd14k", **ctx_usd)
        pdf_usd = HTML(string=html_usd, base_url=request.url_root).write_pdf()

    pdf_tradicional = None
    if session.get("contrato_tradicional"):
        html_tradicional = render_doc_by_slug("contrato_tradicional", **ctx_operativo)
        pdf_tradicional = HTML(string=html_tradicional, base_url=request.url_root).write_pdf()

    pdf_electronico = None
    if session.get("contrato_electronico"):
        html_electronico = render_doc_by_slug("contrato_electronico", **ctx_operativo)
        pdf_electronico = HTML(string=html_electronico, base_url=request.url_root).write_pdf()

    pdf_rdc = None
    if session.get("rdc_reporte"):
        html_rdc = render_doc_by_slug("reporte_rdc", **ctx_operativo)
        pdf_rdc = HTML(string=html_rdc, base_url=request.url_root).write_pdf()

    # ZIP
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("02_Anexo_Operativo.pdf", pdf_operativo)
        if pdf_usd:
            zf.writestr("03_Anexo_USD14K.pdf", pdf_usd)
        if pdf_tradicional:
            zf.writestr("01_Contrato_SEF_Tradicional.pdf", pdf_tradicional)
        if pdf_electronico:
            zf.writestr("01_Contrato_SEF_Electronico.pdf", pdf_electronico)
        if pdf_rdc:
            zf.writestr("04_RDC.pdf", pdf_rdc)

    zip_buffer.seek(0)
    filename_zip = f"documentos_{f1.get('numero_cliente','NA')}_{datetime.now().strftime('%Y-%m-%d')}.zip"
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=filename_zip)


@exportar_bp.route("/fake_data")
def fake_data():
    session["frame1"] = {
        "numero_cliente": "123456789",
        "tipo_tramite": "ALTA",
        "tipo_contrato": "CPAE TRADICIONAL",
    }
    session["firmantes"] = {
        "apoderado_legal": "Lic. Juan Pérez",
        "nombre_autorizador": "Ana López",
        "nombre_director_divisional": "Carlos Ruiz",
        "puesto_autorizador": "Gerente",
        "puesto_director_divisional": "Director",
        "fecha_firma": "20/08/2025",
    }
    session["usuarios"] = []
    session["cuentas"] = []
    session["unidades"] = []
    session["contactos"] = []
    session["anexo_usd_14k"] = True
    session["contrato_tradicional"] = True
    session["contrato_electronico"] = False
    return "Datos de prueba cargados"

@exportar_bp.route("/_debug_session")
def _debug_session():
    return {"firmantes": session.get("firmantes"), "frame1": session.get("frame1")}
