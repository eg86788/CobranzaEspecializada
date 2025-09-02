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
    """
    Devuelve el HTML tal cual está guardado en DB (content_html) renderizado con Jinja,
    sin concatenar CSS externo ni reordenar nada. Si tu registro tiene 'css', se ignora
    salvo que QUIERAS explícitamente usarlo.
    """
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT content_html, css
            FROM document_templates
            WHERE slug=%s AND is_active=TRUE
            ORDER BY version DESC LIMIT 1
        """, (slug,))
        tpl = cur.fetchone()

    if tpl and tpl.get("content_html"):
        # Renderiza el HTML crudo con Jinja y devuelve exactamente eso.
        # OJO: NO agregamos <style> desde tpl['css'] para no alterar el documento.
        html = render_template_string(tpl["content_html"], **ctx)
        return html

    # Fallback a archivo físico si no existe en DB
    return render_template(f"{slug}.html", **ctx)


# --- REEMPLAZAR SOLO ESTA FUNCIÓN ---

@exportar_bp.route("/exportar_pdf", methods=["GET", "POST"])
@exportar_bp.route("/exportar_pdf/<int:solicitud_id>", methods=["GET"])
def exportar_pdf(solicitud_id=None):
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

    # ---- helpers para resolver el slug operativo (DB → 'anexo_operativo' | fallback 'finalizar') ----
    def _find_first_active_slug(slugs):
        """Devuelve el primer slug activo que exista en document_templates."""
        if not slugs:
            return None
        with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for s in slugs:
                cur.execute(
                    "SELECT 1 FROM document_templates WHERE slug=%s AND is_active=TRUE LIMIT 1",
                    (s,)
                )
                if cur.fetchone():
                    return s
        return None

    def _resolve_operativo_slug():
        """
        1) Permite forzar por ?operativo_slug=...
        2) Si no viene, intenta 'anexo_operativo'
        3) Fallback a 'finalizar'
        """
        forced = request.args.get("operativo_slug")
        if forced:
            return forced.strip() or "finalizar"
        return _find_first_active_slug(["anexo_operativo", "finalizar"]) or "finalizar"

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
    # Si viene solicitud_id por URL, reconstruimos TODO desde BD.
    if solicitud_id:
        with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM solicitudes WHERE id=%s", (solicitud_id,))
            sol = cur.fetchone()
            if not sol:
                flash("No se encontró la solicitud.", "warning")
                return redirect(url_for("solicitudes_portal.lista"))

            # Hijos
            cur.execute("SELECT * FROM unidades  WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
            unidades_db = cur.fetchall() or []
            cur.execute("SELECT * FROM cuentas   WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
            cuentas_db  = cur.fetchall() or []
            cur.execute("SELECT * FROM usuarios  WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
            usuarios_db = cur.fetchall() or []
            cur.execute("SELECT * FROM contactos WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
            contactos_db= cur.fetchall() or []

        # Construye frame1 como lo espera el template
        f1 = {
            "numero_cliente": sol.get("numero_cliente"),
            "razon_social": sol.get("razon_social"),
            "segmento": sol.get("segmento"),
            "domicilio_cliente": sol.get("domicilio_cliente"),
            "numero_contrato": sol.get("numero_contrato"),
            "tipo_tramite": sol.get("tipo_tramite"),
            "tipo_contrato": sol.get("tipo_contrato"),
            "tipo_servicio": sol.get("tipo_servicio"),
            "tipo_cobro": sol.get("tipo_cobro"),
            "importe_maximo_dif": sol.get("importe_maximo_dif"),
            "nombre_ejecutivo": sol.get("nombre_ejecutivo"),
            "rdc_reporte": sol.get("rdc_reporte"),
            "servicio_solicitado": sol.get("servicio_solicitado"),
            "fecha_solicitud": sol.get("fecha_solicitud").isoformat() if sol.get("fecha_solicitud") else None,
            "estatus": sol.get("estatus"),
            "tipo_persona": sol.get("tipo_persona"),
            "telefono_cliente": sol.get("telefono_cliente"),
            "apoderado_legal": sol.get("apoderado_legal"),
        }

        # Firmantes (si existen en BD)
        ff = sol.get("fecha_firma")
        firmantes = {
            "apoderado_legal": sol.get("apoderado_legal") or "",
            "nombre_autorizador": sol.get("nombre_autorizador") or "",
            "nombre_director_divisional": sol.get("nombre_director_divisional") or "",
            "puesto_autorizador": sol.get("puesto_autorizador") or "",
            "puesto_director_divisional": sol.get("puesto_director_divisional") or "",
            "fecha_firma": ff.strftime("%Y-%m-%d") if ff else "",
        }

        # Flags desde BD o deducidos
        anexo_usd_14k = bool(sol.get("anexo_usd_14k"))
        contrato_tradicional = bool(sol.get("contrato_tradicional")) if "contrato_tradicional" in sol else (f1.get("tipo_contrato") == "CPAE TRADICIONAL")
        contrato_electronico = bool(sol.get("contrato_electronico")) if "contrato_electronico" in sol else (f1.get("tipo_contrato") == "SEF ELECTRÓNICO")
        rdc_reporte = bool(sol.get("rdc_reporte"))

        # Contextos usan datos de BD (no tocamos sesión)
        fecha_impresion = datetime.now().strftime("%d/%m/%Y %H:%M")

        ctx_operativo = {
            "frame1": f1,
            "usuarios": usuarios_db,
            "cuentas": cuentas_db,
            "unidades": unidades_db,
            "contactos": contactos_db,
            "apoderado_legal": firmantes.get("apoderado_legal", ""),
            "nombre_autorizador": firmantes.get("nombre_autorizador", ""),
            "nombre_director_divisional": firmantes.get("nombre_director_divisional", ""),
            "puesto_autorizador": firmantes.get("puesto_autorizador", ""),
            "puesto_director_divisional": firmantes.get("puesto_director_divisional", ""),
            "imprimir_pdf": True,
            "fecha_impresion": fecha_impresion,
            "firmantes": firmantes,
            "fecha_firma": firmantes.get("fecha_firma") or "",
        }

        ctx_usd = {
            "frame1": f1,
            "firmantes": firmantes,
            "apoderado_legal": firmantes.get("apoderado_legal", ""),
            "nombre_autorizador": firmantes.get("nombre_autorizador", ""),
            "nombre_director_divisional": firmantes.get("nombre_director_divisional", ""),
            "fecha_impresion": fecha_impresion,
            "fecha_firma": firmantes.get("fecha_firma") or "",
            "imprimir_pdf": True,
        }

        # --- Slug operativo (forzado por query o detectado) ---
        operativo_slug = _resolve_operativo_slug()

        # Render y PDFs desde BD
        html_operativo = render_doc_by_slug(operativo_slug, **ctx_operativo)
        pdf_operativo = HTML(string=html_operativo, base_url=request.url_root).write_pdf()

        pdf_usd = None
        if anexo_usd_14k:
            html_usd = render_doc_by_slug("anexo_usd14k", **ctx_usd)
            pdf_usd = HTML(string=html_usd, base_url=request.url_root).write_pdf()

        pdf_tradicional = None
        if contrato_tradicional:
            html_tradicional = render_doc_by_slug("contrato_tradicional", **ctx_operativo)
            pdf_tradicional = HTML(string=html_tradicional, base_url=request.url_root).write_pdf()

        pdf_electronico = None
        if contrato_electronico:
            html_electronico = render_doc_by_slug("contrato_electronico", **ctx_operativo)
            pdf_electronico = HTML(string=html_electronico, base_url=request.url_root).write_pdf()

        pdf_rdc = None
        if rdc_reporte:
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
        filename_zip = f"documentos_{(f1.get('numero_cliente') or 'NA')}_{datetime.now().strftime('%Y-%m-%d')}.zip"
        return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=filename_zip)

    # ------- SIN solicitud_id: sigue funcionando con datos de sesión (flujo actual) -------
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
    }

    # --- Slug operativo (forzado por query o detectado) ---
    operativo_slug = _resolve_operativo_slug()

    # Render y PDFs (sesión)
    html_operativo = render_doc_by_slug(operativo_slug, **ctx_operativo)
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
