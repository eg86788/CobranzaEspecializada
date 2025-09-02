# app/blueprints/frames.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import psycopg2
try:
    from ..db_legacy import fetchall, fetchone, conectar
except Exception:
    from app.db_legacy import fetchall, fetchone, conectar  # pragma: no cover

frames_bp = Blueprint("frames", __name__)

# -------------------- Helpers de normalización --------------------
def _upper(s): return (s or "").upper()
def _v(s): return (s or "").strip()
def _digits(s, maxlen=None):
    s = (s or "")
    only = "".join(ch for ch in s if ch.isdigit())
    return only[:maxlen] if maxlen else only

def limpiar_dependientes():
    """Limpia colecciones dependientes de frame1 al cambiar configuración clave."""
    session.pop("unidades", None)
    session.pop("cuentas", None)
    session.pop("usuarios", None)
    session.pop("contactos", None)
    session.modified = True

def hay_dependientes():
    return any((session.get("unidades"), session.get("cuentas"),
                session.get("usuarios"), session.get("contactos")))

from datetime import datetime, date

def _parse_fecha_dmy(s):
    """Convierte 'dd/mm/aaaa' a date. Devuelve None si es inválida o vacía."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        d, m, y = s.split("/")
        return date(int(y), int(m), int(d))
    except Exception:
        return None


# -------------------- FRAME 1 --------------------
@frames_bp.route("/solicitud_sef", methods=["GET", "POST"])
def frame1():
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    if request.method == "POST":
        datos = {k: _v(request.form.get(k)) for k in (
            "tipo_tramite","nombre_ejecutivo","segmento","numero_cliente","tipo_persona",
            "razon_social","apoderado_legal","correo_apoderado_legal","tipo_contrato",
            "tipo_servicio","tipo_cobro","importe_maximo_dif","numero_contrato",
            "telefono_cliente","domicilio_cliente"
        )}

        # Reglas mínimas
        if (datos.get("tipo_tramite") or "").upper() == "ALTA":
            datos["numero_contrato"] = "-"
        elif not datos.get("numero_contrato"):
            flash("El número de contrato es obligatorio para sustitución.", "danger")
            return redirect(url_for("frames.frame1"))

        obligatorios = ("tipo_tramite","nombre_ejecutivo","segmento","numero_cliente",
                        "razon_social","apoderado_legal","correo_apoderado_legal",
                        "tipo_persona","tipo_contrato","tipo_servicio","tipo_cobro")
        if not all(datos.get(k) for k in obligatorios):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("frames.frame1"))

        # Si cambian llaves clave → limpiar dependientes
        f1_prev = session.get("frame1") or {}
        if f1_prev and any((
            (datos.get("tipo_tramite") or "").upper()  != (f1_prev.get("tipo_tramite") or ""),
            (datos.get("tipo_contrato") or "").upper() != (f1_prev.get("tipo_contrato") or ""),
            (datos.get("tipo_servicio") or "").upper() != (f1_prev.get("tipo_servicio") or ""),
        )):
            limpiar_dependientes()
            session["frame1_prev"] = f1_prev.copy()
            flash("Se limpiaron Unidades/Cuentas/Usuarios/Contactos por cambio de configuración.", "warning")

        if not datos.get("importe_maximo_dif"):
            datos["importe_maximo_dif"] = "-"

        session["rdc_reporte"] = (datos.get("tipo_cobro") == "CENTRALIZADO")
        # ⚠️ numero_cliente es VARCHAR en tu BD → lo almacenamos como string
        session["frame1"] = {
            **datos,
            "fecha_solicitud": datetime.now().date().isoformat(),  # tu BD tiene date para fecha_solicitud
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

# -------------------- FRAME 2 (Unidades) --------------------
@frames_bp.route("/unidades", methods=["GET", "POST"])
def frame2():
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    if request.method == "POST":
        if "regresar_frame1" in request.form:
            return redirect(url_for("frames.frame1"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            unidades = session.get("unidades", [])
            if 0 <= idx < len(unidades):
                unidades.pop(idx)
                session["unidades"] = unidades
                flash("Unidad eliminada.", "info")
            return redirect(url_for("frames.frame2"))

        # Validación mínima
        obligatorios = ("cpae", "nombre_unidad", "calle_numero", "tipo_servicio_unidad")
        faltantes = [k for k in obligatorios if not _v(request.form.get(k))]
        if faltantes:
            from markupsafe import escape
            faltantes = [escape(f) for f in faltantes]
            flash(f"Faltan campos: {', '.join(faltantes)}", "danger")
            return redirect(url_for("frames.frame2"))

        u = {
            "cpae": _v(request.form.get("cpae")),
            "cpae_nombre": _upper(request.form.get("cpae_nombre")),
            "tipo_servicio_unidad": _upper(request.form.get("tipo_servicio_unidad")),
            "etv_nombre": _upper(request.form.get("empresa_traslado")),  # en tu BD se llama etv_nombre
            "empresa_traslado": _v(request.form.get("empresa_traslado")),
            "frecuencia_traslado": _v(request.form.get("frecuencia_traslado")),
            "horario_inicio": _v(request.form.get("horario_inicio")),
            "horario_fin": _v(request.form.get("horario_fin")),
            "direccion": _upper(request.form.get("direccion")),
            "entre_calles": _upper(request.form.get("entre_calles")),
            "calle_numero": _upper(request.form.get("calle_numero")),
            "colonia": _upper(request.form.get("colonia")),
            "municipio_id": int(_digits(request.form.get("municipio_id"), 6)) if request.form.get("municipio_id") else None,
            "municipio_nombre": _upper(request.form.get("municipio_nombre")),
            "estado": int(_digits(request.form.get("estado"), 3)) if request.form.get("estado") else None,
            "estado_nombre": _upper(request.form.get("estado_nombre")),
            "codigo_postal": _digits(request.form.get("codigo_postal"), 16),
            "nombre_unidad": _upper(request.form.get("nombre_unidad")),
            "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
            "terminal_integradora": _v(request.form.get("terminal_integradora")),
            "terminal_dotacion_centralizada": _v(request.form.get("terminal_dotacion_centralizada")),
            "terminal_certificado_centralizada": _v(request.form.get("terminal_certificado_centralizada")),
            # Compat con tus columnas espejo:
            "tipo_cobro": session.get("frame1", {}).get("tipo_cobro"),
            "servicio": session.get("frame1", {}).get("tipo_servicio"),
            "tipo_unidad": _upper(request.form.get("tipo_servicio_unidad")),
            "tipo_servicio": _upper(request.form.get("tipo_servicio_unidad")),
        }
        unidades = session.get("unidades", [])
        unidades.append(u)
        session["unidades"] = unidades
        flash("Unidad agregada.", "success")
        return redirect(url_for("frames.frame2"))

    return render_template(
        "frame2.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        paso_actual=2,
        catalogo_cpae=catalogo_cpae,
        catalogo_etv=catalogo_etv,
        catalogo_estados=catalogo_estados
    )

# Endpoint para Municipios (depende de estado)
@frames_bp.get("/api/municipios")
def api_municipios():
    estado_id = request.args.get("estado_id")
    if not estado_id or not estado_id.isdigit():
        return jsonify({"ok": False, "error": "estado_id inválido"}), 400
    rows = fetchall(
        "SELECT id, nombre FROM catalogo_municipios WHERE estado_id = %s ORDER BY nombre",
        (int(estado_id),)
    ) or []
    return jsonify({"ok": True, "data": rows})

# -------------------- FRAME 3 (Cuentas) --------------------
@frames_bp.route("/cuentas", methods=["GET", "POST"])
def frame3():
    """
    Usa los nombres de campos de tu BD:
    cuentas(solicitud_id, servicio, sucursal, cuenta, moneda, terminal_aplica,
            numero_sucursal, numero_cuenta, terminal_aplicable)
    """
    if request.method == "POST":
        if "regresar_frame1" in request.form:
            return redirect(url_for("frames.frame1"))
        if "regresar_frame2" in request.form:
            return redirect(url_for("frames.frame2"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            cuentas = session.get("cuentas", [])
            if 0 <= idx < len(cuentas):
                cuentas.pop(idx)
                session["cuentas"] = cuentas
                flash("Cuenta eliminada.", "info")
            return redirect(url_for("frames.frame3"))

        # Captura flexible según tu template
        cta = {
            "servicio": _upper(request.form.get("servicio")),
            "sucursal": _v(request.form.get("sucursal")),
            "cuenta": _v(request.form.get("cuenta")),
            "moneda": _upper(request.form.get("moneda")),
            "terminal_aplica": _v(request.form.get("terminal_aplica")),  # puede ser índice o nombre de unidad
            "numero_sucursal": int(_digits(request.form.get("numero_sucursal"))) if _digits(request.form.get("numero_sucursal")) else None,
            "numero_cuenta": int(_digits(request.form.get("numero_cuenta"))) if _digits(request.form.get("numero_cuenta")) else None,
            "terminal_aplicable": _v(request.form.get("terminal_aplicable")),
        }
        cuentas = session.get("cuentas", [])
        cuentas.append(cta)
        session["cuentas"] = cuentas
        flash("Cuenta agregada.", "success")
        return redirect(url_for("frames.frame3"))

    unidades = session.get("unidades", [])
    catalogo_unidades = [
        {"idx": i, "nombre": (u.get("nombre_unidad") or f"Unidad {i+1}")} for i, u in enumerate(unidades)
    ]
    return render_template(
        "frame3.html",
        frame1=session.get("frame1"),
        cuentas=session.get("cuentas", []),
        unidades=unidades,
        catalogo_unidades=catalogo_unidades,
        paso_actual=3
    )

# -------------------- FRAME 4 (Usuarios SEF) --------------------
@frames_bp.route("/usuarios", methods=["GET", "POST"])
def frame4():
    """
    usuarios(solicitud_id, nombre_usuario, clave_usuario, perfil, maker_checker,
             correo, telefono, terminal_aplica, tipo_usuario, numero_terminal_sef, role)
    """
    if request.method == "POST":
        if "regresar_frame3" in request.form:
            return redirect(url_for("frames.frame3"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            usuarios = session.get("usuarios", [])
            if 0 <= idx < len(usuarios):
                usuarios.pop(idx)
                session["usuarios"] = usuarios
                flash("Usuario eliminado.", "info")
            return redirect(url_for("frames.frame4"))

        # Acepta campos tal como tu template los mande
        perfiles_list = request.form.getlist("perfiles") or []
        usuario = {
            "nombre_usuario": _upper(request.form.get("nombre_usuario") or request.form.get("nombre")),
            "clave_usuario": _v(request.form.get("clave_usuario")),
            "perfil": _upper(request.form.get("perfil") or ",".join(perfiles_list)),
            "maker_checker": _upper(request.form.get("maker_checker")),
            "correo": _v(request.form.get("correo")),
            "telefono": _v(request.form.get("telefono")),
            "terminal_aplica": _v(request.form.get("terminal_aplica")),
            "tipo_usuario": _upper(request.form.get("tipo_usuario")),
            "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
            "role": _upper(request.form.get("role") or "USER"),
        }
        usuarios = session.get("usuarios", [])
        usuarios.append(usuario)
        session["usuarios"] = usuarios
        flash("Usuario agregado.", "success")
        return redirect(url_for("frames.frame4"))

    return render_template(
        "frame4.html",
        frame1=session.get("frame1"),
        usuarios=session.get("usuarios", []),
        paso_actual=4
    )

# -------------------- FRAME 5 (Contactos) --------------------
@frames_bp.route("/contactos", methods=["GET", "POST"])
def frame5():
    """
    contactos(solicitud_id, nombre_contacto, correo, telefono, numero_terminal_sef, tipos_contacto)
    """
    if request.method == "POST":
        if "regresar_frame4" in request.form:
            return redirect(url_for("frames.frame4"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            contactos = session.get("contactos", [])
            if 0 <= idx < len(contactos):
                contactos.pop(idx)
                session["contactos"] = contactos
                flash("Contacto eliminado.", "info")
            return redirect(url_for("frames.frame5"))

        tipos = request.form.getlist("tipos_contacto") or []
        contacto = {
            "nombre_contacto": _upper(request.form.get("nombre_contacto") or request.form.get("nombre")),
            "correo": _v(request.form.get("correo")),
            "telefono": _v(request.form.get("telefono")),
            "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
            "tipos_contacto": ",".join(tipos),
        }
        contactos = session.get("contactos", [])
        contactos.append(contacto)
        session["contactos"] = contactos
        flash("Contacto agregado.", "success")
        return redirect(url_for("frames.frame5"))

    return render_template(
        "frame5.html",
        frame1=session.get("frame1"),
        contactos=session.get("contactos", []),
        paso_actual=5
    )

# -------------------- FINALIZAR --------------------
@frames_bp.route("/finalizar", methods=["GET", "POST"])
def finalizar():
    if request.method == "POST":
        if "regresar_frame5" in request.form:
            return redirect(url_for("frames.frame5"))

        if "confirmar" in request.form:
            try:
                f1 = session["frame1"]
                unidades = session.get("unidades", [])
                cuentas  = session.get("cuentas", [])
                usuarios = session.get("usuarios", [])
                contactos= session.get("contactos", [])
                editing_id = session.get("editing_solicitud_id")
                now = datetime.now()

                from psycopg2.extras import RealDictCursor
                with conectar() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if editing_id:
                        # UPDATE solicitudes (solo columnas que existen en tu tabla)
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
                                importe_maximo_dif = %s,
                                nombre_ejecutivo = %s,
                                domicilio_cliente = %s,
                                telefono_cliente = %s,
                                rdc_reporte = %s,
                                fecha_solicitud = %s,
                                updated_at = %s,
                                paso_actual = %s
                            WHERE id = %s
                        """, (
                            f1.get("numero_cliente"), f1.get("numero_contrato"),
                            f1.get("razon_social"), f1.get("segmento"),
                            f1.get("tipo_persona"), f1.get("tipo_tramite"),
                            f1.get("tipo_contrato"), f1.get("tipo_servicio"),
                            f1.get("tipo_cobro"), f1.get("importe_maximo_dif"),
                            f1.get("nombre_ejecutivo"), f1.get("domicilio_cliente"),
                            f1.get("telefono_cliente"), session.get("rdc_reporte", False),
                            f1.get("fecha_solicitud"), now, 6,
                            editing_id
                        ))
                        solicitud_id = editing_id
                    else:
                        # INSERT solicitudes (usa nombres de tu tabla)
                        cur.execute("""
                            INSERT INTO solicitudes (
                                numero_cliente, razon_social, segmento, domicilio_cliente,
                                numero_contrato, tipo_tramite, tipo_contrato, tipo_servicio,
                                tipo_cobro, importe_maximo_dif, nombre_ejecutivo,
                                rdc_reporte, created_at, servicio_solicitado,
                                fecha_solicitud, estatus, tipo_persona, created_by,
                                updated_at, paso_actual, telefono_cliente, apoderado_legal
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now(),%s,%s,%s,%s,%s,now(),%s,%s,%s)
                            RETURNING id
                        """, (
                            f1.get("numero_cliente"), f1.get("razon_social"), f1.get("segmento"), f1.get("domicilio_cliente"),
                            f1.get("numero_contrato"), f1.get("tipo_tramite"), f1.get("tipo_contrato"), f1.get("tipo_servicio"),
                            f1.get("tipo_cobro"), f1.get("importe_maximo_dif"), f1.get("nombre_ejecutivo"),
                            session.get("rdc_reporte", False),
                            f1.get("servicio_solicitado") or "",  # opcional
                            f1.get("fecha_solicitud"), f1.get("estatus") or "CAPTURADA",
                            f1.get("tipo_persona"), session.get("user_id"),
                            6, f1.get("telefono_cliente"), f1.get("apoderado_legal")
                        ))
                        solicitud_id = cur.fetchone()["id"]

                    # -------- UNIDADES --------
                    cur.execute("DELETE FROM unidades WHERE solicitud_id = %s", (solicitud_id,))
                    for u in unidades:
                        cur.execute("""
                            INSERT INTO unidades (
                                solicitud_id, nombre_unidad, cpae_nombre, tipo_servicio_unidad,
                                etv_nombre, numero_terminal_sef, calle_numero, colonia,
                                municipio_nombre, estado_nombre, codigo_postal,
                                terminal_integradora, terminal_dotacion_centralizada, terminal_certificado_centralizada,
                                tipo_cobro, servicio, tipo_unidad, cpae, tipo_servicio,
                                empresa_traslado, municipio_id, estado
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            u.get("nombre_unidad"),
                            u.get("cpae_nombre"),
                            u.get("tipo_servicio_unidad"),
                            u.get("etv_nombre") or u.get("empresa_traslado"),
                            u.get("numero_terminal_sef"),
                            u.get("calle_numero"),
                            u.get("colonia"),
                            u.get("municipio_nombre"),
                            u.get("estado_nombre"),
                            u.get("codigo_postal"),
                            u.get("terminal_integradora"),
                            u.get("terminal_dotacion_centralizada"),
                            u.get("terminal_certificado_centralizada"),
                            u.get("tipo_cobro"),
                            u.get("servicio"),
                            u.get("tipo_unidad"),
                            u.get("cpae"),
                            u.get("tipo_servicio"),
                            u.get("empresa_traslado"),
                            u.get("municipio_id"),
                            u.get("estado"),
                        ))

                    # -------- CUENTAS --------
                    cur.execute("DELETE FROM cuentas WHERE solicitud_id = %s", (solicitud_id,))
                    for c in cuentas:
                        cur.execute("""
                            INSERT INTO cuentas (
                                solicitud_id, servicio, sucursal, cuenta, moneda,
                                terminal_aplica, numero_sucursal, numero_cuenta, terminal_aplicable
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            c.get("servicio"),
                            c.get("sucursal"),
                            c.get("cuenta"),
                            c.get("moneda"),
                            c.get("terminal_aplica"),
                            c.get("numero_sucursal"),
                            c.get("numero_cuenta"),
                            c.get("terminal_aplicable"),
                        ))

                    # -------- USUARIOS --------
                    cur.execute("DELETE FROM usuarios WHERE solicitud_id = %s", (solicitud_id,))
                    for u in usuarios:
                        cur.execute("""
                            INSERT INTO usuarios (
                                solicitud_id, nombre_usuario, clave_usuario, perfil, maker_checker,
                                correo, telefono, terminal_aplica, tipo_usuario, numero_terminal_sef, role
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            u.get("nombre_usuario") or u.get("nombre"),
                            u.get("clave_usuario"),
                            u.get("perfil"),
                            u.get("maker_checker"),
                            u.get("correo"),
                            u.get("telefono"),
                            u.get("terminal_aplica"),
                            u.get("tipo_usuario"),
                            u.get("numero_terminal_sef"),
                            u.get("role") or "USER",
                        ))

                    # -------- CONTACTOS --------
                    cur.execute("DELETE FROM contactos WHERE solicitud_id = %s", (solicitud_id,))
                    for c in contactos:
                        cur.execute("""
                            INSERT INTO contactos (
                                solicitud_id, nombre_contacto, correo, telefono, numero_terminal_sef, tipos_contacto
                            ) VALUES (%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            c.get("nombre_contacto") or c.get("nombre"),
                            c.get("correo"),
                            c.get("telefono"),
                            c.get("numero_terminal_sef"),
                            c.get("tipos_contacto") if isinstance(c.get("tipos_contacto"), str)
                                else ",".join(c.get("tipos_contacto") or []),
                        ))

                session.pop("editing_solicitud_id", None)
              #  flash("Solicitud guardada correctamente.", "success")
                return redirect(url_for("solicitudes_portal.lista"))
            except Exception as e:
                flash(f"Error al guardar la solicitud: {str(e)}", "danger")
                return redirect(url_for("frames.finalizar"))

    # GET finalizar
    return render_template(
        "finalizar.html",
        frame1=session.get("frame1") or {},
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        paso_actual=6
    )
# app/blueprints/frames.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime
import psycopg2
try:
    from ..db_legacy import fetchall, fetchone, conectar
except Exception:
    from app.db_legacy import fetchall, fetchone, conectar  # pragma: no cover

frames_bp = Blueprint("frames", __name__)

# -------------------- Helpers de normalización --------------------
def _upper(s): return (s or "").upper()
def _v(s): return (s or "").strip()
def _digits(s, maxlen=None):
    s = (s or "")
    only = "".join(ch for ch in s if ch.isdigit())
    return only[:maxlen] if maxlen else only

def limpiar_dependientes():
    """Limpia colecciones dependientes de frame1 al cambiar configuración clave."""
    session.pop("unidades", None)
    session.pop("cuentas", None)
    session.pop("usuarios", None)
    session.pop("contactos", None)
    session.modified = True

def hay_dependientes():
    return any((session.get("unidades"), session.get("cuentas"),
                session.get("usuarios"), session.get("contactos")))

# -------------------- FRAME 1 --------------------
@frames_bp.route("/solicitud_sef", methods=["GET", "POST"])
def frame1():
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    if request.method == "POST":
        datos = {k: _v(request.form.get(k)) for k in (
            "tipo_tramite","nombre_ejecutivo","segmento","numero_cliente","tipo_persona",
            "razon_social","apoderado_legal","correo_apoderado_legal","tipo_contrato",
            "tipo_servicio","tipo_cobro","importe_maximo_dif","numero_contrato",
            "telefono_cliente","domicilio_cliente"
        )}

        # Reglas mínimas
        if (datos.get("tipo_tramite") or "").upper() == "ALTA":
            datos["numero_contrato"] = "-"
        elif not datos.get("numero_contrato"):
            flash("El número de contrato es obligatorio para sustitución.", "danger")
            return redirect(url_for("frames.frame1"))

        obligatorios = ("tipo_tramite","nombre_ejecutivo","segmento","numero_cliente",
                        "razon_social","apoderado_legal","correo_apoderado_legal",
                        "tipo_persona","tipo_contrato","tipo_servicio","tipo_cobro")
        if not all(datos.get(k) for k in obligatorios):
            flash("Todos los campos son obligatorios.", "danger")
            return redirect(url_for("frames.frame1"))
        
                # --- Regla: si cambia el Tipo de Cobro, elimina contactos incompatibles ---
        try:
            prev_cobro  = ((session.get("frame1") or {}).get("tipo_cobro") or "").upper()
            nuevo_cobro = (datos.get("tipo_cobro") or "").upper()

            if prev_cobro and nuevo_cobro and prev_cobro != nuevo_cobro:
                contactos = session.get("contactos", []) or []
                eliminados = 0
                resultado = []

                def truthy(v):
                    return str(v).strip().upper() in ("SI", "TRUE", "1")

                def norm(s):
                    return (s or "").strip().upper()

                def es_local_label(lbl):
                    n = norm(lbl)
                    return ("LOCAL" in n) or ("DIFERENCIAS LOCALES" in n)

                def es_central_label(lbl):
                    n = norm(lbl)
                    return ("CENTRAL" in n) or ("DIFERENCIAS CENTRALES" in n)

                for c in contactos:
                    fl_local    = truthy(c.get("contacto_diferencias_locales"))
                    fl_central  = truthy(c.get("contacto_diferencias_centrales"))
                    labels      = [x.strip() for x in str(c.get("tipos_contacto") or "").split(",") if x.strip()]

                    incompatible = False
                    if prev_cobro == "CENTRALIZADO" and nuevo_cobro == "LOCAL":
                        # Cualquier indicio de "diferencias centrales" lo hace incompatible
                        incompatible = fl_central or any(es_central_label(lbl) for lbl in labels)
                    elif prev_cobro == "LOCAL" and nuevo_cobro == "CENTRALIZADO":
                        # Cualquier indicio de "diferencias locales" lo hace incompatible
                        incompatible = fl_local or any(es_local_label(lbl) for lbl in labels)

                    if incompatible:
                        eliminados += 1
                        continue  # no se conserva el contacto

                    resultado.append(c)

                if eliminados:
                    session["contactos"] = resultado
                    session.modified = True
                    flash(
                        f"Se cambió el Tipo de Cobro a {nuevo_cobro}. "
                        f"Se eliminaron {eliminados} contacto(s) incompatibles. "
                        f"Vuelve a capturarlos conforme al nuevo esquema.",
                        "warning"
                    )
        except Exception:
            # No interrumpir flujo si algo falla
            pass


        # Si cambian llaves clave → limpiar dependientes
        f1_prev = session.get("frame1") or {}
        if f1_prev and any((
            (datos.get("tipo_tramite") or "").upper()  != (f1_prev.get("tipo_tramite") or ""),
            (datos.get("tipo_contrato") or "").upper() != (f1_prev.get("tipo_contrato") or ""),
            (datos.get("tipo_servicio") or "").upper() != (f1_prev.get("tipo_servicio") or ""),
        )):
            limpiar_dependientes()
            session["frame1_prev"] = f1_prev.copy()
            flash("Se limpiaron Unidades/Cuentas/Usuarios/Contactos por cambio de configuración.", "warning")

        if not datos.get("importe_maximo_dif"):
            datos["importe_maximo_dif"] = "-"

            

        session["rdc_reporte"] = (datos.get("tipo_cobro") == "CENTRALIZADO")
        # ⚠️ numero_cliente es VARCHAR en tu BD → lo almacenamos como string
        session["frame1"] = {
            **datos,
            "fecha_solicitud": datetime.now().date().isoformat(),  # tu BD tiene date para fecha_solicitud
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

# -------------------- FRAME 2 (Unidades) --------------------
@frames_bp.route("/unidades", methods=["GET", "POST"])
def frame2():
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    # Helper local para obtener la descripción por id (soporta dicts/tuplas/objetos simples)
    def _desc_por_id(rows, id_val, label_key):
        if not id_val and id_val != 0:
            return ""
        for r in rows or []:
            try:
                _id = r.get("id") if isinstance(r, dict) else getattr(r, "id", None)
                _label = (r.get(label_key) if isinstance(r, dict)
                          else getattr(r, label_key, None))
            except Exception:
                _id, _label = None, None
            if str(_id) == str(id_val):
                return str(_label or "")
        return ""

    if request.method == "POST":
        if "regresar_frame1" in request.form:
            return redirect(url_for("frames.frame1"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            unidades = session.get("unidades", [])
            if 0 <= idx < len(unidades):
                unidades.pop(idx)
                session["unidades"] = unidades
                flash("Unidad eliminada.", "info")
            return redirect(url_for("frames.frame2"))

        # Validación mínima
        obligatorios = ("cpae", "nombre_unidad", "tipo_servicio_unidad")
        faltantes = [k for k in obligatorios if not _v(request.form.get(k))]
        if faltantes:
            from markupsafe import escape
            faltantes = [escape(f) for f in faltantes]
            flash(f"Faltan campos: {', '.join(faltantes)}", "danger")
            return redirect(url_for("frames.frame2"))

        # IDs recibidos
        _cpae_id = _v(request.form.get("cpae"))
        _etv_id  = _v(request.form.get("empresa_traslado"))
        _edo_id  = _v(request.form.get("estado"))
        _mun_id  = _v(request.form.get("municipio_id"))

        # Nombres recibidos por ocultos (si vienen)
        _cpae_nombre_form = _upper(request.form.get("cpae_nombre"))
        _etv_nombre_form  = _upper(request.form.get("etv_nombre"))
        _edo_nombre_form  = _upper(request.form.get("estado_nombre"))
        _mun_nombre_form  = _upper(request.form.get("municipio_nombre"))

        # Resolver en servidor si falta alguno
        cpae_nombre = _cpae_nombre_form or _upper(_desc_por_id(catalogo_cpae, _cpae_id, "descripcion"))
        etv_nombre  = _etv_nombre_form  or _upper(_desc_por_id(catalogo_etv,  _etv_id,  "descripcion"))
        estado_nombre = _edo_nombre_form or _upper(_desc_por_id(catalogo_estados, _edo_id, "nombre"))

        municipio_nombre = _mun_nombre_form
        if not municipio_nombre and _mun_id:
            # Resuelve municipio por id desde la BD (independiente del estado)
            rows_mun = fetchall(
                "SELECT nombre FROM catalogo_municipios WHERE id = %s LIMIT 1",
                (int(_digits(_mun_id, 6)),)
            ) or []
            if rows_mun:
                if isinstance(rows_mun[0], dict):
                    municipio_nombre = _upper(rows_mun[0].get("nombre", ""))
                else:
                    # tupla con primer campo nombre
                    municipio_nombre = _upper(rows_mun[0][0] if rows_mun[0] else "")

        u = {
            "cpae": _cpae_id,
            "cpae_nombre": cpae_nombre,  # <-- NOMBRE garantizado
            "tipo_servicio_unidad": _upper(request.form.get("tipo_servicio_unidad")),
            "etv_nombre": etv_nombre,    # <-- NOMBRE garantizado
            "empresa_traslado": _etv_id,
            "frecuencia_traslado": _v(request.form.get("frecuencia_traslado")),
            "horario_inicio": _v(request.form.get("horario_inicio")),
            "horario_fin": _v(request.form.get("horario_fin")),
            "direccion": _upper(request.form.get("direccion")),
            "entre_calles": _upper(request.form.get("entre_calles")),
            "calle_numero": _upper(request.form.get("calle_numero")),
            "colonia": _upper(request.form.get("colonia")),
            "municipio_id": int(_digits(request.form.get("municipio_id"), 6)) if request.form.get("municipio_id") else None,
            "municipio_nombre": municipio_nombre,  # <-- NOMBRE garantizado
            "estado": int(_digits(request.form.get("estado"), 3)) if request.form.get("estado") else None,
            "estado_nombre": estado_nombre,        # <-- NOMBRE garantizado
            "codigo_postal": _digits(request.form.get("codigo_postal"), 16),
            "nombre_unidad": _upper(request.form.get("nombre_unidad")),
            "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
            "terminal_integradora": _v(request.form.get("terminal_integradora")),
            "terminal_dotacion_centralizada": _v(request.form.get("terminal_dotacion_centralizada")),
            "terminal_certificado_centralizada": _v(request.form.get("terminal_certificado_centralizada")),
            # Compat con tus columnas espejo:
            "tipo_cobro": session.get("frame1", {}).get("tipo_cobro"),
            "servicio": session.get("frame1", {}).get("tipo_servicio"),
            "tipo_unidad": _upper(request.form.get("tipo_servicio_unidad")),
            "tipo_servicio": _upper(request.form.get("tipo_servicio_unidad")),
        }
        unidades = session.get("unidades", [])
        unidades.append(u)
        session["unidades"] = unidades
        flash("Unidad agregada.", "success")
        return redirect(url_for("frames.frame2"))

    return render_template(
        "frame2.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        paso_actual=2,
        catalogo_cpae=catalogo_cpae,
        catalogo_etv=catalogo_etv,
        catalogo_estados=catalogo_estados
    )

# Endpoint para Municipios (depende de estado)
@frames_bp.get("/api/municipios")
def api_municipios():
    estado_id = request.args.get("estado_id")
    if not estado_id or not estado_id.isdigit():
        return jsonify({"ok": False, "error": "estado_id inválido"}), 400
    rows = fetchall(
        "SELECT id, nombre FROM catalogo_municipios WHERE estado_id = %s ORDER BY nombre",
        (int(estado_id),)
    ) or []
    return jsonify({"ok": True, "data": rows})

# -------------------- FRAME 3 (Cuentas) --------------------
@frames_bp.route("/cuentas", methods=["GET", "POST"])
def frame3():
    """
    Frame 3 - Cuentas.
    Usa columnas válidas según la tabla real:
    cuentas(id, solicitud_id, servicio, sucursal, cuenta, moneda, terminal_aplica)
    """
    if request.method == "POST":
        if "regresar_frame1" in request.form:
            return redirect(url_for("frames.frame1"))
        if "regresar_frame2" in request.form:
            return redirect(url_for("frames.frame2"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            cuentas = session.get("cuentas", [])
            if 0 <= idx < len(cuentas):
                cuentas.pop(idx)
                session["cuentas"] = cuentas
                flash("Cuenta eliminada.", "info")
            return redirect(url_for("frames.frame3"))

        # Validación básica
        obligatorios = ("servicio", "sucursal", "cuenta", "moneda")
        faltantes = [k for k in obligatorios if not request.form.get(k)]
        if faltantes:
            from markupsafe import escape
            faltantes = [escape(f) for f in faltantes]
            flash(f"Faltan campos: {', '.join(faltantes)}", "danger")
            return redirect(url_for("frames.frame3"))

        # Captura y normalización
        cuenta = {
            "servicio": (request.form.get("servicio") or "").upper(),
            "sucursal": request.form.get("sucursal") or "",
            "cuenta": request.form.get("cuenta") or "",
            "moneda": (request.form.get("moneda") or "").upper(),
            "terminal_aplica": request.form.get("terminal_aplica") or "",
        }

        cuentas = session.get("cuentas", [])
        cuentas.append(cuenta)
        session["cuentas"] = cuentas
        flash("Cuenta agregada.", "success")
        return redirect(url_for("frames.frame3"))

    unidades = session.get("unidades", [])
    catalogo_unidades = [
        {"idx": i, "nombre": (u.get("nombre_unidad") or f"Unidad {i+1}")} for i, u in enumerate(unidades)
    ]
    return render_template(
        "frame3.html",
        frame1=session.get("frame1"),
        cuentas=session.get("cuentas", []),
        unidades=unidades,
        catalogo_unidades=catalogo_unidades,
        paso_actual=3
    )


# -------------------- FRAME 4 (Usuarios SEF) --------------------
@frames_bp.route("/usuarios", methods=["GET", "POST"])
def frame4():
    """
    usuarios(solicitud_id, nombre_usuario, clave_usuario, perfil, maker_checker,
             correo, telefono, terminal_aplica, tipo_usuario, numero_terminal_sef, role)
    """
    if request.method == "POST":
        if "regresar_frame3" in request.form:
            return redirect(url_for("frames.frame3"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            usuarios = session.get("usuarios", [])
            if 0 <= idx < len(usuarios):
                usuarios.pop(idx)
                session["usuarios"] = usuarios
                flash("Usuario eliminado.", "info")
            return redirect(url_for("frames.frame4"))

        # Acepta campos tal como tu template los mande
        perfiles_list = request.form.getlist("perfiles") or []
        usuario = {
            "nombre_usuario": _upper(request.form.get("nombre_usuario") or request.form.get("nombre")),
            "clave_usuario": _v(request.form.get("clave_usuario")),
            "perfil": _upper(request.form.get("perfil") or ",".join(perfiles_list)),
            "maker_checker": _upper(request.form.get("maker_checker")),
            "correo": _v(request.form.get("correo")),
            "telefono": _v(request.form.get("telefono")),
            "terminal_aplica": _v(request.form.get("terminal_aplica")),
            "tipo_usuario": _upper(request.form.get("tipo_usuario")),
            "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
            "role": _upper(request.form.get("role") or "USER"),
        }
        usuarios = session.get("usuarios", [])
        usuarios.append(usuario)
        session["usuarios"] = usuarios
        flash("Usuario agregado.", "success")
        return redirect(url_for("frames.frame4"))

    catalogo_perfiles = fetchall(
        "SELECT id, descripcion, perfil FROM catalogo_perfiles ORDER BY perfil"
    )
    return render_template(
        "frame4.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        catalogo_perfiles=catalogo_perfiles,
        paso_actual=4
    )


# -------------------- FRAME 5 (Contactos) --------------------
@frames_bp.route("/contactos", methods=["GET", "POST"])
def frame5():
    """
    contactos(solicitud_id, nombre_contacto, correo, telefono, numero_terminal_sef, tipos_contacto)
    """
    if request.method == "POST":
        if "regresar_frame4" in request.form:
            return redirect(url_for("frames.frame4"))

        if "eliminar" in request.form:
            idx = int(request.form["eliminar"])
            contactos = session.get("contactos", [])
            if 0 <= idx < len(contactos):
                contactos.pop(idx)
                session["contactos"] = contactos
                flash("Contacto eliminado.", "info")
            return redirect(url_for("frames.frame5"))

        tipos = request.form.getlist("tipos_contacto") or []
        contacto = {
            "nombre_contacto": _upper(request.form.get("nombre_contacto") or request.form.get("nombre")),
            "correo": _v(request.form.get("correo")),
            "telefono": _v(request.form.get("telefono")),
            "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
            "tipos_contacto": ",".join(tipos),
        }
        contactos = session.get("contactos", [])
        contactos.append(contacto)
        session["contactos"] = contactos
        flash("Contacto agregado.", "success")
        return redirect(url_for("frames.frame5"))

    return render_template(
        "frame5.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),   # <-- agregar
        contactos=session.get("contactos", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        paso_actual=5
    )

# -------------------- FINALIZAR --------------------
@frames_bp.route("/finalizar", methods=["GET", "POST"])
def finalizar():
    def _to_bool(v):
        # acepta '1', 'true', True -> True
        return str(v).strip().lower() in ("1", "true", "t", "yes", "si")

    def _parse_fecha_ddmmyyyy(s):
        s = (s or "").strip()
        if not s:
            return None
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except Exception:
            return None

    if request.method == "POST":
        # 1) Confirmar firmantes (solo sesión)
        if "confirmar_firmantes" in request.form:
            apoderado = (request.form.get("apoderado_legal") or "").strip()
            fecha_firma_txt = (request.form.get("fecha_firma") or "").strip()
            nombre_aut1 = (request.form.get("nombre_autorizador") or "").strip()
            puesto_aut1 = (request.form.get("puesto_autorizador") or "").strip()
            nombre_aut2 = (request.form.get("nombre_director_divisional") or "").strip()
            puesto_aut2 = (request.form.get("puesto_director_divisional") or "").strip()
            anexo_usd = _to_bool(request.form.get("anexo_usd_14k"))

            falta = [x for x in (apoderado, fecha_firma_txt, nombre_aut1, puesto_aut1, nombre_aut2, puesto_aut2) if not x]
            if falta:
                flash("Completa todos los campos de firmantes antes de confirmar.", "warning")
                return redirect(url_for("frames.finalizar"))

            # persistir en sesión
            session["apoderado_legal"] = apoderado
            session["fecha_firma"] = fecha_firma_txt  # mantener formato dd/mm/aaaa en UI
            session["fecha_firma_iso"] = _parse_fecha_ddmmyyyy(fecha_firma_txt).isoformat() if _parse_fecha_ddmmyyyy(fecha_firma_txt) else None
            session["nombre_autorizador"] = nombre_aut1
            session["puesto_autorizador"] = puesto_aut1
            session["nombre_director_divisional"] = nombre_aut2
            session["puesto_director_divisional"] = puesto_aut2
            session["anexo_usd_14k"] = anexo_usd
            session["firmantes_confirmados"] = True
            session.modified = True

            flash("Solicitud validada. Proceda a guardarla.", "success")
            return redirect(url_for("frames.finalizar"))

        # 2) Guardar todo en BD
        # 2) Guardar todo en BD
        if "guardar_todo" in request.form:
            try:
                f1 = session["frame1"]
                unidades = session.get("unidades", [])
                cuentas  = session.get("cuentas", [])
                usuarios = session.get("usuarios", [])
                contactos= session.get("contactos", [])
                editing_id = session.get("editing_solicitud_id")

                # firmantes desde sesión (tras confirmar)
                def _to_bool(v): return str(v).strip().lower() in ("1","true","t","yes","si")
                def _parse_fecha_ddmmyyyy(s):
                    s = (s or "").strip()
                    if not s:
                        return None
                    try:
                        return datetime.strptime(s, "%d/%m/%Y").date()
                    except Exception:
                        return None

                apoderado = session.get("apoderado_legal") or f1.get("apoderado_legal")
                fecha_firma_date = None
                if session.get("fecha_firma_iso"):
                    try:
                        fecha_firma_date = datetime.fromisoformat(session["fecha_firma_iso"]).date()
                    except Exception:
                        fecha_firma_date = _parse_fecha_ddmmyyyy(session.get("fecha_firma"))
                else:
                    fecha_firma_date = _parse_fecha_ddmmyyyy(session.get("fecha_firma"))

                nombre_aut1 = session.get("nombre_autorizador")
                puesto_aut1 = session.get("puesto_autorizador")
                nombre_aut2 = session.get("nombre_director_divisional")
                puesto_aut2 = session.get("puesto_director_divisional")
                anexo_usd   = bool(session.get("anexo_usd_14k", False))

                contrato_tradicional = (f1.get("tipo_contrato") == "CPAE TRADICIONAL")
                contrato_electronico = (f1.get("tipo_contrato") == "SEF ELECTRÓNICO")

                from psycopg2.extras import RealDictCursor
                with conectar() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                    if editing_id:
                        # UPDATE solicitudes — placeholders y valores alineados
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
                                importe_maximo_dif = %s,
                                nombre_ejecutivo = %s,
                                domicilio_cliente = %s,
                                telefono_cliente = %s,
                                rdc_reporte = %s,
                                fecha_solicitud = %s,
                                updated_at = now(),
                                paso_actual = %s,
                                apoderado_legal = %s,
                                fecha_firma = %s,
                                anexo_usd_14k = %s,
                                contrato_tradicional = %s,
                                contrato_electronico = %s,
                                servicio_solicitado = %s,
                                estatus = %s,
                                nombre_autorizador = %s,
                                nombre_director_divisional = %s,
                                puesto_autorizador = %s,
                                puesto_director_divisional = %s
                            WHERE id = %s
                        """, (
                            f1.get("numero_cliente"),
                            f1.get("numero_contrato"),
                            f1.get("razon_social"),
                            f1.get("segmento"),
                            f1.get("tipo_persona"),
                            f1.get("tipo_tramite"),
                            f1.get("tipo_contrato"),
                            f1.get("tipo_servicio"),
                            f1.get("tipo_cobro"),
                            f1.get("importe_maximo_dif"),
                            f1.get("nombre_ejecutivo"),
                            f1.get("domicilio_cliente"),
                            f1.get("telefono_cliente"),
                            session.get("rdc_reporte", False),
                            f1.get("fecha_solicitud"),
                            6,
                            apoderado,
                            fecha_firma_date,
                            anexo_usd,
                            contrato_tradicional,
                            contrato_electronico,
                            f1.get("servicio_solicitado") or "",
                            f1.get("estatus") or "CAPTURADA",
                            nombre_aut1,
                            nombre_aut2,
                            puesto_aut1,
                            puesto_aut2,
                            editing_id
                        ))
                        solicitud_id = editing_id
                    else:
                        # INSERT solicitudes — placeholders y valores alineados
                        cur.execute("""
                            INSERT INTO solicitudes (
                                numero_cliente, razon_social, segmento, domicilio_cliente,
                                numero_contrato, tipo_tramite, tipo_contrato, tipo_servicio,
                                tipo_cobro, importe_maximo_dif, nombre_ejecutivo,
                                rdc_reporte, created_at, servicio_solicitado,
                                fecha_solicitud, estatus, tipo_persona, created_by,
                                updated_at, paso_actual, telefono_cliente, apoderado_legal,
                                fecha_firma, anexo_usd_14k, contrato_tradicional, contrato_electronico,
                                nombre_autorizador, nombre_director_divisional, puesto_autorizador, puesto_director_divisional
                            ) VALUES (
                                %s,%s,%s,%s,
                                %s,%s,%s,%s,
                                %s,%s,%s,
                                %s, now(), %s,
                                %s,%s,%s,%s,
                                now(), %s, %s, %s,
                                %s,%s,%s,%s,
                                %s,%s,%s,%s
                            )
                            RETURNING id
                        """, (
                            f1.get("numero_cliente"),
                            f1.get("razon_social"),
                            f1.get("segmento"),
                            f1.get("domicilio_cliente"),
                            f1.get("numero_contrato"),
                            f1.get("tipo_tramite"),
                            f1.get("tipo_contrato"),
                            f1.get("tipo_servicio"),
                            f1.get("tipo_cobro"),
                            f1.get("importe_maximo_dif"),
                            f1.get("nombre_ejecutivo"),
                            session.get("rdc_reporte", False),
                            f1.get("servicio_solicitado") or "",
                            f1.get("fecha_solicitud"),
                            f1.get("estatus") or "CAPTURADA",
                            f1.get("tipo_persona"),
                            session.get("user_id"),
                            6,
                            f1.get("telefono_cliente"),
                            apoderado,
                            fecha_firma_date,
                            anexo_usd,
                            contrato_tradicional,
                            contrato_electronico,
                            nombre_aut1,
                            nombre_aut2,
                            puesto_aut1,
                            puesto_aut2
                        ))
                        solicitud_id = cur.fetchone()["id"]

                    # -------- UNIDADES --------
                    cur.execute("DELETE FROM unidades WHERE solicitud_id = %s", (solicitud_id,))
                    for u in unidades:
                        cur.execute("""
                            INSERT INTO unidades (
                                solicitud_id, nombre_unidad, cpae_nombre, tipo_servicio_unidad,
                                etv_nombre, numero_terminal_sef, calle_numero, colonia,
                                municipio_nombre, estado_nombre, codigo_postal,
                                terminal_integradora, terminal_dotacion_centralizada, terminal_certificado_centralizada,
                                tipo_cobro, servicio, tipo_unidad, cpae, tipo_servicio,
                                empresa_traslado, municipio_id, estado
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            u.get("nombre_unidad"),
                            u.get("cpae_nombre"),
                            u.get("tipo_servicio_unidad"),
                            u.get("etv_nombre") or u.get("empresa_traslado"),
                            u.get("numero_terminal_sef"),
                            u.get("calle_numero"),
                            u.get("colonia"),
                            u.get("municipio_nombre"),
                            u.get("estado_nombre"),
                            u.get("codigo_postal"),
                            u.get("terminal_integradora"),
                            u.get("terminal_dotacion_centralizada"),
                            u.get("terminal_certificado_centralizada"),
                            u.get("tipo_cobro"),
                            u.get("servicio"),
                            u.get("tipo_unidad"),
                            u.get("cpae"),
                            u.get("tipo_servicio"),
                            u.get("empresa_traslado"),
                            u.get("municipio_id"),
                            u.get("estado"),
                        ))

                    # -------- CUENTAS --------
                    cur.execute("DELETE FROM cuentas WHERE solicitud_id = %s", (solicitud_id,))
                    for c in cuentas:
                        cur.execute("""
                            INSERT INTO cuentas (
                                solicitud_id, servicio, sucursal, cuenta, moneda,
                                terminal_aplica)
                            VALUES (%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            c.get("servicio"),
                            c.get("sucursal"),
                            c.get("cuenta"),
                            c.get("moneda"),
                            c.get("terminal_aplica"),
                        ))

                    # -------- USUARIOS --------
                    cur.execute("DELETE FROM usuarios WHERE solicitud_id = %s", (solicitud_id,))
                    for u in usuarios:
                        cur.execute("""
                            INSERT INTO usuarios (
                                solicitud_id, nombre_usuario, clave_usuario, perfil, maker_checker,
                                correo, telefono, terminal_aplica, tipo_usuario, numero_terminal_sef, role
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            u.get("nombre_usuario") or u.get("nombre"),
                            u.get("clave_usuario"),
                            u.get("perfil"),
                            u.get("maker_checker"),
                            u.get("correo"),
                            u.get("telefono"),
                            u.get("terminal_aplica"),
                            u.get("tipo_usuario"),
                            u.get("numero_terminal_sef"),
                            u.get("role") or "USER",
                        ))

                    # -------- CONTACTOS --------
                    cur.execute("DELETE FROM contactos WHERE solicitud_id = %s", (solicitud_id,))
                    for c in contactos:
                        cur.execute("""
                            INSERT INTO contactos (
                                solicitud_id, nombre_contacto, correo, telefono, numero_terminal_sef, tipos_contacto
                            ) VALUES (%s,%s,%s,%s,%s,%s)
                        """, (
                            solicitud_id,
                            c.get("nombre_contacto") or c.get("nombre"),
                            c.get("correo"),
                            c.get("telefono"),
                            c.get("numero_terminal_sef"),
                            c.get("tipos_contacto") if isinstance(c.get("tipos_contacto"), str)
                                else ",".join(c.get("tipos_contacto") or []),
                        ))

                session.pop("editing_solicitud_id", None)
          #      flash("Solicitud guardada correctamente.", "success")
                return redirect(url_for("solicitudes_portal.lista"))
            except Exception as e:
                flash(f"Error al guardar la solicitud: {e}", "danger")
                return redirect(url_for("frames.finalizar"))

        # Regresar
        if "regresar_frame5" in request.form:
            return redirect(url_for("frames.frame5"))

    # --- GET con ?solicitud_id=... -> cargar desde BD a sesión para ver/retomar ---
    if request.method == "GET" and request.args.get("solicitud_id"):
        try:
            sol_id = int(request.args.get("solicitud_id"))
        except Exception:
            flash("El identificador de la solicitud no es válido.", "danger")
            return redirect(url_for("solicitudes_portal.lista"))

        try:
            from psycopg2.extras import RealDictCursor
            with conectar() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Carga cabecera
                cur.execute(
                    """
                    SELECT *
                    FROM solicitudes
                    WHERE id = %s
                    """,
                    (sol_id,)
                )
                sol = cur.fetchone()
                if not sol:
                    flash("No se encontró la solicitud indicada.", "warning")
                    return redirect(url_for("solicitudes_portal.lista"))

                # Mapear cabecera a la estructura de frame1 usada en tu flujo
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
                    "telefono_cliente": sol.get("telefono_cliente"),
                    "apoderado_legal": sol.get("apoderado_legal"),
                    "tipo_persona": sol.get("tipo_persona"),
                    "servicio_solicitado": sol.get("servicio_solicitado") or "",
                    "estatus": sol.get("estatus") or "CAPTURADA",
                    # tu app usa date ISO para fecha_solicitud en sesión
                    "fecha_solicitud": (sol.get("fecha_solicitud").isoformat()
                                        if sol.get("fecha_solicitud") else None),
                }
                session["frame1"] = f1
                session["rdc_reporte"] = bool(sol.get("rdc_reporte"))
                session["anexo_usd_14k"] = bool(sol.get("anexo_usd_14k"))

                # Firmantes (para prellenar y permitir exportar/guardar)
                session["apoderado_legal"] = sol.get("apoderado_legal")
                # guarda ISO y visible dd/mm/aaaa
                _ff = sol.get("fecha_firma")
                session["fecha_firma_iso"] = (_ff.isoformat() if _ff else None)
                session["fecha_firma"] = (_ff.strftime("%d/%m/%Y") if _ff else None)

                session["nombre_autorizador"] = sol.get("nombre_autorizador")
                session["puesto_autorizador"] = sol.get("puesto_autorizador")
                session["nombre_director_divisional"] = sol.get("nombre_director_divisional")
                session["puesto_director_divisional"] = sol.get("puesto_director_divisional")

                # Carga hijos
                # Unidades
                cur.execute(
                    """
                    SELECT *
                    FROM unidades
                    WHERE solicitud_id = %s
                    ORDER BY id
                    """,
                    (sol_id,)
                )
                rows_u = cur.fetchall() or []
                unidades = []
                for u in rows_u:
                    unidades.append({
                        "nombre_unidad": u.get("nombre_unidad"),
                        "cpae_nombre": u.get("cpae_nombre"),
                        "tipo_servicio_unidad": u.get("tipo_servicio_unidad"),
                        "etv_nombre": u.get("etv_nombre"),
                        "numero_terminal_sef": u.get("numero_terminal_sef"),
                        "calle_numero": u.get("calle_numero"),
                        "colonia": u.get("colonia"),
                        "municipio_nombre": u.get("municipio_nombre"),
                        "estado_nombre": u.get("estado_nombre"),
                        "codigo_postal": u.get("codigo_postal"),
                        "terminal_integradora": u.get("terminal_integradora"),
                        "terminal_dotacion_centralizada": u.get("terminal_dotacion_centralizada"),
                        "terminal_certificado_centralizada": u.get("terminal_certificado_centralizada"),
                        # claves espejo que usas al guardar
                        "tipo_cobro": u.get("tipo_cobro"),
                        "servicio": u.get("servicio"),
                        "tipo_unidad": u.get("tipo_unidad"),
                        "cpae": u.get("cpae"),
                        "tipo_servicio": u.get("tipo_servicio"),
                        "empresa_traslado": u.get("empresa_traslado"),
                        "municipio_id": u.get("municipio_id"),
                        "estado": u.get("estado"),
                    })
                session["unidades"] = unidades

                # Cuentas
                cur.execute(
                    """
                    SELECT *
                    FROM cuentas
                    WHERE solicitud_id = %s
                    ORDER BY id
                    """,
                    (sol_id,)
                )
                rows_c = cur.fetchall() or []
                cuentas = []
                for c in rows_c:
                    cuentas.append({
                        "servicio": c.get("servicio"),
                        "sucursal": c.get("sucursal"),
                        "cuenta": c.get("cuenta"),
                        "moneda": c.get("moneda"),
                        "terminal_aplica": c.get("terminal_aplica"),
                        # si en tu tabla existen estas columas opcionales,
                        "numero_sucursal": c.get("numero_sucursal"),
                        "numero_cuenta": c.get("numero_cuenta"),
                        "terminal_aplicable": c.get("terminal_aplicable"),
                    })
                session["cuentas"] = cuentas

                # Usuarios
                cur.execute(
                    """
                    SELECT *
                    FROM usuarios
                    WHERE solicitud_id = %s
                    ORDER BY id
                    """,
                    (sol_id,)
                )
                rows_us = cur.fetchall() or []
                usuarios = []
                for u in rows_us:
                    usuarios.append({
                        "nombre_usuario": u.get("nombre_usuario"),
                        "clave_usuario": u.get("clave_usuario"),
                        "perfil": u.get("perfil"),
                        "maker_checker": u.get("maker_checker"),
                        "correo": u.get("correo"),
                        "telefono": u.get("telefono"),
                        "terminal_aplica": u.get("terminal_aplica"),
                        "tipo_usuario": u.get("tipo_usuario"),
                        "numero_terminal_sef": u.get("numero_terminal_sef"),
                        "role": u.get("role") or "USER",
                    })
                session["usuarios"] = usuarios

                # Contactos
                cur.execute(
                    """
                    SELECT *
                    FROM contactos
                    WHERE solicitud_id = %s
                    ORDER BY id
                    """,
                    (sol_id,)
                )
                rows_ct = cur.fetchall() or []
                contactos = []
                for c in rows_ct:
                    contactos.append({
                        "nombre_contacto": c.get("nombre_contacto") or c.get("nombre"),
                        "correo": c.get("correo"),
                        "telefono": c.get("telefono"),
                        "numero_terminal_sef": c.get("numero_terminal_sef"),
                        "tipos_contacto": c.get("tipos_contacto"),
                    })
                session["contactos"] = contactos

                # Marcar que estamos retomando/visualizando esta solicitud
                session["editing_solicitud_id"] = sol_id
                session.modified = True

        except Exception as e:
            # Si algo falla, no tumbes la vista
            flash(f"No fue posible cargar la solicitud seleccionada: {e}", "danger")
            return redirect(url_for("solicitudes_portal.lista"))

    # GET finalizar
    return render_template(
        "finalizar.html",
        frame1=session.get("frame1") or {},
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        paso_actual=6
    )

import logging
from psycopg2.extras import RealDictCursor

log = logging.getLogger(__name__)

def exec_sql(cur, sql, params=()):
    """
    Ejecuta SQL logueando la sentencia mogrificada.
    Útil para depurar errores como "not all arguments converted during string formatting".
    """
    try:
        q = cur.mogrify(sql, params)
        log.debug("SQL -> %s", q.decode() if isinstance(q, bytes) else q)
    except Exception as e_mog:
        log.error("❌ Error al mogrificar: %s", e_mog)
        log.error("SQL plantilla -> %s", sql)
        log.error("Params -> %r", params)

    try:
        cur.execute(sql, params)
    except Exception as e_exec:
        log.exception("❌ Falló execute(): %s | SQL -> %s | Params -> %r", e_exec, sql, params)
        raise
    
@frames_bp.route("/solicitudes/nueva")
def nueva_solicitud():
    # Limpia variables de sesión relacionadas con la captura
    for k in ["frame1", "unidades", "cuentas", "usuarios", "contactos",
              "firmantes", "anexo_usd_14k", "contrato_tradicional",
              "contrato_electronico", "rdc_reporte", "editing_solicitud_id"]:
        session.pop(k, None)
    session.modified = True
    return redirect(url_for("frames.frame1"))
