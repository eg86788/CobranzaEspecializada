# app/blueprints/captura.py
# -----------------------------------------------------------------------------
# Blueprint "captura" - página única que integra Frame1,2,3,4,5 y Firmantes/Finalizar.
# No reemplaza frames.py; usa los mismos nombres de campos y estructuras en sesión.
# Al finalizar, redirige a /finalizar para persistir usando la lógica existente.
# -----------------------------------------------------------------------------

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import date, datetime
from psycopg2.extras import RealDictCursor

# Reutiliza tus helpers y conectores existentes
try:
    from ..db_legacy import fetchall, conectar
except Exception:
    from app.db_legacy import fetchall, conectar  # pragma: no cover

captura_bp = Blueprint("captura", __name__)

# ------------------------ Helpers “clone” minimalistas ------------------------
def _upper(s): return (s or "").upper()
def _v(s): return (s or "").strip()
def _digits(s, maxlen=None):
    s = (s or "")
    only = "".join(ch for ch in s if ch.isdigit())
    return only[:maxlen] if maxlen else only

def _parse_fecha_ddmmyyyy(s):
    s = (s or "").strip()
    if not s: return None
    try:
        return datetime.strptime(s, "%d/%m/%Y").date()
    except Exception:
        return None

# -----------------------------------------------------------------------------
# Página única
# -----------------------------------------------------------------------------
@captura_bp.route("/captura", methods=["GET","POST"])
def captura_registros():
    # Catálogos que necesita la UI (mismos que frame1/frame2)
    catalogo_cpae    = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv     = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    # Estado actual de sesión
    f1        = session.get("frame1") or {}
    unidades  = session.get("unidades", [])
    cuentas   = session.get("cuentas", [])
    usuarios  = session.get("usuarios", [])
    contactos = session.get("contactos", [])

    if request.method == "POST":
        action = request.form.get("_action") or ""

        # ==================== Sección: Datos de la solicitud (Frame1) ====================
        if action == "guardar_frame1":
            # Lee exactamente los mismos campos que ya usas en frame1
            datos = {k: _v(request.form.get(k)) for k in (
                "tipo_tramite","nombre_ejecutivo","segmento","numero_cliente","tipo_persona",
                "razon_social","apoderado_legal","correo_apoderado_legal","tipo_contrato",
                "tipo_servicio","tipo_cobro","importe_maximo_dif","numero_contrato",
                "telefono_cliente","domicilio_cliente",
                # nuevos campos sust_* (cheks/radios guardados como 'on'/'1' etc.)
                "sust_modo_contrato","sust_modo_registros",
                "sust_op_unidades","sust_op_cuentas","sust_op_usuarios","sust_op_contactos",
                "sust_op_impdif","sust_op_tipocobro",
                # “sombra” para repintar (si tu template lo usa)
                "sustitucion_modo","sustitucion_registros"
            )}

            # Consistencia mínima
            if (datos.get("tipo_tramite") or "").upper() == "ALTA":
                datos["numero_contrato"] = "-"
            elif not datos.get("numero_contrato"):
                flash("El número de contrato es obligatorio para sustitución.", "danger")
                return redirect(url_for("captura.captura_registros"))

            for k in ("tipo_tramite","nombre_ejecutivo","segmento","numero_cliente",
                      "razon_social","apoderado_legal","tipo_persona","tipo_contrato",
                      "tipo_servicio","tipo_cobro"):
                if not datos.get(k):
                    flash("Completa los campos obligatorios de la solicitud.", "danger")
                    return redirect(url_for("captura.captura_registros"))

            if not datos.get("importe_maximo_dif"):
                datos["importe_maximo_dif"] = "-"

            # Persistencia en sesión (igual a frame1)
            session["rdc_reporte"] = (datos.get("tipo_cobro") == "CENTRALIZADO")
            session["frame1"] = {**datos, "fecha_solicitud": date.today().isoformat()}
            session.modified = True
            flash("Datos de la solicitud guardados.", "success")
            return redirect(url_for("captura.captura_registros"))

        # ==================== Sección: Unidades (Frame2) ====================
        if action == "agregar_unidad":
            # Respeta nombres de campos actuales
            u = {
                "cpae": _v(request.form.get("cpae")),
                "cpae_nombre": _upper(request.form.get("cpae_nombre")),
                "tipo_servicio_unidad": _upper(request.form.get("tipo_servicio_unidad")),
                "etv_nombre": _upper(request.form.get("etv_nombre")),
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
                # Espejos
                "tipo_cobro": (session.get("frame1") or {}).get("tipo_cobro"),
                "servicio": (session.get("frame1") or {}).get("tipo_servicio"),
                "tipo_unidad": _upper(request.form.get("tipo_servicio_unidad")),
                "tipo_servicio": _upper(request.form.get("tipo_servicio_unidad")),
                # NUEVO (tipo de movimiento de la unidad)
                "tipo_movimiento": _upper(request.form.get("tipo_movimiento_unidad")),
            }

            unidades = session.get("unidades", [])
            unidades.append(u)
            session["unidades"] = unidades
            session.modified = True
            flash("Unidad agregada.", "success")
            return redirect(url_for("captura.captura_registros"))

        if action.startswith("eliminar_unidad_"):
            try:
                idx = int(action.split("_")[-1])
            except Exception:
                idx = -1
            unidades = session.get("unidades", [])
            if 0 <= idx < len(unidades):
                unidades.pop(idx)
                session["unidades"] = unidades
                session.modified = True
                flash("Unidad eliminada.", "info")
            return redirect(url_for("captura.captura_registros"))

        # ==================== Sección: Cuentas (Frame3) ====================
        if action == "agregar_cuenta":
            cta = {
                "servicio": _upper(request.form.get("servicio")),
                "sucursal": _v(request.form.get("sucursal")),
                "cuenta": _v(request.form.get("cuenta")),
                "moneda": _upper(request.form.get("moneda")),
                "terminal_aplica": _v(request.form.get("terminal_aplica")),
                # NUEVO
                "tipo_movimiento": _upper(request.form.get("tipo_movimiento_cuenta")),
            }
            cuentas = session.get("cuentas", [])
            cuentas.append(cta)
            session["cuentas"] = cuentas
            session.modified = True
            flash("Cuenta agregada.", "success")
            return redirect(url_for("captura.captura_registros"))

        if action.startswith("eliminar_cuenta_"):
            try:
                idx = int(action.split("_")[-1])
            except Exception:
                idx = -1
            cuentas = session.get("cuentas", [])
            if 0 <= idx < len(cuentas):
                cuentas.pop(idx)
                session["cuentas"] = cuentas
                session.modified = True
                flash("Cuenta eliminada.", "info")
            return redirect(url_for("captura.captura_registros"))

        # ==================== Sección: Usuarios (Frame4) ====================
        if action == "agregar_usuario":
            perfiles_list = request.form.getlist("perfiles") or []
            us = {
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
                # NUEVO
                "tipo_movimiento": _upper(request.form.get("tipo_movimiento_usuario")),
            }
            usuarios = session.get("usuarios", [])
            usuarios.append(us)
            session["usuarios"] = usuarios
            session.modified = True
            flash("Usuario agregado.", "success")
            return redirect(url_for("captura.captura_registros"))

        if action.startswith("eliminar_usuario_"):
            try:
                idx = int(action.split("_")[-1])
            except Exception:
                idx = -1
            usuarios = session.get("usuarios", [])
            if 0 <= idx < len(usuarios):
                usuarios.pop(idx)
                session["usuarios"] = usuarios
                session.modified = True
                flash("Usuario eliminado.", "info")
            return redirect(url_for("captura.captura_registros"))

        # ==================== Sección: Contactos (Frame5) ====================
        if action == "agregar_contacto":
            tipos = request.form.getlist("tipos_contacto") or []
            ct = {
                "nombre_contacto": _upper(request.form.get("nombre_contacto") or request.form.get("nombre")),
                "correo": _v(request.form.get("correo")),
                "telefono": _v(request.form.get("telefono")),
                "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
                "tipos_contacto": ",".join(tipos),
                # NUEVO
                "tipo_movimiento": _upper(request.form.get("tipo_movimiento_contacto")),
            }
            contactos = session.get("contactos", [])
            contactos.append(ct)
            session["contactos"] = contactos
            session.modified = True
            flash("Contacto agregado.", "success")
            return redirect(url_for("captura.captura_registros"))

        if action.startswith("eliminar_contacto_"):
            try:
                idx = int(action.split("_")[-1])
            except Exception:
                idx = -1
            contactos = session.get("contactos", [])
            if 0 <= idx < len(contactos):
                contactos.pop(idx)
                session["contactos"] = contactos
                session.modified = True
                flash("Contacto eliminado.", "info")
            return redirect(url_for("captura.captura_registros"))

        # ==================== Sección: Firmantes (Finalizar UI) ====================
        if action == "guardar_firmantes":
            # Guarda en sesión para que /finalizar lo tome igual que hoy
            session["apoderado_legal"] = _v(request.form.get("apoderado_legal"))
            ff_txt = _v(request.form.get("fecha_firma"))
            ff = _parse_fecha_ddmmyyyy(ff_txt)
            session["fecha_firma"] = ff_txt
            session["fecha_firma_iso"] = ff.isoformat() if ff else None
            session["nombre_autorizador"] = _v(request.form.get("nombre_autorizador"))
            session["puesto_autorizador"] = _v(request.form.get("puesto_autorizador"))
            session["nombre_director_divisional"] = _v(request.form.get("nombre_director_divisional"))
            session["puesto_director_divisional"] = _v(request.form.get("puesto_director_divisional"))
            session["anexo_usd_14k"] = (_v(request.form.get("anexo_usd_14k")).lower() in ("1","true","t","yes","si","on"))
            session["firmantes_confirmados"] = True
            session.modified = True
            flash("Firmantes guardados.", "success")
            return redirect(url_for("captura.captura_registros"))

        # ==================== Guardar todo en BD ====================
        if action == "guardar_todo":
            # Reutiliza tu flujo actual
            return redirect(url_for("frames.finalizar"))

    # GET
    return render_template(
        "captura_registros.html",
        frame1=session.get("frame1") or {},
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        catalogo_cpae=catalogo_cpae,
        catalogo_etv=catalogo_etv,
        catalogo_estados=catalogo_estados,
    )
