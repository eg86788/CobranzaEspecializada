# app/blueprints/solicitudes_portal.py
from flask import Blueprint, render_template, redirect, url_for, session, request, flash, abort
import psycopg2.extras
from ..db_legacy import conectar

sol_portal = Blueprint("sol_portal", __name__, url_prefix="/mis-solicitudes")

# --- helpers ---
def _user_required():
    if session.get("role") != "user":
        flash("Debes iniciar sesión de usuario.", "warning")
        return False
    return True

def _fetchone(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchone()

def _fetchall(q, p=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(q, p)
        return cur.fetchall()

def _load_solicitud_to_session(solicitud_id: int):
    """
    Carga en session: frame1, unidades, cuentas, usuarios, contactos desde BD.
    Adaptado a tus tablas reales: usuarios, unidades.
    """
    uid = session.get("user_id")
    if not uid:
        raise ValueError("Sesión expirada.")

    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # ---- solicitud principal -> frame1
        cur.execute("""
            SELECT
              numero_cliente, numero_contrato, razon_social, segmento,
              tipo_persona, tipo_tramite, tipo_contrato, tipo_servicio,
              nombre_ejecutivo, tipo_cobro,
              COALESCE(importe_maximo_dif,'-') AS importe_maximo_dif,
              COALESCE(telefono_cliente,'') AS telefono_cliente,
              COALESCE(domicilio_cliente,'') AS domicilio_cliente,
              fecha_solicitud, estatus, paso_actual
            FROM solicitudes
            WHERE id=%s AND created_by=%s
        """, (solicitud_id, uid))
        s = cur.fetchone()
        if not s:
            raise ValueError("Solicitud no encontrada o no pertenece al usuario.")

        session["frame1"] = dict(s)

        # ---- UNIDADES (tus columnas reales)
        cur.execute("""
            SELECT
              tipo_cobro, servicio, tipo_unidad, numero_terminal_sef,
              nombre_unidad,
              cpae, cpae_nombre,
              tipo_servicio, tipo_servicio_unidad,
              empresa_traslado, etv_nombre,
              calle_numero, colonia, municipio_id, municipio_nombre,
              estado, estado_nombre, codigo_postal,
              terminal_integradora, terminal_dotacion_centralizada,
              terminal_certificado_centralizada
            FROM unidades
            WHERE solicitud_id=%s
            ORDER BY id
        """, (solicitud_id,))
        unidades_db = cur.fetchall()
        unidades_sess = []
        for r in unidades_db:
            unidades_sess.append({
                # claves que usan tus frames:
                "tipo_cobro": r["tipo_cobro"],
                "servicio": r["servicio"],
                "tipo_unidad": r["tipo_unidad"],
                "numero_terminal_sef": r["numero_terminal_sef"],
                "nombre_unidad": r["nombre_unidad"],
                "cpae": r["cpae"],
                "tipo_servicio": r["tipo_servicio"],
                "empresa_traslado": r["empresa_traslado"],
                "calle_numero": r["calle_numero"],
                "colonia": r["colonia"],
                "municipio_id": r["municipio_id"],
                "estado": r["estado"],
                "codigo_postal": r["codigo_postal"],
                "terminal_integradora": r["terminal_integradora"],
                "terminal_dotacion_centralizada": r["terminal_dotacion_centralizada"],
                "terminal_certificado_centralizada": r["terminal_certificado_centralizada"],
                # extras de “nombre bonito” (no estorban en sesión)
                "cpae_nombre": r["cpae_nombre"],
                "tipo_servicio_unidad": r["tipo_servicio_unidad"],
                "etv_nombre": r["etv_nombre"],
                "municipio_nombre": r["municipio_nombre"],
                "estado_nombre": r["estado_nombre"],
            })
        session["unidades"] = unidades_sess

        # ---- CUENTAS (asumo tu tabla es 'cuentas' con estas columnas)
        cur.execute("""
            SELECT servicio, numero_sucursal AS sucursal, numero_cuenta AS cuenta,
                   moneda, terminal_aplicable AS terminal_aplica
            FROM cuentas
            WHERE solicitud_id=%s
            ORDER BY id
        """, (solicitud_id,))
        session["cuentas"] = [dict(r) for r in cur.fetchall()]

        # ---- USUARIOS (tus columnas reales)
        cur.execute("""
            SELECT
              tipo_usuario,
              numero_terminal_sef,
              terminal_aplica,
              nombre_usuario,
              clave_usuario,
              perfil,
              maker_checker,
              correo,
              telefono
            FROM usuarios
            WHERE solicitud_id=%s
            ORDER BY id
        """, (solicitud_id,))
        usuarios_db = cur.fetchall()
        usuarios_sess = []
        for u in usuarios_db:
            usuarios_sess.append({
                "tipo_usuario": u["tipo_usuario"],
                # tus capturas aceptan una u otra:
                "numero_terminal_sef": u["numero_terminal_sef"],
                "terminal_aplica": u["terminal_aplica"],
                "nombre_usuario": u["nombre_usuario"],
                "clave_usuario": u["clave_usuario"],
                "perfil": u["perfil"],
                "maker_checker": u["maker_checker"],
                "correo": u["correo"],
                "telefono": u["telefono"],
                # en tu tabla no hay montos → deja None
                "monto_mxn": None,
                "monto_usd": None,
            })
        session["usuarios"] = usuarios_sess

        # ---- CONTACTOS (asumo tu tabla 'contactos' con estas columnas)
        cur.execute("""
            SELECT
              numero_terminal_sef,
              nombre AS nombre_contacto,
              telefono,
              correo,
              tipo_contacto AS tipos_contacto
            FROM contactos
            WHERE solicitud_id=%s
            ORDER BY id
        """, (solicitud_id,))
        session["contactos"] = [dict(r) for r in cur.fetchall()]

        # banderas usadas en exportar
        f1 = session.get("frame1", {})
        session["anexo_usd_14k"] = any(c.get("moneda") == "USD" for c in session.get("cuentas", []))
        session["contrato_tradicional"] = (f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "CPAE TRADICIONAL")
        session["contrato_electronico"] = (f1.get("tipo_tramite") == "ALTA" and f1.get("tipo_contrato") == "SEF ELECTRÓNICO")

        return s.get("paso_actual", 1)

# --- rutas ---
@sol_portal.route("/")
def listar():
    if not _user_required():
        return redirect(url_for("auth_admin.login", next=request.path))

    estatus = request.args.get("estatus")  # opcional
    params = [session.get("user_id")]
    where = "WHERE s.created_by=%s"
    if estatus:
        where += " AND s.estatus=%s"
        params.append(estatus)

    rows = _fetchall(f"""
        SELECT
          s.id, s.numero_cliente, s.razon_social, s.segmento,
          s.tipo_tramite, s.tipo_contrato, s.tipo_servicio,
          s.estatus, s.paso_actual,
          to_char(s.created_at, 'YYYY-MM-DD HH24:MI') AS creado,
          to_char(s.updated_at, 'YYYY-MM-DD HH24:MI') AS actualizado
        FROM solicitudes s
        {where}
        ORDER BY s.updated_at DESC
        LIMIT 200
    """, tuple(params))

    return render_template("solicitudes/lista.html", items=rows, estatus=estatus)

@sol_portal.route("/<int:solicitud_id>")
def detalle(solicitud_id):
    if not _user_required():
        return redirect(url_for("auth_admin.login", next=request.path))

    sol = _fetchone("""
        SELECT
          s.*,
          to_char(s.created_at, 'YYYY-MM-DD HH24:MI') AS creado_fmt,
          to_char(s.updated_at, 'YYYY-MM-DD HH24:MI') AS actualizado_fmt
        FROM solicitudes s
        WHERE s.id=%s AND s.created_by=%s
    """, (solicitud_id, session.get("user_id")))
    if not sol:
        abort(404)

    unidades = _fetchall("SELECT * FROM unidades WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
    cuentas  = _fetchall("SELECT * FROM cuentas  WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
    usuarios = _fetchall("SELECT * FROM usuarios WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
    contactos= _fetchall("SELECT * FROM contactos WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))

    return render_template("solicitudes/detalle.html",
                           sol=sol, unidades=unidades, cuentas=cuentas, usuarios=usuarios, contactos=contactos)

@sol_portal.route("/<int:solicitud_id>/retomar")
def retomar(solicitud_id):
    if not _user_required():
        return redirect(url_for("auth_admin.login", next=request.path))
    try:
        paso = _load_solicitud_to_session(solicitud_id)
        destino = {
            1: "frames.frame1",
            2: "frames.frame2",
            3: "frames.frame3",
            4: "frames.frame4",
            5: "frames.frame5",
            6: "exportar.exportar_pdf",
        }.get(int(paso or 1), "frames.frame1")
        flash("Solicitud cargada. Puedes continuar la captura.", "success")
        return redirect(url_for(destino))
    except Exception as e:
        flash(f"No fue posible cargar la solicitud: {e}", "danger")
        return redirect(url_for("sol_portal.listar"))
