# app/blueprints/frames.py
# El flujo de captura dividido en frames 1..5 y 'finalizar'.
# Incluye validaciones, gestión de sesión y nombres de claves consistentes.

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from ..db_legacy import fetchall, fetchone, execute
from ..utils.session_utils import limpiar_dependientes, hay_dependientes, normalizar_unidad
from ..auth.decorators import login_required



frames_bp = Blueprint("frames", __name__)

@frames_bp.before_request
@login_required
def _guard_frames():
    pass

# ---------- FRAME 1 ----------
@frames_bp.route("/solicitud_sef", methods=["GET", "POST"])
def frame1():
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    if request.method == "POST":
        datos = {k: request.form.get(k, "").strip() for k in (
            "tipo_tramite","nombre_ejecutivo","segmento","numero_cliente","tipo_persona",
            "razon_social","apoderado_legal","correo_apoderado_legal","tipo_contrato","tipo_servicio","tipo_cobro",
            "importe_maximo_dif","numero_contrato","telefono_cliente","domicilio_cliente"
        )}

        # Normalización de contrato
        if datos["tipo_tramite"] == "ALTA":
            datos["numero_contrato"] = "-"
        elif not datos["numero_contrato"]:
            datos["numero_contrato"] = "-"

        # Validación mínima
        obligatorios = ("tipo_tramite","nombre_ejecutivo","segmento","numero_cliente",
                        "razon_social","apoderado_legal", "correo_apoderado_legal","tipo_persona","tipo_contrato",
                        "tipo_servicio","tipo_cobro")
        if not all(datos.get(k) for k in obligatorios):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("frames.frame1"))

        # Si cambian llaves que afectan dependencias, limpiamos
        frame1_prev = session.get("frame1", {})
        if frame1_prev and any((
            datos["tipo_tramite"] != frame1_prev.get("tipo_tramite"),
            datos["tipo_contrato"] != frame1_prev.get("tipo_contrato"),
            datos["tipo_servicio"] != frame1_prev.get("tipo_servicio"),
        )):
            limpiar_dependientes()
            flash("Se borró la información de unidades, cuentas, usuarios y contactos por cambiar el tipo de contrato.", "warning")

        if not datos["importe_maximo_dif"]:
            datos["importe_maximo_dif"] = "-"

        session["rdc_reporte"] = (datos.get("tipo_cobro") == "CENTRALIZADO")

        session["frame1"] = {
            **datos,
            "numero_cliente": int(datos["numero_cliente"]),
            "fecha_solicitud": datetime.now().isoformat(),
        }
        return redirect(url_for("frames.frame2"))

    return render_template(
        "frame1.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        paso_actual=1,
        catalogo_cpae=catalogo_cpae,
        catalogo_etv=catalogo_etv,
        catalogo_estados=catalogo_estados,
        hay_datos_dependientes=hay_dependientes(),
    )

# ---------- FRAME 2 ----------
@frames_bp.route("/unidades", methods=["GET", "POST"])
def frame2():
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    # Decorar unidades con nombres legibles
    unidades = session.get("unidades", [])
    for u in unidades:
        if u.get("municipio_id"):
            row = fetchone("SELECT nombre FROM catalogo_municipios WHERE id=%s", (u["municipio_id"],))
            u["municipio_nombre"] = row["nombre"] if row else "Sin municipio"
        if u.get("empresa_traslado"):
            row = fetchone("SELECT descripcion FROM catalogo_etv WHERE id=%s", (u["empresa_traslado"],))
            u["etv_nombre"] = row["descripcion"] if row else "Sin ETV"
        if u.get("estado"):
            row = fetchone("SELECT nombre FROM catalogo_estados WHERE id=%s", (u["estado"],))
            u["estado_nombre"] = row["nombre"] if row else "Sin estado"
        if u.get("cpae"):
            row = fetchone("SELECT descripcion FROM catalogo_cpae WHERE id=%s", (u["cpae"],))
            u["cpae_nombre"] = row["descripcion"] if row else "Sin CPAE"

    if request.method == "POST":
        if "regresar" in request.form:
            return redirect(url_for("frames.frame1"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            unidades = session.get("unidades", [])
            if 0 <= idx < len(unidades):
                unidades.pop(idx)
                session["unidades"] = unidades
            return redirect(url_for("frames.frame2"))

        campos_obligatorios = (
            "cpae", "tipo_servicio_unidad",
            "empresa_traslado", "calle_numero", "colonia", "municipio_id",
            "estado", "codigo_postal"
        )
        faltantes = [c for c in campos_obligatorios if not request.form.get(c)]
        if faltantes:
            from markupsafe import escape
            faltantes = [escape(f) for f in faltantes]
            flash(f"Faltan campos: {', '.join(faltantes)}", "danger")
            return redirect(url_for("frames.frame2"))

        unidad = normalizar_unidad(request.form)
        unidades = session.get("unidades", [])
        unidades.append(unidad)
        session["unidades"] = unidades
        flash("Unidad agregada.", "success")
        return redirect(url_for("frames.frame2"))

    return render_template(
        "frame2.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        catalogo_cpae=catalogo_cpae,
        catalogo_etv=catalogo_etv,
        catalogo_estados=catalogo_estados,
        paso_actual=2,
    )

# ---------- VALIDACIÓN CARGA MASIVA ----------
@frames_bp.route("/validar_excel_unidades", methods=["POST"])
def validar_excel_unidades():
    import pandas as pd
    from werkzeug.utils import secure_filename  # por si decides guardar

    columnas_esperadas = [
        "ORIGEN", "TIPO_SERVICIO", "NUMERO_TERMINAL", "NOMBRE_UNIDAD",
        "CPAE", "EMPRESA_TRASLADO", "CALLE_NUMERO", "COLONIA",
        "MUNICIPIO_ID", "ESTADO", "CODIGO_POSTAL",
        "TERMINAL_INTEGRADORA", "DOTACION_CENTRALIZADA", "CERTIFICADO_CENTRALIZADA"
    ]

    if "archivo_excel" not in request.files:
        return {"errores": ["No se recibió ningún archivo."]}, 400

    archivo = request.files["archivo_excel"]
    if not archivo.filename.endswith((".xlsx", ".xls")):
        return {"errores": ["El archivo debe tener extensión .xlsx o .xls"]}, 400

    try:
        df = pd.read_excel(archivo, header=0)
        columnas_faltantes = [c for c in columnas_esperadas if c not in df.columns]
        if columnas_faltantes:
            return {"errores": [f"Faltan columnas: {', '.join(columnas_faltantes)}"]}, 400

        if len(df) > 1000:
            return {"errores": ["El archivo excede el límite de 1000 registros."]}, 400

        errores = []
        for i, fila in df.iterrows():
            if pd.isna(fila["NOMBRE_UNIDAD"]):
                errores.append(f"Fila {i+2}: Falta NOMBRE_UNIDAD.")
            if pd.isna(fila["MUNICIPIO_ID"]):
                errores.append(f"Fila {i+2}: Falta MUNICIPIO_ID.")
        if errores:
            return {"errores": errores}, 400

        # Mapeo a la estructura de 'unidades' de sesión
        registros = []
        for _, r in df.iterrows():
            registros.append({
                "origen_unidad": r.get("ORIGEN"),
                "tipo_unidad": r.get("TIPO_SERVICIO"),
                "tipo_servicio": r.get("TIPO_SERVICIO"),
                "numero_terminal_sef": r.get("NUMERO_TERMINAL"),
                "nombre_unidad": r.get("NOMBRE_UNIDAD"),
                "cpae": r.get("CPAE"),
                "empresa_traslado": r.get("EMPRESA_TRASLADO"),
                "calle_numero": r.get("CALLE_NUMERO"),
                "colonia": r.get("COLONIA"),
                "municipio_id": r.get("MUNICIPIO_ID"),
                "estado": r.get("ESTADO"),
                "codigo_postal": r.get("CODIGO_POSTAL"),
                "terminal_integradora": r.get("TERMINAL_INTEGRADORA"),
                "terminal_dotacion_centralizada": r.get("DOTACION_CENTRALIZADA"),
                "terminal_certificado_centralizada": r.get("CERTIFICADO_CENTRALIZADA"),
            })

        session["unidades"] = registros
        return {"registros": registros}
    except Exception as e:
        return {"errores": [f"Error al procesar el archivo: {str(e)}"]}, 500

# ---------- FRAME 3 ----------
@frames_bp.route("/cuentas", methods=["GET", "POST"])
def frame3():
    if request.method == "POST":
        if "regresar_frame1" in request.form: return redirect(url_for("frames.frame1"))
        if "regresar_frame2" in request.form: return redirect(url_for("frames.frame2"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            cuentas = session.get("cuentas", [])
            if 0 <= idx < len(cuentas):
                cuentas.pop(idx)
                session["cuentas"] = cuentas
            return redirect(url_for("frames.frame3"))

        campos = ("servicio","sucursal","cuenta","moneda","terminal_aplica")
        if not all(request.form.get(c) for c in campos):
            flash("Completa todos los datos de la cuenta.", "danger")
            return redirect(url_for("frames.frame3"))

        cuenta = {k: request.form.get(k) for k in campos}

        # Confirmación USD para el anexo
        confirmacion_usd = request.form.get("confirmacion_usd")
        if "USD" in (cuenta.get("moneda") or ""):
            session["anexo_usd_14k"] = (confirmacion_usd == "NO")
        else:
            session["anexo_usd_14k"] = False

        session.setdefault("cuentas", []).append(cuenta)
        flash("Cuenta agregada.", "success")
        return redirect(url_for("frames.frame3"))

    return render_template(
        "frame3.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        paso_actual=3,
    )

# ---------- FRAME 4 ----------
@frames_bp.route("/usuarios_sef", methods=["GET", "POST"])
def frame4():
    catalogo_perfiles = fetchall("SELECT perfil, perfil FROM catalogo_perfiles ORDER BY perfil")

    if request.method == "POST":
        if "regresar_frame1" in request.form: return redirect(url_for("frames.frame1"))
        if "regresar_frame2" in request.form: return redirect(url_for("frames.frame2"))
        if "regresar_frame3" in request.form: return redirect(url_for("frames.frame3"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            usuarios = session.get("usuarios", [])
            if 0 <= idx < len(usuarios):
                usuarios.pop(idx)
                session["usuarios"] = usuarios
            return redirect(url_for("frames.frame4"))

        usuario = {k: request.form.get(k) for k in (
            "tipo_usuario","terminal_aplica","nombre_usuario",
            "clave_usuario","perfil","maker_checker","correo","telefono",
            "monto_mxn","monto_usd"
        )}

        if not usuario["perfil"]:
            flash("El campo perfil es obligatorio.", "danger")
            return redirect(url_for("frames.frame4"))

        session.setdefault("usuarios", []).append(usuario)
        session["ultimo_perfil"] = usuario["perfil"]
        flash("Usuario agregado.", "success")
        return redirect(url_for("frames.frame4"))

    terminales = [u["numero_terminal_sef"] for u in session.get("unidades", []) if u.get("numero_terminal_sef")]
    perfil_seleccionado = session.pop("ultimo_perfil", "")

    return render_template(
        "frame4.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        lista_terminales=terminales,
        catalogo_perfiles=catalogo_perfiles,
        paso_actual=4,
        perfil_seleccionado=perfil_seleccionado,
    )

# ---------- FRAME 5 ----------
@frames_bp.route("/contactos", methods=["GET", "POST"])
def frame5():
    if request.method == "POST":
        for btn, destino in (
            ("regresar_frame1","frames.frame1"),
            ("regresar_frame2","frames.frame2"),
            ("regresar_frame3","frames.frame3"),
            ("regresar_frame4","frames.frame4"),
        ):
            if btn in request.form:
                return redirect(url_for(destino))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            contactos = session.get("contactos", [])
            if 0 <= idx < len(contactos):
                contactos.pop(idx)
                session["contactos"] = contactos
            return redirect(url_for("frames.frame5"))

        contacto = {
            "numero_terminal_sef": request.form.get("numero_terminal_sef") or None,
            "nombre_contacto": request.form.get("nombre_contacto"),
            "telefono": request.form.get("telefono"),
            "correo": request.form.get("correo"),
            "tipos_contacto": request.form.getlist("tipos_contacto"),
        }
        if not contacto["nombre_contacto"]:
            flash("El nombre del contacto es obligatorio.", "danger")
            return redirect(url_for("frames.frame5"))

        session.setdefault("contactos", []).append(contacto)
        flash("Contacto agregado.", "success")
        return redirect(url_for("frames.frame5"))

    terminales = [u["numero_terminal_sef"] for u in session.get("unidades", []) if u.get("numero_terminal_sef")]
    return render_template(
        "frame5.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        lista_terminales=terminales,
        paso_actual=5,
    )

# app/blueprints/frames.py (dentro de finalizar)
from app.services.solicitudes_sef import guardar_solicitud_desde_session
from ..utils.session_utils import limpiar_sesion

@frames_bp.route("/terminar", methods=["GET", "POST"])
def finalizar():
    if request.method == "POST":
        if "regresar_frame5" in request.form:
            return redirect(url_for("frames.frame5"))
        if "confirmar" in request.form:
            try:
                solicitud_id = guardar_solicitud_desde_session(session)
                limpiar_sesion()
                flash(f"Solicitud #{solicitud_id} guardada en BD.", "success")
                return redirect(url_for("frames.frame1"))
            except Exception as e:
                flash(f"Error BD: {e}", "danger")

    return render_template(
        "finalizar.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        paso_actual=6,
    )

