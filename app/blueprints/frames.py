# app/blueprints/frames.py
# -----------------------------------------------------------------------------
# Blueprint de "frames" para capturar solicitudes en múltiples pantallas (frames).
# Mantiene datos en sesión por cada paso y finalmente guarda todo en BD
# desde la pantalla "Finalizar". Incluye endpoint clásico "nueva_solicitud".
# -----------------------------------------------------------------------------

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime, date
import logging
import unicodedata
import re
import psycopg2
from psycopg2.extras import RealDictCursor

# Conectores BD (usa tu módulo db_legacy)
try:
    from ..db_legacy import fetchall, fetchone, conectar
except Exception:
    from app.db_legacy import fetchall, fetchone, conectar  # pragma: no cover

frames_bp = Blueprint("frames", __name__)
log = logging.getLogger(__name__)

# =============================================================================
# Helpers y utilidades
# =============================================================================

def _upper(s):
    return (s or "").upper()

def _v(s):
    return (s or "").strip()

def _digits(s, maxlen=None):
    s = (s or "")
    only = "".join(ch for ch in s if ch.isdigit())
    return only[:maxlen] if maxlen else only

def _parse_fecha_dmy(s):
    """Convierte 'dd/mm/aaaa' -> date; devuelve None si no es válida."""
    s = (s or "").strip()
    if not s:
        return None
    try:
        d, m, y = s.split("/")
        return date(int(y), int(m), int(d))
    except Exception:
        return None

def limpiar_dependientes():
    """Limpia colecciones dependientes de frame1 cuando cambia configuración clave."""
    for k in ("unidades", "cuentas", "usuarios", "contactos"):
        session.pop(k, None)
    session.modified = True

def hay_dependientes():
    """Indica si hay datos capturados en frames 2–5 en sesión."""
    return any((session.get("unidades"), session.get("cuentas"),
                session.get("usuarios"), session.get("contactos")))

def exec_sql(cur, sql, params=()):
    """
    Ejecuta SQL logueando la sentencia mogrificada (útil para depuración).
    No cambia la lógica; es auxiliar por si quieres instrumentar.
    """
    try:
        q = cur.mogrify(sql, params)
        log.debug("SQL -> %s", q.decode() if isinstance(q, bytes) else q)
    except Exception as e_mog:
        log.error("❌ Error al mogrificar: %s", e_mog)
        log.error("SQL plantilla -> %s", sql)
        log.error("Params -> %r", params)
    cur.execute(sql, params)

# ---------- Helpers ----------
def _norm(s: str) -> str:
    import unicodedata
    s = (s or "")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return s.upper().strip()

def _as_decimal_str(s: str, default="200.01") -> str:
    raw = (s or "").replace(",", "").replace("$", "").strip()
    if not raw:
        return default
    try:
        return f"{float(raw):.2f}"
    except ValueError:
        return default

def _required(errors, data, name, label=None):
    label = label or name
    if not (data.get(name) or "").strip():
        errors.append(f"Falta {label}")
        return False
    return True

def _changed(a, b, key):
    return _norm((a or {}).get(key)) != _norm((b or {}).get(key))

def _get_nombre_usuario_sesion() -> str:
    """
    Obtiene el nombre del usuario desde la sesión para precargar 'nombre_ejecutivo'
    SOLO en solicitudes nuevas.
    Ajusta/expande las llaves según tu login real.
    """
    for k in ("user_name", "username", "nombre", "nombre_usuario", "full_name", "display_name"):
        v = (session.get(k) or "").strip()
        if v:
            return v
    return ""


# -----------------------------------------------------------------------------
# NUEVA SOLICITUD
# -----------------------------------------------------------------------------
@frames_bp.route("/solicitudes/nueva", methods=["GET"])
def nueva_solicitud():
    for k in [
        "frame1", "frame1_prev", "unidades", "cuentas", "usuarios", "contactos",
        "firmantes", "anexo_usd_14k", "contrato_tradicional", "contrato_electronico",
        "rdc_reporte", "editing_solicitud_id"
    ]:
        session.pop(k, None)
    session.modified = True
    return redirect(url_for("frames.frame1"))
# -----------------------------------------------------------------------------
# FRAME 1
# -----------------------------------------------------------------------------
@frames_bp.route("/solicitud_sef", methods=["GET", "POST"])
def frame1():
    # catálogos para selects
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    def _digits_only(s: str, maxlen: int) -> str:
        s = (s or "")
        s = "".join(ch for ch in s if ch.isdigit())
        return s[:maxlen] if maxlen else s

    def _decimal_str(s: str, default="200.01") -> str:
        raw = (s or "").replace(",", "").replace("$", "").strip()
        if not raw:
            return default
        try:
            return f"{float(raw):.2f}"
        except Exception:
            return default

    log.warning("SESSION KEYS: %s", list(session.keys()))
    log.warning("SESSION user_id=%r user_name=%r username=%r nombre=%r", 
                session.get("user_id"), session.get("user_name"), session.get("username"), session.get("nombre"))


    if request.method == "POST":
        # Campos base
        datos = {k: _v(request.form.get(k)) for k in (
            "tipo_tramite","nombre_ejecutivo","segmento","numero_cliente","tipo_persona",
            "razon_social","apoderado_legal","correo_apoderado_legal","tipo_contrato",
            "tipo_servicio","tipo_cobro","importe_maximo_dif","numero_contrato",
            "telefono_cliente","domicilio_cliente",
        )}

        # Sanitizados básicos
        datos["numero_cliente"]     = _digits_only(datos.get("numero_cliente"), 9)
        datos["numero_contrato"]    = _digits_only(datos.get("numero_contrato"), 11)
        datos["importe_maximo_dif"] = _decimal_str(datos.get("importe_maximo_dif"))

        # GET: estado de sesión actual
        session.modified = True
        editing_id = session.get("editing_solicitud_id")

        if not (datos.get("nombre_ejecutivo") or "").strip():
            if editing_id:
                datos["nombre_ejecutivo"] = (session.get("frame1") or {}).get("nombre_ejecutivo") or ""
            else:
                datos["nombre_ejecutivo"] = _get_nombre_usuario_sesion() or ""

        # ------------------ SUSTITUCIÓN: acción única, múltiples entidades ------------------
        # MODIFICAR: entidades
        mod = []
        if request.form.get("smod_unidades"):  mod.append("UNIDADES")
        if request.form.get("smod_cuentas"):   mod.append("CUENTAS")
        if request.form.get("smod_usuarios"):  mod.append("USUARIOS")
        if request.form.get("smod_contactos"): mod.append("CONTACTOS")

        # CREAR: entidades
        crea = []
        if request.form.get("screa_unidades"):  crea.append("UNIDADES")
        if request.form.get("screa_cuentas"):   crea.append("CUENTAS")
        if request.form.get("screa_usuarios"):  crea.append("USUARIOS")
        if request.form.get("screa_contactos"): crea.append("CONTACTOS")

        # Extras de MODIFICAR sobre configuración del contrato
        mod_extras = []
        if request.form.get("smod_tipocobro"): mod_extras.append("TIPOCOBRO")
        if request.form.get("smod_impdif"):    mod_extras.append("IMPDIF")

        # Guardar en datos (y CSVs por si los reportes/BD los quieren planos)
        datos["sust_mod"]             = mod[:]
        datos["sust_crea"]            = crea[:]
        datos["sust_mod_extras"]      = mod_extras[:]
        datos["sust_mod_csv"]         = ",".join(mod)
        datos["sust_crea_csv"]        = ",".join(crea)
        datos["sust_mod_extras_csv"]  = ",".join(mod_extras)

        # Determinar acción: exclusiva
        total_mod = len(mod) + len(mod_extras)
        if total_mod > 0 and len(crea) == 0:
            datos["sust_accion"]  = "MODIFICAR"
            # Si solo hay extras sin entidades, marca entidad como CONFIG
            if len(mod) == 0 and len(mod_extras) > 0:
                datos["sust_entidad"] = "CONFIG"
            else:
                datos["sust_entidad"] = "MULTIPLE" if len(mod) > 1 else (mod[0] if len(mod)==1 else "CONFIG")
        elif len(crea) > 0 and total_mod == 0:
            datos["sust_accion"]  = "CREAR"
            datos["sust_entidad"] = "MULTIPLE" if len(crea) > 1 else crea[0]
        else:
            datos["sust_accion"]  = ""
            datos["sust_entidad"] = ""

        # ------------------ Compatibilidad legacy (no estorba si ya no lo usas) --------------
        regs = []
        if request.form.get("sust_op_unidades"):  regs.append("UNIDADES")
        if request.form.get("sust_op_cuentas"):   regs.append("CUENTAS")
        if request.form.get("sust_op_usuarios"):  regs.append("USUARIOS")
        if request.form.get("sust_op_contactos"): regs.append("CONTACTOS")
        if request.form.get("sust_op_impdif"):    regs.append("IMPDIF")
        if request.form.get("sust_op_tipocobro"): regs.append("TIPOCOBRO")
        sustitucion_modo = (request.form.get("sustitucion_modo") or "").strip()
        datos["sustitucion_modo"]      = sustitucion_modo
        datos["sustitucion_registros"] = ",".join(regs) if regs else ""

        # ------------------ Reglas de consistencia de negocio --------------------------------
        tipo_tramite = (datos.get("tipo_tramite") or "").upper()
        if tipo_tramite == "ALTA":
            # En ALTA no exigimos número de contrato; placeholder
            datos["numero_contrato"] = datos.get("numero_contrato") or "-"
        elif tipo_tramite in ("SUSTITUCIÓN","SUSTITUCION"):
            if not datos.get("numero_contrato"):
                flash("El número de contrato es obligatorio para SUSTITUCIÓN.", "danger")
                return redirect(url_for("frames.frame1"))

            if total_mod == 0 and len(crea) == 0:
                flash("Marca al menos una entidad para MODIFICAR (o sus opciones), o entidades para CREAR.", "danger")
                return redirect(url_for("frames.frame1"))

            if total_mod > 0 and len(crea) > 0:
                flash("No puedes mezclar MODIFICAR y CREAR en la misma solicitud. Elige solo una acción.", "danger")
                return redirect(url_for("frames.frame1"))

            # Reglas específicas de extras
            if "TIPOCOBRO" in mod_extras and not (datos.get("tipo_cobro") or "").strip():
                flash("Selecciona el nuevo Tipo de Cobro para la modificación.", "danger")
                return redirect(url_for("frames.frame1"))
            if "IMPDIF" in mod_extras and not (datos.get("importe_maximo_dif") or "").strip():
                flash("Captura el nuevo Importe Máximo de Diferencias para la modificación.", "danger")
                return redirect(url_for("frames.frame1"))

            # Legacy: si alguien activa modo REGISTROS sin detalle
            if sustitucion_modo == "REGISTROS" and not regs:
                flash("En modo de sustitución por registros (legacy), marca al menos un tipo de registro.", "danger")
                return redirect(url_for("frames.frame1"))
        else:
            flash("Selecciona el Tipo de Trámite.", "danger")
            return redirect(url_for("frames.frame1"))

        # ------------------ Purgar contactos si cambia Tipo de Cobro --------------------------
        try:
            prev_cobro  = ((session.get("frame1") or {}).get("tipo_cobro") or "").upper()
            nuevo_cobro = (datos.get("tipo_cobro") or "").upper()

            if prev_cobro and nuevo_cobro and prev_cobro != nuevo_cobro:
                contactos = session.get("contactos", []) or []
                eliminados = 0
                resultado = []

                def truthy(v): return str(v).strip().upper() in ("SI", "TRUE", "1")
                def norm(s): return (s or "").strip().upper()
                def es_local_label(lbl):    return ("LOCAL" in norm(lbl)) or ("DIFERENCIAS LOCALES" in norm(lbl))
                def es_central_label(lbl):  return ("CENTRAL" in norm(lbl)) or ("DIFERENCIAS CENTRALES" in norm(lbl))

                for c in contactos:
                    fl_local    = truthy(c.get("contacto_diferencias_locales"))
                    fl_central  = truthy(c.get("contacto_diferencias_centrales"))
                    labels      = [x.strip() for x in str(c.get("tipos_contacto") or "").split(",") if x.strip()]

                    incompatible = False
                    if prev_cobro == "CENTRALIZADO" and nuevo_cobro == "LOCAL":
                        incompatible = fl_central or any(es_central_label(lbl) for lbl in labels)
                    elif prev_cobro == "LOCAL" and nuevo_cobro == "CENTRALIZADO":
                        incompatible = fl_local or any(es_local_label(lbl) for lbl in labels)

                    if incompatible:
                        eliminados += 1
                        continue
                    resultado.append(c)

                if eliminados:
                    session["contactos"] = resultado
                    session.modified = True
                    flash(
                        f"Se cambió el Tipo de Cobro a {nuevo_cobro}. "
                        f"Se eliminaron {eliminados} contacto(s) incompatibles.",
                        "warning"
                    )
        except Exception:
            # No interrumpir flujo por estado de sesión inconsistente
            pass

        # ------------------ Limpiar dependientes si cambian llaves de configuración ----------
        f1_prev = session.get("frame1") or {}
        if f1_prev and any((
            _upper(datos.get("tipo_tramite"))  != _upper(f1_prev.get("tipo_tramite")),
            _upper(datos.get("tipo_contrato")) != _upper(f1_prev.get("tipo_contrato")),
            _upper(datos.get("tipo_servicio")) != _upper(f1_prev.get("tipo_servicio")),
        )):
            limpiar_dependientes()
            session["frame1_prev"] = f1_prev.copy()
            flash("Se limpiaron Unidades/Cuentas/Usuarios/Contactos por cambio de configuración.", "warning")

        if not datos.get("importe_maximo_dif"):
            datos["importe_maximo_dif"] = "200.01"

        # Persistir captura base en sesión y seguir al frame 2
        session["rdc_reporte"] = (datos.get("tipo_cobro") == "CENTRALIZADO")
        
        session["correo_apoderado_legal"] = datos.get("correo_apoderado_legal", "")
        session.modified = True

        session["frame1"] = {
            **datos,
            "fecha_solicitud": date.today().isoformat(),
        }
        session.modified = True
        return redirect(url_for("frames.frame2"))
    
        # GET: pinta la pantalla con catálogos y estado de sesión actual
    f1 = session.get("frame1") or {}
    editing_id = session.get("editing_solicitud_id")
    
    # GET: pinta la pantalla con catálogos y estado de sesión actual
    return render_template(
        "frame1.html",
        frame1=f1,
        # frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        paso_actual=1,
        catalogo_cpae=catalogo_cpae,
        catalogo_etv=catalogo_etv,
        catalogo_estados=catalogo_estados,
        hay_datos_dependientes=hay_dependientes(),
    )

# -----------------------------------------------------------------------------
# FRAME 2 (Unidades)
# -----------------------------------------------------------------------------
@frames_bp.route("/unidades", methods=["GET", "POST"])
def frame2():
    catalogo_cpae = fetchall("SELECT id, descripcion FROM catalogo_cpae ORDER BY descripcion")
    catalogo_etv = fetchall("SELECT id, descripcion FROM catalogo_etv ORDER BY descripcion")
    catalogo_estados = fetchall("SELECT id, nombre FROM catalogo_estados ORDER BY nombre")

    # Helper para mapear id -> descripción en catálogos
    def _desc_por_id(rows, id_val, label_key):
        if id_val is None or id_val == "":
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

        # Eliminar por índice mostrado en UI
        if "eliminar" in request.form:
            try:
                idx = int(request.form["eliminar"])
            except Exception:
                idx = -1
            unidades = session.get("unidades", [])
            if 0 <= idx < len(unidades):
                unidades.pop(idx)
                session["unidades"] = unidades
                session.modified = True
                flash("Unidad eliminada.", "info")
            return redirect(url_for("frames.frame2"))

        # ============== VALIDACIÓN ALINEADA A UI ==============
        f1 = session.get("frame1") or {}
        tipo_tramite = _upper(f1.get("tipo_tramite"))

        # Lo que marcó el usuario en Frame 1
        sust_mod  = f1.get("sust_mod")  or []  # p.ej. ["UNIDADES", ...]
        sust_crea = f1.get("sust_crea") or []  # p.ej. ["UNIDADES", ...]
        sust_mod  = [(_upper(x) if isinstance(x, str) else x) for x in sust_mod]
        sust_crea = [(_upper(x) if isinstance(x, str) else x) for x in sust_crea]

        # Lo que eligió en el combo de Frame 2 (si existe)
        tipo_movimiento = _upper(request.form.get("tipo_movimiento") or "")
        campo_mod_unidad = _upper(request.form.get("campo_mod_unidad") or "")

        # Decidir qué requiere el backend
        required_keys = set()

        if tipo_tramite == "ALTA":
            # Todos obligatorios “de negocio” menos la terminal
            required_keys.update({"cpae", "nombre_unidad", "tipo_servicio_unidad"})

        elif tipo_tramite in ("SUSTITUCION", "SUSTITUCIÓN"):
            hay_mod_unidades  = "UNIDADES" in sust_mod
            hay_crea_unidades = "UNIDADES" in sust_crea

            if not hay_mod_unidades and not hay_crea_unidades:
                # Sin acción en UNIDADES: dejamos pasar sin requerir nada
                required_keys = set()

            else:
                # Determina movimiento efectivo
                mov_eff = None
                if hay_crea_unidades and not hay_mod_unidades:
                    mov_eff = "ALTA"
                elif hay_mod_unidades and not hay_crea_unidades:
                    # Si hay combo lo usamos; si no, por defecto MODIFICACIÓN
                    mov_eff = ("BAJA" if tipo_movimiento == "BAJA"
                               else "MODIFICACIÓN")
                else:
                    # Caso mixto raro: honra el combo si existe
                    if tipo_movimiento in ("ALTA", "BAJA", "MODIFICACION", "MODIFICACIÓN"):
                        mov_eff = "BAJA" if tipo_movimiento == "BAJA" else ("ALTA" if tipo_movimiento == "ALTA" else "MODIFICACIÓN")

                # Reglas por movimiento
                if mov_eff == "ALTA":
                    required_keys.update({"cpae", "nombre_unidad", "tipo_servicio_unidad"})
                elif mov_eff == "BAJA":
                    required_keys.update({"numero_terminal_sef"})  # solo terminal, resto opcional
                else:
                    # MODIFICACIÓN: terminal es obligatorio SIEMPRE
                    required_keys.update({"numero_terminal_sef"})
                    # Además, el usuario debe elegir el campo puntual a modificar
                    if not campo_mod_unidad:
                        flash("Selecciona el 'Campo a modificar'.", "danger")
                        return redirect(url_for("frames.frame2"))

                    # Mapea selección a campos requeridos
                    mapa_mod = {
                        "NOMBRE_UNIDAD": ["nombre_unidad"],
                        "CPAE": ["cpae"],
                        "SERVICIO_UNIDAD": ["tipo_servicio_unidad"],
                        "ETV": ["empresa_traslado"],
                        "DOMICILIO": ["calle_numero", "colonia", "codigo_postal", "estado", "municipio_id"],
                        "TERM_INTEG": ["terminal_integradora"],
                        "TERM_DOT_CENT": ["terminal_dotacion_centralizada"],
                        "TERM_CERT_CENT": ["terminal_certificado_centralizada"],
                    }
                    extras = mapa_mod.get(campo_mod_unidad, [])
                    required_keys.update(extras)

        else:
            # Sin trámite definido: no bloqueamos aquí
            required_keys = set()

        # Valida faltantes
        faltantes = [k for k in required_keys if not _v(request.form.get(k))]
        if faltantes:
            from markupsafe import escape
            faltantes = [escape(f) for f in faltantes]
            flash(f"Faltan campos obligatorios: {', '.join(faltantes)}", "danger")
            return redirect(url_for("frames.frame2"))

        # ============== DETERMINAR MOVIMIENTO A GUARDAR ==============
        movimiento = "ALTA"
        if tipo_tramite == "ALTA":
            movimiento = "ALTA"
        elif tipo_tramite in ("SUSTITUCION", "SUSTITUCIÓN"):
            hay_mod_unidades  = "UNIDADES" in sust_mod
            hay_crea_unidades = "UNIDADES" in sust_crea
            if hay_crea_unidades and not hay_mod_unidades:
                movimiento = "ALTA"
            elif hay_mod_unidades and not hay_crea_unidades:
                if tipo_movimiento == "BAJA":
                    movimiento = "BAJA"
                elif tipo_movimiento in ("MODIFICACION", "MODIFICACIÓN"):
                    movimiento = "MODIFICACIÓN"
                else:
                    movimiento = "MODIFICACIÓN"
            else:
                if tipo_movimiento == "BAJA":
                    movimiento = "BAJA"
                elif tipo_movimiento == "ALTA":
                    movimiento = "ALTA"
                elif tipo_movimiento in ("MODIFICACION", "MODIFICACIÓN"):
                    movimiento = "MODIFICACIÓN"

        # ============== IDs de catálogo recibidos ==============
        _cpae_id = _v(request.form.get("cpae"))
        _etv_id  = _v(request.form.get("empresa_traslado"))
        _edo_id  = _v(request.form.get("estado"))
        _mun_id  = _v(request.form.get("municipio_id"))

        # Nombres enviados por la forma (si vienen)
        _cpae_nombre_form = _upper(request.form.get("cpae_nombre"))
        _etv_nombre_form  = _upper(request.form.get("etv_nombre"))
        _edo_nombre_form  = _upper(request.form.get("estado_nombre"))
        _mun_nombre_form  = _upper(request.form.get("municipio_nombre"))

        # Resolver en servidor si faltan nombres
        cpae_nombre = _cpae_nombre_form or _upper(_desc_por_id(catalogo_cpae, _cpae_id, "descripcion"))
        etv_nombre  = _etv_nombre_form  or _upper(_desc_por_id(catalogo_etv,  _etv_id,  "descripcion"))
        estado_nombre = _edo_nombre_form or _upper(_desc_por_id(catalogo_estados, _edo_id, "nombre"))

        municipio_nombre = _mun_nombre_form
        if not municipio_nombre and _mun_id:
            rows_mun = fetchall(
                "SELECT nombre FROM catalogo_municipios WHERE id = %s LIMIT 1",
                (int(_digits(_mun_id, 6)),)
            ) or []
            if rows_mun:
                municipio_nombre = _upper(rows_mun[0].get("nombre") if isinstance(rows_mun[0], dict) else rows_mun[0][0])

        # ============== Construir registro de unidad para sesión ==============
        u = {
            "movimiento": movimiento,                 # ALTA / MODIFICACIÓN / BAJA
            "tipo_movimiento": movimiento,            # compat

            "cpae": _cpae_id,
            "cpae_nombre": cpae_nombre,
            "tipo_servicio_unidad": _upper(request.form.get("tipo_servicio_unidad")),
            "etv_nombre": etv_nombre,
            "empresa_traslado": _etv_id,
            "frecuencia_traslado": _v(request.form.get("frecuencia_traslado")),
            "horario_inicio": _v(request.form.get("horario_inicio")),
            "horario_fin": _v(request.form.get("horario_fin")),
            "direccion": _upper(request.form.get("direccion")),
            "entre_calles": _upper(request.form.get("entre_calles")),
            "calle_numero": _upper(request.form.get("calle_numero")),
            "colonia": _upper(request.form.get("colonia")),
            "municipio_id": int(_digits(request.form.get("municipio_id"), 6)) if request.form.get("municipio_id") else None,
            "municipio_nombre": municipio_nombre,
            "estado": int(_digits(request.form.get("estado"), 3)) if request.form.get("estado") else None,
            "estado_nombre": estado_nombre,
            "codigo_postal": _digits(request.form.get("codigo_postal"), 16),
            "nombre_unidad": _upper(request.form.get("nombre_unidad")),
            "numero_terminal_sef": _v(request.form.get("numero_terminal_sef")),
            "terminal_integradora": _v(request.form.get("terminal_integradora")),
            "terminal_dotacion_centralizada": _v(request.form.get("terminal_dotacion_centralizada")),
            "terminal_certificado_centralizada": _v(request.form.get("terminal_certificado_centralizada")),

            # Espejo para compatibilidad
            "tipo_cobro": session.get("frame1", {}).get("tipo_cobro"),
            "servicio": session.get("frame1", {}).get("tipo_servicio"),
            "tipo_unidad": _upper(request.form.get("tipo_servicio_unidad")),
            "tipo_servicio": _upper(request.form.get("tipo_servicio_unidad")),
        }

        # Si el movimiento es BAJA, puedes “sanear” campos no editables
        if movimiento == "BAJA":
            for k in ("cpae","cpae_nombre","tipo_servicio_unidad","empresa_traslado","etv_nombre",
                      "frecuencia_traslado","horario_inicio","horario_fin","direccion","entre_calles",
                      "calle_numero","colonia","municipio_id","municipio_nombre","estado","estado_nombre",
                      "codigo_postal","nombre_unidad"):
                u[k] = u.get(k) or "-"

        unidades = session.get("unidades", [])
        unidades.append(u)
        session["unidades"] = unidades
        session.modified = True
        flash(f"Unidad agregada ({movimiento}).", "success")
        return redirect(url_for("frames.frame2"))

    # GET: muestra unidades capturadas
    return render_template(
        "frame2.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        paso_actual=2,
        catalogo_cpae=catalogo_cpae,
        catalogo_etv=catalogo_etv,
        catalogo_estados=catalogo_estados
    )
# -----------------------------------------------------------------------------
# API MUNICIPIOS
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# FRAME 3 (Cuentas)
# -----------------------------------------------------------------------------
@frames_bp.route("/cuentas", methods=["GET", "POST"])
def frame3():
    if request.method == "POST":
        if "regresar_frame1" in request.form:
            return redirect(url_for("frames.frame1"))
        if "regresar_frame2" in request.form:
            return redirect(url_for("frames.frame2"))

        # Eliminar por índice
        if "eliminar" in request.form:
            try:
                idx = int(request.form["eliminar"])
            except Exception:
                idx = -1
            cuentas = session.get("cuentas", [])
            if 0 <= idx < len(cuentas):
                cuentas.pop(idx)
                session["cuentas"] = cuentas
                session.modified = True
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

        # Captura/normalización
        cuenta = {
            "servicio": _upper(request.form.get("servicio")),
            "sucursal": _v(request.form.get("sucursal")),
            "cuenta": _v(request.form.get("cuenta")),
            "moneda": _upper(request.form.get("moneda")),
            "terminal_aplica": _v(request.form.get("terminal_aplica")),
        }
        cuentas = session.get("cuentas", [])
        cuentas.append(cuenta)
        session["cuentas"] = cuentas
        session.modified = True
        flash("Cuenta agregada.", "success")
        return redirect(url_for("frames.frame3"))

    # GET: catálogo de unidades para mostrar (opcional en tu UI)
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

# -----------------------------------------------------------------------------
# FRAME 4 (Usuarios SEF)
# -----------------------------------------------------------------------------
@frames_bp.route("/usuarios", methods=["GET", "POST"])
def frame4():
    if request.method == "POST":
        if "regresar_frame3" in request.form:
            return redirect(url_for("frames.frame3"))

        # Eliminar por índice
        if "eliminar" in request.form:
            try:
                idx = int(request.form["eliminar"])
            except Exception:
                idx = -1
            usuarios = session.get("usuarios", [])
            if 0 <= idx < len(usuarios):
                usuarios.pop(idx)
                session["usuarios"] = usuarios
                session.modified = True
                flash("Usuario eliminado.", "info")
            return redirect(url_for("frames.frame4"))

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
        session.modified = True
        flash("Usuario agregado.", "success")
        return redirect(url_for("frames.frame4"))

    # GET: catálogo de perfiles si existe en tu BD
    catalogo_perfiles = fetchall("SELECT id, descripcion, perfil FROM catalogo_perfiles ORDER BY perfil")
    return render_template(
        "frame4.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        catalogo_perfiles=catalogo_perfiles,
        paso_actual=4
    )

# -----------------------------------------------------------------------------
# FRAME 5 (Contactos)
# -----------------------------------------------------------------------------
@frames_bp.route("/contactos", methods=["GET", "POST"])
def frame5():
    if request.method == "POST":
        if "regresar_frame4" in request.form:
            return redirect(url_for("frames.frame4"))

        # Eliminar por índice
        if "eliminar" in request.form:
            try:
                idx = int(request.form["eliminar"])
            except Exception:
                idx = -1
            contactos = session.get("contactos", [])
            if 0 <= idx < len(contactos):
                contactos.pop(idx)
                session["contactos"] = contactos
                session.modified = True
                flash("Contacto eliminado.", "info")
            return redirect(url_for("frames.frame5"))

        # Alta de contacto en sesión
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
        session.modified = True
        flash("Contacto agregado.", "success")
        return redirect(url_for("frames.frame5"))

    # GET: muestra contactos y otros bloques capturados (para revisión)
    return render_template(
        "frame5.html",
        frame1=session.get("frame1"),
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        paso_actual=5
    )

# -----------------------------------------------------------------------------
# FINALIZAR
# -----------------------------------------------------------------------------
@frames_bp.route("/finalizar", methods=["GET", "POST"])
def finalizar():
    
    # --- Asegurar que siempre exista solicitud_id en sesión ---
    # Intentamos recuperar el ID desde querystring (cuando vienes desde lista "Ver")
    # o desde valores ya existentes en sesión.
    if not session.get("solicitud_id"):
        raw_id = (
            request.args.get("solicitud_id")
            or request.args.get("id")
            or session.get("solicitud_db_id")
            or session.get("solicitud_actual_id")
        )
        try:
            if raw_id is not None and str(raw_id).strip() != "":
                session["solicitud_id"] = int(raw_id)
        except Exception:
            pass


    def _to_bool(v):
        return str(v).strip().lower() in ("1", "true", "t", "yes", "si")

    def _parse_fecha_ddmmyyyy(s):
        s = (s or "").strip()
        if not s:
            return None
        try:
            return datetime.strptime(s, "%d/%m/%Y").date()
        except Exception:
            return None

    from datetime import datetime  # si no lo tienes ya

    def normaliza_fecha(value):
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

    # -------------------- POST: Confirmar firmantes (solo sesión) --------------------
    if request.method == "POST" and "confirmar_firmantes" in request.form:
        fecha_norm = normaliza_fecha(request.form.get("fecha_firma"))
        apoderado_legal = (request.form.get("apoderado_legal") or "").strip()
        correo_apoderado_legal = (request.form.get("correo_apoderado_legal") or "").strip()
        nombre_aut = (request.form.get("nombre_autorizador") or "").strip()
        puesto_aut = (request.form.get("puesto_autorizador") or "").strip()
        nombre_dir = (request.form.get("nombre_director_divisional") or "").strip()
        puesto_dir = (request.form.get("puesto_director_divisional") or "").strip()

        # Validación mínima (mantén tu regla)
        falta = [x for x in (apoderado_legal, fecha_norm, nombre_aut, puesto_aut, nombre_dir, puesto_dir) if not x]
        if falta:
            flash("Completa todos los campos de firmantes antes de confirmar.", "warning")
            return redirect(url_for("frames.finalizar"))

        # 1) Guardado agrupado
        session["firmantes"] = {
            "apoderado_legal": apoderado_legal,
            "correo_apoderado_legal": correo_apoderado_legal,
            "nombre_autorizador": nombre_aut,
            "puesto_autorizador": puesto_aut,
            "nombre_director_divisional": nombre_dir,
            "puesto_director_divisional": puesto_dir,
            "fecha_firma": fecha_norm,
        }

        # 2) Guardado “legacy” (root keys) para que export/templates lo encuentren sí o sí
        session["apoderado_legal"] = apoderado_legal
        session["correo_apoderado_legal"] = correo_apoderado_legal
        session["nombre_autorizador"] = nombre_aut
        session["puesto_autorizador"] = puesto_aut
        session["nombre_director_divisional"] = nombre_dir
        session["puesto_director_divisional"] = puesto_dir
        session["fecha_firma"] = fecha_norm

        # Banderas de export
        session["firmantes_confirmados"] = True
        session["anexo_usd_14k"] = bool(request.form.get("anexo_usd_14k"))

        f1 = session.get("frame1", {}) or {}
        session["contrato_tradicional"] = (f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "CPAE TRADICIONAL")
        session["contrato_electronico"] = (f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "SEF ELECTRÓNICO")

        session.modified = True
        flash("Solicitud validada. Procede a guardar o exportar.", "success")
        return redirect(url_for("frames.finalizar"))

    # -------------------- POST: Guardar todo en BD --------------------
    if request.method == "POST" and "guardar_todo" in request.form:
        if not session.get("firmantes_confirmados"):
            flash("Primero confirma firmantes antes de guardar.", "warning")
            return redirect(url_for("frames.finalizar"))

        try:
            f1 = session["frame1"]
            unidades = session.get("unidades", [])
            cuentas  = session.get("cuentas", [])
            usuarios = session.get("usuarios", [])
            contactos= session.get("contactos", [])
            editing_id = session.get("editing_solicitud_id")

            # Firmantes desde sesión (tras confirmar)
            apoderado_legal = session.get("apoderado_legal") or f1.get("apoderado_legal")
            
           # Correo apoderado: puede venir en root o dentro de session["firmantes"]
            firm = session.get("firmantes") or {}
            correo_apoderado_legal = (
                (session.get("correo_apoderado_legal") or firm.get("correo_apoderado_legal") or f1.get("correo_apoderado_legal") or "")
            ).strip()
            
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

            with conectar() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                # -------- SOLICITUDES (cabecera) --------
                if editing_id:
                    exec_sql(cur, """
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
                            correo_apoderado_legal = %s,
                            fecha_firma = %s,
                            anexo_usd_14k = %s,
                            contrato_tradicional = %s,
                            contrato_electronico = %s,
                            servicio_solicitado = %s,
                            estatus = %s,
                            nombre_autorizador = %s,
                            nombre_director_divisional = %s,
                            puesto_autorizador = %s,
                            puesto_director_divisional = %s,
                            sust_modo_contrato = %s,
                            sust_modo_registros = %s,
                            sust_op_unidades = %s,
                            sust_op_cuentas = %s,
                            sust_op_usuarios = %s,
                            sust_op_contactos = %s,
                            sust_op_impdif = %s,
                            sust_op_tipocobro = %s
                        WHERE id = %s
                    """, (
                        f1.get("numero_cliente"), f1.get("numero_contrato"),
                        f1.get("razon_social"), f1.get("segmento"),
                        f1.get("tipo_persona"), f1.get("tipo_tramite"),
                        f1.get("tipo_contrato"), f1.get("tipo_servicio"),
                        f1.get("tipo_cobro"), f1.get("importe_maximo_dif"),
                        f1.get("nombre_ejecutivo"), f1.get("domicilio_cliente"),
                        f1.get("telefono_cliente"), session.get("rdc_reporte", False),
                        f1.get("fecha_solicitud"), 6,
                        apoderado_legal, correo_apoderado_legal, fecha_firma_date, anexo_usd,
                        contrato_tradicional, contrato_electronico,
                        f1.get("servicio_solicitado") or "",
                        f1.get("estatus") or "CAPTURADA",
                        nombre_aut1, nombre_aut2, puesto_aut1, puesto_aut2,
                        f1.get("sust_modo_contrato"),f1.get("sust_modo_registros"),
                        f1.get("sust_op_unidades"),f1.get("sust_op_cuentas"),
                        f1.get("sust_op_usuarios"),f1.get("sust_op_contactos"),
                        f1.get("sust_op_impdif"),f1.get("sust_op_tipocobro"),
                        editing_id
                    ))
                    solicitud_id = editing_id
                else:
                    exec_sql(cur, """
                        INSERT INTO solicitudes (
                            numero_cliente, razon_social, segmento, domicilio_cliente,
                            numero_contrato, tipo_tramite, tipo_contrato, tipo_servicio,
                            tipo_cobro, importe_maximo_dif, nombre_ejecutivo,
                            rdc_reporte, created_at, servicio_solicitado,
                            fecha_solicitud, estatus, tipo_persona, created_by,
                            updated_at, paso_actual, telefono_cliente, apoderado_legal, correo_apoderado_legal,
                            fecha_firma, anexo_usd_14k, contrato_tradicional, contrato_electronico,
                            nombre_autorizador, nombre_director_divisional, puesto_autorizador, puesto_director_divisional
                        ) VALUES (
                            %s,%s,%s,%s,
                            %s,%s,%s,%s,
                            %s,%s,%s,
                            %s, now(), %s,
                            %s,%s,%s,%s,
                            now(), %s, %s, %s, %s,
                            %s,%s,%s,%s,
                            %s,%s,%s,%s
                        )
                        RETURNING id
                    """, (
                        f1.get("numero_cliente"), f1.get("razon_social"),
                        f1.get("segmento"), f1.get("domicilio_cliente"),
                        f1.get("numero_contrato"), f1.get("tipo_tramite"),
                        f1.get("tipo_contrato"), f1.get("tipo_servicio"),
                        f1.get("tipo_cobro"), f1.get("importe_maximo_dif"),
                        f1.get("nombre_ejecutivo"),
                        session.get("rdc_reporte", False),
                        f1.get("servicio_solicitado") or "",
                        f1.get("fecha_solicitud"), f1.get("estatus") or "CAPTURADA",
                        f1.get("tipo_persona"), session.get("user_id"),
                        6, f1.get("telefono_cliente"), apoderado_legal, correo_apoderado_legal,
                        fecha_firma_date, anexo_usd, contrato_tradicional, contrato_electronico,
                        nombre_aut1, nombre_aut2, puesto_aut1, puesto_aut2
                    ))
                    solicitud_id = cur.fetchone()["id"]

                # -------- HIJOS: UNIDADES --------
                exec_sql(cur, "DELETE FROM unidades WHERE solicitud_id = %s", (solicitud_id,))
                for u in unidades:
                    exec_sql(cur, """
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
                        u.get("nombre_unidad"), u.get("cpae_nombre"),
                        u.get("tipo_servicio_unidad"),
                        u.get("etv_nombre") or u.get("empresa_traslado"),
                        u.get("numero_terminal_sef"), u.get("calle_numero"), u.get("colonia"),
                        u.get("municipio_nombre"), u.get("estado_nombre"), u.get("codigo_postal"),
                        u.get("terminal_integradora"), u.get("terminal_dotacion_centralizada"),
                        u.get("terminal_certificado_centralizada"),
                        u.get("tipo_cobro"), u.get("servicio"), u.get("tipo_unidad"),
                        u.get("cpae"), u.get("tipo_servicio"),
                        u.get("empresa_traslado"), u.get("municipio_id"), u.get("estado")
                    ))

                # -------- HIJOS: CUENTAS --------
                exec_sql(cur, "DELETE FROM cuentas WHERE solicitud_id = %s", (solicitud_id,))
                for c in cuentas:
                    exec_sql(cur, """
                        INSERT INTO cuentas (
                            solicitud_id, servicio, sucursal, cuenta, moneda, terminal_aplica
                        ) VALUES (%s,%s,%s,%s,%s,%s)
                    """, (
                        solicitud_id, c.get("servicio"), c.get("sucursal"),
                        c.get("cuenta"), c.get("moneda"), c.get("terminal_aplica")
                    ))

                # -------- HIJOS: USUARIOS --------
                exec_sql(cur, "DELETE FROM usuarios WHERE solicitud_id = %s", (solicitud_id,))
                for u in usuarios:
                    exec_sql(cur, """
                        INSERT INTO usuarios (
                            solicitud_id, nombre_usuario, clave_usuario, perfil, maker_checker,
                            correo, telefono, terminal_aplica, tipo_usuario, numero_terminal_sef, role
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        solicitud_id,
                        u.get("nombre_usuario") or u.get("nombre"),
                        u.get("clave_usuario"), u.get("perfil"), u.get("maker_checker"),
                        u.get("correo"), u.get("telefono"), u.get("terminal_aplica"),
                        u.get("tipo_usuario"), u.get("numero_terminal_sef"), u.get("role") or "USER"
                    ))

                # -------- HIJOS: CONTACTOS --------
                exec_sql(cur, "DELETE FROM contactos WHERE solicitud_id = %s", (solicitud_id,))
                for c in contactos:
                    exec_sql(cur, """
                        INSERT INTO contactos (
                            solicitud_id, nombre_contacto, correo, telefono, numero_terminal_sef, tipos_contacto
                        ) VALUES (%s,%s,%s,%s,%s,%s)
                    """, (
                        solicitud_id,
                        c.get("nombre_contacto") or c.get("nombre"),
                        c.get("correo"), c.get("telefono"),
                        c.get("numero_terminal_sef"),
                        c.get("tipos_contacto") if isinstance(c.get("tipos_contacto"), str)
                            else ",".join(c.get("tipos_contacto") or [])
                    ))

            session.pop("editing_solicitud_id", None)
            
            session["correo_apoderado_legal"] = frame1.get("correo_apoderado_legal", "")
            session.modified = True
            return redirect(url_for("solicitudes_portal.lista"))

        except Exception as e:
            flash(f"Error al guardar la solicitud: {e}", "danger")
            return redirect(url_for("frames.finalizar"))

    # -------------------- GET: Cargar solicitud para retomar (opcional) --------------------
    if request.method == "GET" and request.args.get("solicitud_id"):
        try:
            sol_id = int(request.args.get("solicitud_id"))
        except Exception:
            flash("El identificador de la solicitud no es válido.", "danger")
            return redirect(url_for("solicitudes_portal.lista"))

        try:
            with conectar() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Cabecera
                cur.execute("SELECT * FROM solicitudes WHERE id = %s", (sol_id,))
                sol = cur.fetchone()
                if not sol:
                    flash("No se encontró la solicitud indicada.", "warning")
                    return redirect(url_for("solicitudes_portal.lista"))

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
                    "fecha_solicitud": (sol.get("fecha_solicitud").isoformat()
                                        if sol.get("fecha_solicitud") else None),
                    # también conservamos las banderas de sustitución si existen
                    "sustitucion_modo": "CONTRATO" if sol.get("sust_modo_contrato")
                                       else ("REGISTROS" if sol.get("sust_modo_registros") else ""),
                    "sustitucion_registros": ",".join([
                        x for x,flag in [
                            ("UNIDADES", sol.get("sust_op_unidades")),
                            ("CUENTAS", sol.get("sust_op_cuentas")),
                            ("USUARIOS", sol.get("sust_op_usuarios")),
                            ("CONTACTOS", sol.get("sust_op_contactos")),
                            ("IMPDIF", sol.get("sust_op_impdif")),
                            ("TIPOCOBRO", sol.get("sust_op_tipocobro")),
                        ] if flag
                    ])
                }
                session["frame1"] = f1
                session["rdc_reporte"] = bool(sol.get("rdc_reporte"))
                session["anexo_usd_14k"] = bool(sol.get("anexo_usd_14k"))

                # Firmantes para UI
                session["apoderado_legal"] = sol.get("apoderado_legal")
                _ff = sol.get("fecha_firma")
                session["fecha_firma_iso"] = (_ff.isoformat() if _ff else None)
                session["fecha_firma"] = (_ff.strftime("%d/%m/%Y") if _ff else None)
                session["nombre_autorizador"] = sol.get("nombre_autorizador")
                session["puesto_autorizador"] = sol.get("puesto_autorizador")
                session["nombre_director_divisional"] = sol.get("nombre_director_divisional")
                session["puesto_director_divisional"] = sol.get("puesto_director_divisional")

                # Hijos (se mantienen igual)
                cur.execute("SELECT * FROM unidades WHERE solicitud_id = %s ORDER BY id", (sol_id,))
                rows_u = cur.fetchall() or []
                session["unidades"] = [{
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
                    "tipo_cobro": u.get("tipo_cobro"),
                    "servicio": u.get("servicio"),
                    "tipo_unidad": u.get("tipo_unidad"),
                    "cpae": u.get("cpae"),
                    "tipo_servicio": u.get("tipo_servicio"),
                    "empresa_traslado": u.get("empresa_traslado"),
                    "municipio_id": u.get("municipio_id"),
                    "estado": u.get("estado"),
                } for u in rows_u]

                cur.execute("SELECT * FROM cuentas WHERE solicitud_id = %s ORDER BY id", (sol_id,))
                rows_c = cur.fetchall() or []
                session["cuentas"] = [{
                    "servicio": c.get("servicio"),
                    "sucursal": c.get("sucursal"),
                    "cuenta": c.get("cuenta"),
                    "moneda": c.get("moneda"),
                    "terminal_aplica": c.get("terminal_aplica"),
                    "numero_sucursal": c.get("numero_sucursal"),
                    "numero_cuenta": c.get("numero_cuenta"),
                    "terminal_aplicable": c.get("terminal_aplicable"),
                } for c in rows_c]

                cur.execute("SELECT * FROM usuarios WHERE solicitud_id = %s ORDER BY id", (sol_id,))
                rows_us = cur.fetchall() or []
                session["usuarios"] = [{
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
                } for u in rows_us]

                cur.execute("SELECT * FROM contactos WHERE solicitud_id = %s ORDER BY id", (sol_id,))
                rows_ct = cur.fetchall() or []
                session["contactos"] = [{
                    "nombre_contacto": c.get("nombre_contacto") or c.get("nombre"),
                    "correo": c.get("correo"),
                    "telefono": c.get("telefono"),
                    "numero_terminal_sef": c.get("numero_terminal_sef"),
                    "tipos_contacto": c.get("tipos_contacto"),
                } for c in rows_ct]

                session["editing_solicitud_id"] = sol_id
                session.modified = True

        except Exception as e:
            flash(f"No fue posible cargar la solicitud seleccionada: {e}", "danger")
            return redirect(url_for("solicitudes_portal.lista"))

    # GET simple: renderiza resumen para revisión y acciones finales
    return render_template(
        "finalizar.html",
        frame1=session.get("frame1") or {},
        unidades=session.get("unidades", []),
        cuentas=session.get("cuentas", []),
        usuarios=session.get("usuarios", []),
        contactos=session.get("contactos", []),
        paso_actual=6
    )

@frames_bp.route("/formulario/<int:solicitud_id>/<int:step>")
def formulario_step(solicitud_id, step):
    from app.models import Solicitud

    solicitud = Solicitud.query.get_or_404(solicitud_id)

    # aquí decides qué template cargar según step
    template = f"frames/step_{step}.html"

    return render_template(
        template,
        solicitud=solicitud,
        step=step
    )
