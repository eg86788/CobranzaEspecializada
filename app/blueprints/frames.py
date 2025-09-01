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
        obligatorios = ("cpae", "nombre_unidad", "tipo_servicio_unidad")
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
                flash("Solicitud guardada correctamente.", "success")
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
        obligatorios = ("cpae", "nombre_unidad", "tipo_servicio_unidad")
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
                flash("Solicitud guardada correctamente.", "success")
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
