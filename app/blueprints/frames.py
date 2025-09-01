# app/blueprints/frames.py
# El flujo de captura dividido en frames 1..5 y 'finalizar'.
# Incluye validaciones, gestión de sesión y nombres de claves consistentes.

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
import psycopg2
from ..db_legacy import fetchall, fetchone, execute
from ..utils.session_utils import limpiar_dependientes, hay_dependientes, normalizar_unidad
from ..auth.decorators import login_required
# Ejemplo al finalizar frame2:

frames_bp = Blueprint("frames", __name__)

def _upper(s): return (s or "").upper()
def _strip(s): return (s or "").strip()

@frames_bp.before_request
@login_required
def _guard_frames():
    pass

# ==== Normalizadores comunes para TODOS los frames ====
def _v(s: str | None) -> str:
    return (s or "").strip()

def _upper(s: str | None) -> str:
    return _v(s).upper()

def _digits(s: str | None, maxlen: int | None = None) -> str:
    only = "".join(ch for ch in _v(s) if ch.isdigit())
    return only[:maxlen] if maxlen else only

def _bool_checkbox(val: str | None) -> bool:
    return bool(val in ("1", "true", "on", "yes", "si", "SI", "True", True))

# ==== Mapea y guarda frame1 en sesión ====
def save_frame1_from_form(form):
    tipo_tramite   = _upper(form.get("tipo_tramite"))
    numero_cliente = _digits(form.get("numero_cliente"), 9)
    numero_contrato= _digits(form.get("numero_contrato"), 12) if tipo_tramite != "ALTA" else "-"
    data = {
        "tipo_tramite": tipo_tramite,
        "nombre_ejecutivo": _upper(form.get("nombre_ejecutivo")),
        "segmento": _upper(form.get("segmento")),
        "numero_cliente": int(numero_cliente) if numero_cliente else None,
        "tipo_persona": _upper(form.get("tipo_persona")),
        "razon_social": _upper(form.get("razon_social")),
        "apoderado_legal": _upper(form.get("apoderado_legal")),
        "correo_apoderado_legal": _v(form.get("correo_apoderado_legal")),
        "tipo_contrato": _upper(form.get("tipo_contrato")),
        "tipo_servicio": _upper(form.get("tipo_servicio")),
        "tipo_cobro": _upper(form.get("tipo_cobro")),
        "importe_maximo_dif": _upper(form.get("importe_maximo_dif")) or "-",
        "numero_contrato": numero_contrato or "-",
        "telefono_cliente": _digits(form.get("telefono_cliente"), 15),
        "domicilio_cliente": _upper(form.get("domicilio_cliente")),
    }
    from datetime import datetime
    data.setdefault("fecha_solicitud", datetime.now().isoformat())
    session["rdc_reporte"] = (data["tipo_cobro"] == "CENTRALIZADO")
    session["frame1"] = data
    session.modified = True

# ==== Normaliza una UNIDAD desde form ====
def normalize_unidad_from_form(form):
    return {
        "cpae": _v(form.get("cpae")),
        "cpae_nombre": _upper(form.get("cpae_nombre")),
        "tipo_servicio_unidad": _upper(form.get("tipo_servicio_unidad")),
        "empresa_traslado": _v(form.get("empresa_traslado")),
        "etv_nombre": _upper(form.get("etv_nombre")),
        "calle_numero": _upper(form.get("calle_numero")),
        "colonia": _upper(form.get("colonia")),
        "municipio_id": int(_digits(form.get("municipio_id"), 6)) if form.get("municipio_id") else None,
        "municipio_nombre": _upper(form.get("municipio_nombre")),
        "estado": int(_digits(form.get("estado"), 3)) if form.get("estado") else None,
        "estado_nombre": _upper(form.get("estado_nombre")),
        "codigo_postal": _digits(form.get("codigo_postal"), 5),
        "nombre_unidad": _upper(form.get("nombre_unidad")),
        "numero_terminal_sef": _v(form.get("numero_terminal_sef")),
        "terminal_integradora": _v(form.get("terminal_integradora")),
        "terminal_dotacion_centralizada": _v(form.get("terminal_dotacion_centralizada")),
        "terminal_certificado_centralizada": _v(form.get("terminal_certificado_centralizada")),
        # compatibilidad con inserción BD:
        "tipo_cobro": session.get("frame1", {}).get("tipo_cobro"),
        "servicio": session.get("frame1", {}).get("tipo_servicio"),
        "tipo_unidad": _upper(form.get("tipo_servicio_unidad")),
        "tipo_servicio": _upper(form.get("tipo_servicio_unidad")),
        "empresa_traslado": _v(form.get("empresa_traslado")),
    }

# ==== Normaliza CUENTA desde form ====
def normalize_cuenta_from_form(form):
    return {
        "servicio": _upper(form.get("servicio")),
        "sucursal": _digits(form.get("sucursal"), 5),
        "cuenta": _digits(form.get("cuenta"), 20),
        "moneda": _upper(form.get("moneda")),
        "terminal_aplica": _v(form.get("terminal_aplica")),
    }

# ==== Normaliza USUARIO desde form ====
def normalize_usuario_from_form(form):
    return {
        "tipo_usuario": _upper(form.get("tipo_usuario")),
        "terminal_aplica": _v(form.get("terminal_aplica")),
        "numero_terminal_sef": _v(form.get("numero_terminal_sef")),  # por compatibilidad, si lo usas
        "nombre_usuario": _upper(form.get("nombre_usuario")),
        "clave_usuario": _upper(form.get("clave_usuario")),
        "perfil": _upper(form.get("perfil")),
        "maker_checker": _upper(form.get("maker_checker")),
        "correo": _v(form.get("correo")),
        "telefono": _digits(form.get("telefono"), 15),
        "monto_mxn": _digits(form.get("monto_mxn"), 12),
        "monto_usd": _digits(form.get("monto_usd"), 12),
    }

# ==== Normaliza CONTACTO desde form ====
def normalize_contacto_from_form(form):
    # tipos_contacto puede venir en lista
    tipos = form.getlist("tipos_contacto") if hasattr(form, "getlist") else (form.get("tipos_contacto") or [])
    return {
        "numero_terminal_sef": _v(form.get("numero_terminal_sef")) or None,
        "nombre_contacto": _upper(form.get("nombre_contacto")),
        "telefono": _digits(form.get("telefono"), 15),
        "correo": _v(form.get("correo")),
        "tipos_contacto": tipos,
    }

# ==== Firmantes en sesión (para finalizar / exportar) ====
def save_firmantes_from_form(form):
    session["firmantes"] = {
        "apoderado_legal": _upper(form.get("apoderado_legal")),
        "nombre_autorizador": _upper(form.get("nombre_autorizador")),
        "puesto_autorizador": _upper(form.get("puesto_autorizador")),
        "nombre_director_divisional": _upper(form.get("nombre_director_divisional")),
        "puesto_director_divisional": _upper(form.get("puesto_director_divisional")),
        "fecha_firma": _v(form.get("fecha_firma")),  # dd/mm/aaaa o yyyy-mm-dd (se normaliza al exportar)
    }
    session.modified = True

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
        frame1_prev = session.get("frame1_prev") or {}
        f1 = session["frame1"]
        if frame1_prev and any((
            f1["tipo_tramite"]  != frame1_prev.get("tipo_tramite"),
            f1["tipo_contrato"] != frame1_prev.get("tipo_contrato"),
            f1["tipo_servicio"] != frame1_prev.get("tipo_servicio"),
        )):
            from ..utils.session_utils import limpiar_dependientes
            limpiar_dependientes()
        session["frame1_prev"] = f1.copy()
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

@frames_bp.route("/terminar", methods=["GET","POST"])
def finalizar():
    if request.method == "POST":
        if "regresar_frame5" in request.form:
            return redirect(url_for("frames.frame5"))

        if "confirmar" in request.form:
            try:
                from ..db_legacy import conectar
                f1 = session["frame1"]
                firm = session.get("firmantes", {})  # ← ahora siempre vive en sesión también
                unidades = session.get("unidades", [])
                cuentas  = session.get("cuentas", [])
                usuarios = session.get("usuarios", [])
                contactos= session.get("contactos", [])

                editing_id = session.get("editing_solicitud_id")
                now = datetime.now()

                with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    if editing_id:
                        # -------- UPDATE SOLICITUD EXISTENTE --------
                        cur.execute("""
                            UPDATE solicitudes SET
                                numero_cliente = %s,
                                numero_contrato = %s,
                                razon_social = %s,
                                segmento = %s,
                                tipo_persona = %s,
                                tipo_tramite = %s,
                                tipo_contrato = %s,
                                tipo_servicio = %s,
                                tipo_cobro = %s,
                                paso_actual = %s,
                                -- firmantes
                                apoderado_legal = %s,
                                nombre_autorizador = %s,
                                nombre_director_divisional = %s,
                                puesto_autorizador = %s,
                                puesto_director_divisional = %s,
                                fecha_firma = %s,
                                -- fechas
                                fecha_solicitud = %s,
                                updated_at = %s
                            WHERE id=%s
                        """, (
                            f1["numero_cliente"], f1.get("numero_contrato","-"), f1["razon_social"],
                            f1.get("segmento"), f1.get("tipo_persona"), f1.get("tipo_tramite"),
                            f1.get("tipo_contrato"), f1.get("tipo_servicio"), f1.get("tipo_cobro"),
                            f1.get("paso_actual", 6),
                            # firmantes
                            (firm.get("apoderado_legal") or "").strip(),
                            (firm.get("nombre_autorizador") or "").strip(),
                            (firm.get("nombre_director_divisional") or "").strip(),
                            (firm.get("puesto_autorizador") or "").strip(),
                            (firm.get("puesto_director_divisional") or "").strip(),
                            (firm.get("fecha_firma") or None),
                            # fechas
                            now, now,
                            editing_id
                        ))

                        # Borra hijos y re-inserta (más simple y consistente)
                        cur.execute("DELETE FROM unidades WHERE solicitud_id=%s", (editing_id,))
                        cur.execute("DELETE FROM cuentas  WHERE solicitud_id=%s", (editing_id,))
                        cur.execute("DELETE FROM usuarios WHERE solicitud_id=%s", (editing_id,))
                        cur.execute("DELETE FROM contactos WHERE solicitud_id=%s", (editing_id,))
                        solicitud_id = editing_id
                    else:
                        # -------- INSERT NUEVO --------
                        cur.execute("""
                            INSERT INTO solicitudes (
                                numero_cliente, numero_contrato, razon_social, segmento,
                                tipo_persona, tipo_tramite, tipo_contrato, tipo_servicio, tipo_cobro,
                                fecha_solicitud, paso_actual, created_by,
                                -- firmantes
                                apoderado_legal, nombre_autorizador, nombre_director_divisional,
                                puesto_autorizador, puesto_director_divisional, fecha_firma
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            RETURNING id
                        """, (
                            f1["numero_cliente"], f1.get("numero_contrato","-"), f1["razon_social"], f1.get("segmento"),
                            f1.get("tipo_persona"), f1.get("tipo_tramite"), f1.get("tipo_contrato"),
                            f1.get("tipo_servicio"), f1.get("tipo_cobro"),
                            now, f1.get("paso_actual", 6), session.get("user_id"),
                            # firmantes
                            (firm.get("apoderado_legal") or "").strip(),
                            (firm.get("nombre_autorizador") or "").strip(),
                            (firm.get("nombre_director_divisional") or "").strip(),
                            (firm.get("puesto_autorizador") or "").strip(),
                            (firm.get("puesto_director_divisional") or "").strip(),
                            (firm.get("fecha_firma") or None),
                        ))
                        solicitud_id = cur.fetchone()["id"]
                        session["editing_solicitud_id"] = solicitud_id  # queda en modo edición

                    # -------- Hijos: reinsertar --------
                    for u in unidades:
                        cur.execute("""
                            INSERT INTO unidades
                            (solicitud_id, nombre_unidad, cpae_nombre, tipo_servicio_unidad, etv_nombre,
                             numero_terminal_sef, calle_numero, colonia, municipio_nombre, estado_nombre,
                             codigo_postal, terminal_integradora, terminal_dotacion_centralizada,
                             terminal_certificado_centralizada, tipo_cobro, servicio, tipo_unidad,
                             cpae, tipo_servicio, empresa_traslado, municipio_id, estado)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id, u.get("nombre_unidad"), u.get("cpae_nombre"), u.get("tipo_servicio_unidad"),
                            u.get("etv_nombre"), u.get("numero_terminal_sef"), u.get("calle_numero"),
                            u.get("colonia"), u.get("municipio_nombre"), u.get("estado_nombre"),
                            u.get("codigo_postal"), u.get("terminal_integradora"),
                            u.get("terminal_dotacion_centralizada"), u.get("terminal_certificado_centralizada"),
                            u.get("tipo_cobro"), u.get("servicio"), u.get("tipo_unidad"), u.get("cpae"),
                            u.get("tipo_servicio"), u.get("empresa_traslado"),
                            u.get("municipio_id"), u.get("estado"),
                        ))

                    for c in cuentas:
                        cur.execute("""
                            INSERT INTO cuentas
                            (solicitud_id, servicio, numero_sucursal, numero_cuenta, moneda, terminal_aplicable)
                            VALUES (%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id, c.get("servicio"), c.get("sucursal"), c.get("cuenta"),
                            c.get("moneda"), c.get("terminal_aplica"),
                        ))

                    for u in usuarios:
                        cur.execute("""
                            INSERT INTO usuarios
                            (solicitud_id, tipo_usuario, numero_terminal_sef, nombre_usuario,
                             clave_usuario, perfil, maker_checker, correo, telefono,
                             role, terminal_aplica, monto_maximo_pesos, monto_maximo_dolares)
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'user',%s,%s,%s)
                        """, (
                            solicitud_id, u.get("tipo_usuario"),
                            (u.get("numero_terminal_sef") or u.get("terminal_aplica")),
                            u.get("nombre_usuario"), u.get("clave_usuario"), u.get("perfil"),
                            u.get("maker_checker"), u.get("correo"), u.get("telefono"),
                            u.get("terminal_aplica"), u.get("monto_mxn"), u.get("monto_usd"),
                        ))

                    for c in contactos:
                        # tipos_contacto puede venir como lista; conviértelo a texto
                        tipos = c.get("tipos_contacto")
                        if isinstance(tipos, (list, tuple)):
                            tipos = ", ".join([str(x) for x in tipos])
                        cur.execute("""
                            INSERT INTO contactos
                            (solicitud_id, numero_terminal_sef, nombre, telefono, correo, tipo_contacto)
                            VALUES (%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id, c.get("numero_terminal_sef"),
                            c.get("nombre_contacto"), c.get("telefono"), c.get("correo"), tipos
                        ))

                flash("Solicitud guardada.", "success")
                return redirect(url_for("frames.finalizar"))

            except Exception as e:
                flash(f"Error BD: {e}", "danger")

    # GET: sólo renderiza finalizar.html (ya con sesión cargada)
    return render_template(
        "finalizar.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        firmantes=session.get("firmantes", {}),  # ← pásalos al template
        paso_actual=6,
        es_edicion=bool(session.get("editing_solicitud_id")),
    )


