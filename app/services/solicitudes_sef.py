# app/services/solicitudes_sef.py
from datetime import datetime
from ..db_legacy import conectar

def guardar_solicitud_desde_session(sess) -> int:
    """
    Lee frame1, unidades, cuentas, usuarios, contactos de session
    y guarda todo en BD en una transacción. Devuelve solicitud_id.
    """
    f1 = sess.get("frame1") or {}
    unidades = sess.get("unidades", [])
    cuentas = sess.get("cuentas", [])
    usuarios = sess.get("usuarios", [])
    contactos = sess.get("contactos", [])

    # VALIDACIONES MÍNIMAS (según lo que capturas en frame1)
    requeridos = (
        "numero_cliente","razon_social","segmento","tipo_persona",
        "tipo_tramite","tipo_contrato","tipo_servicio","tipo_cobro",
        "nombre_ejecutivo","fecha_solicitud"
    )
    for k in requeridos:
        if not f1.get(k):
            raise ValueError(f"Falta frame1.{k}")

    # normaliza algunos opcionales
    numero_contrato = f1.get("numero_contrato") or "-"
    importe_maximo_dif = f1.get("importe_maximo_dif") or "-"

    with conectar() as conn, conn.cursor() as cur:
        # ---------------- SOLICITUDES ----------------
        # columnas: número de cliente/contrato, razón social, segmento, tipo_persona,
        # tipo_trámite, tipo_contrato, tipo_servicio, tipo_cobro, importe_max_dif,
        # nombre_ejecutivo, fecha_solicitud, estatus
        cur.execute("""
            INSERT INTO solicitudes
            (numero_cliente, numero_contrato, razon_social, segmento,
             tipo_persona, tipo_tramite, tipo_contrato, tipo_servicio,
             tipo_cobro, importe_maximo_dif, nombre_ejecutivo,
             fecha_solicitud, estatus)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Registrada')
            RETURNING id
        """, (
            int(f1["numero_cliente"]), numero_contrato, f1["razon_social"], f1["segmento"],
            f1["tipo_persona"], f1["tipo_tramite"], f1["tipo_contrato"], f1["tipo_servicio"],
            f1["tipo_cobro"], importe_maximo_dif, f1["nombre_ejecutivo"],
            f1["fecha_solicitud"],
        ))
        solicitud_id = cur.fetchone()[0]

        # ---------------- UNIDADES ----------------
        # columnas según lo que guardas desde frame2 (usa los mismos nombres)
        # tabla: unidades
        for u in unidades:
            cur.execute("""
                INSERT INTO unidades
                (solicitud_id,
                 numero_terminal_sef, nombre_unidad, cpae,
                 tipo_servicio_unidad, empresa_traslado,
                 calle_numero, colonia, municipio_id, estado, codigo_postal,
                 terminal_integradora, terminal_dotacion_centralizada, terminal_certificado_centralizada)
                VALUES
                (%s, %s, %s, %s,
                 %s, %s,
                 %s, %s, %s, %s, %s,
                 %s, %s, %s)
            """, (
                solicitud_id,
                u.get("numero_terminal_sef"), u.get("nombre_unidad"), u.get("cpae"),
                u.get("tipo_servicio_unidad"), u.get("empresa_traslado"),
                u.get("calle_numero"), u.get("colonia"), u.get("municipio_id"),
                u.get("estado"), u.get("codigo_postal"),
                u.get("terminal_integradora"), u.get("terminal_dotacion_centralizada"),
                u.get("terminal_certificado_centralizada"),
            ))

        # ---------------- CUENTAS ----------------
        # columnas según frame3: servicio, sucursal, cuenta, moneda, terminal_aplica
        for c in cuentas:
            cur.execute("""
                INSERT INTO cuentas
                (solicitud_id, servicio, sucursal, cuenta, moneda, terminal_aplica)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id, c["servicio"], c["sucursal"], c["cuenta"],
                c["moneda"], c["terminal_aplica"]
            ))

        # ---------------- USUARIOS ----------------
        # columnas según frame4: tipo_usuario, numero_terminal_sef (o terminal_aplica),
        # nombre_usuario, clave_usuario, perfil, maker_checker, correo, telefono,
        # monto_mxn, monto_usd
        for u in usuarios:
            cur.execute("""
                INSERT INTO usuarios
                (solicitud_id, tipo_usuario, numero_terminal_sef, nombre_usuario,
                 clave_usuario, perfil, maker_checker, correo, telefono)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id,
                u["tipo_usuario"],
                (u.get("numero_terminal_sef") or u.get("terminal_aplica")),
                u["nombre_usuario"], u["clave_usuario"], u["perfil"],
                u["maker_checker"], u["correo"], u["telefono"],
            ))

        # ---------------- CONTACTOS ----------------
        # columnas según frame5: numero_terminal_sef, nombre_contacto, telefono,
        # correo, tipos_contacto (text[] en la BD)
        for c in contactos:
            cur.execute("""
                INSERT INTO contactos
                (solicitud_id, numero_terminal_sef, nombre_contacto, telefono, correo, tipos_contacto)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id,
                c.get("numero_terminal_sef"),
                c["nombre_contacto"], c["telefono"], c["correo"],
                c.get("tipos_contacto", []),  # psycopg2 convierte list -> text[]
            ))

        # commit lo hace el context manager
        return solicitud_id
