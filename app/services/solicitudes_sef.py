# app/services/solicitudes_sef.py
from ..db_legacy import conectar
import psycopg2.extras  # ← IMPORTANTE

def guardar_solicitud_desde_session(sess) -> int:
    f1 = sess.get("frame1") or {}
    unidades = sess.get("unidades", [])
    cuentas = sess.get("cuentas", [])
    usuarios = sess.get("usuarios", [])
    contactos = sess.get("contactos", [])

    created_by = sess.get("user_id")
    if not created_by:
        raise ValueError("Sesión expirada: falta user_id en session.")

    requeridos = ("numero_cliente","razon_social","segmento",
                  "tipo_tramite","tipo_servicio","nombre_ejecutivo","fecha_solicitud")
    for k in requeridos:
        if not f1.get(k):
            raise ValueError(f"Falta frame1.{k}")

    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        # ---------- SOLICITUD ----------
        cur.execute("""
            INSERT INTO solicitudes
            (numero_cliente, numero_contrato, razon_social, segmento,
             tipo_persona, tipo_tramite, tipo_contrato, tipo_servicio,
             nombre_ejecutivo, tipo_cobro, importe_maximo_dif,
             telefono_cliente, domicilio_cliente,
             fecha_solicitud, estatus, paso_actual,
             created_by, created_at, updated_at)
            VALUES
            (%s,%s,%s,%s,
             %s,%s,%s,%s,
             %s,%s,%s,
             %s,%s,
             %s,'Registrada', %s,
             %s, NOW(), NOW())
            RETURNING id
        """, (
            f1["numero_cliente"], f1.get("numero_contrato","-"), f1["razon_social"], f1["segmento"],
            f1.get("tipo_persona"), f1["tipo_tramite"], f1.get("tipo_contrato"), f1["tipo_servicio"],
            f1["nombre_ejecutivo"], f1.get("tipo_cobro"), f1.get("importe_maximo_dif"),
            f1.get("telefono_cliente"), f1.get("domicilio_cliente"),
            f1["fecha_solicitud"], int(f1.get("paso_actual") or 1),
            created_by
        ))
        row = cur.fetchone()
        solicitud_id = row["id"] if isinstance(row, dict) else row[0]  # ← fallback seguro

        # ---------- UNIDADES ----------
        for u in unidades:
            cur.execute("""
                INSERT INTO unidades
                (solicitud_id,
                 nombre_unidad, cpae_nombre, tipo_servicio_unidad, etv_nombre,
                 numero_terminal_sef, calle_numero, colonia,
                 municipio_nombre, estado_nombre, codigo_postal,
                 terminal_integradora, terminal_dotacion_centralizada, terminal_certificado_centralizada,
                 tipo_cobro, servicio, tipo_unidad, cpae, tipo_servicio, empresa_traslado,
                 municipio_id, estado)
                VALUES
                (%s,
                 %s,%s,%s,%s,
                 %s,%s,%s,
                 %s,%s,%s,
                 %s,%s,%s,
                 %s,%s,%s,%s,%s,%s,
                 %s,%s)
            """, (
                solicitud_id,
                u.get("nombre_unidad"), u.get("cpae_nombre"), u.get("tipo_servicio_unidad"), u.get("etv_nombre"),
                u.get("numero_terminal_sef"), u.get("calle_numero"), u.get("colonia"),
                u.get("municipio_nombre"), u.get("estado_nombre"), u.get("codigo_postal"),
                u.get("terminal_integradora"), u.get("terminal_dotacion_centralizada"), u.get("terminal_certificado_centralizada"),
                u.get("tipo_cobro") or f1.get("tipo_cobro"), u.get("servicio") or f1.get("tipo_servicio"),
                u.get("tipo_unidad"), u.get("cpae"), u.get("tipo_servicio") or f1.get("tipo_servicio"),
                u.get("empresa_traslado"),
                u.get("municipio_id"), u.get("estado"),
            ))

        # ---------- CUENTAS ----------
        for c in cuentas:
            cur.execute("""
                INSERT INTO cuentas
                (solicitud_id, servicio, numero_sucursal, numero_cuenta, moneda, terminal_aplicable)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id, c.get("servicio"), c.get("sucursal"),
                c.get("cuenta"), c.get("moneda"), c.get("terminal_aplica")
            ))

        # ---------- USUARIOS ----------
        for u in usuarios:
            cur.execute("""
                INSERT INTO usuarios
                (solicitud_id, nombre_usuario, clave_usuario, perfil, maker_checker,
                 correo, telefono, terminal_aplica, tipo_usuario, numero_terminal_sef, role)
                VALUES
                (%s,%s,%s,%s,%s,
                 %s,%s,%s,%s,%s,'user')
            """, (
                solicitud_id, u.get("nombre_usuario"), u.get("clave_usuario"), u.get("perfil"), u.get("maker_checker"),
                u.get("correo"), u.get("telefono"), u.get("terminal_aplica"), u.get("tipo_usuario"),
                (u.get("numero_terminal_sef") or u.get("terminal_aplica")),
            ))

        # ---------- CONTACTOS ----------
        for c in contactos:
            cur.execute("""
                INSERT INTO contactos
                (solicitud_id, numero_terminal_sef, nombre, telefono, correo, tipo_contacto)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id, c.get("numero_terminal_sef"),
                c.get("nombre_contacto"), c.get("telefono"),
                c.get("correo"), c.get("tipos_contacto"),
            ))

        return solicitud_id
