# app/services/solicitudes_sef.py
from datetime import datetime
import psycopg2, psycopg2.extras
from ..db_legacy import conectar

def _now_iso():
    return datetime.now().isoformat()

def _coalesce_str(v, default=""):
    return (v or "").strip()

def _list(v):
    return v if isinstance(v, list) else (v or [])

def guardar_solicitud_desde_session(sess) -> int:
    """
    Guarda TODA la solicitud leyendo de session:
      frame1, unidades, cuentas, usuarios, contactos, firmantes
    Reglas:
      - Si existe session["solicitud_id"] -> UPDATE + reemplazo de hijos.
      - Si no existe -> INSERT + guarda id en session["solicitud_id"].
    Devuelve el solicitud_id.
    """
    f1 = sess.get("frame1") or {}
    unidades = sess.get("unidades", [])
    cuentas = sess.get("cuentas", [])
    usuarios = sess.get("usuarios", [])
    contactos = sess.get("contactos", [])
    firmantes = sess.get("firmantes", {})

    # Validación mínima
    req = ("numero_cliente","razon_social","segmento","tipo_tramite","tipo_contrato","tipo_servicio","tipo_cobro","nombre_ejecutivo")
    for k in req:
        if not f1.get(k):
            raise ValueError(f"Falta frame1.{k}")

    created_by = sess.get("username") or "anon"  # si tu columna es INT usa: sess.get("user_id")
    fecha_solicitud = f1.get("fecha_solicitud") or _now_iso()
    solicitud_id = sess.get("solicitud_id")

    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        if solicitud_id:
            # UPDATE maestro
            cur.execute("""
                UPDATE solicitudes SET
                    numero_cliente = %s,
                    numero_contrato = %s,
                    razon_social = %s,
                    segmento = %s,
                    tipo_tramite = %s,
                    tipo_contrato = %s,
                    tipo_servicio = %s,
                    tipo_cobro = %s,
                    importe_maximo_dif = %s,
                    nombre_ejecutivo = %s,
                    fecha_solicitud = NOW(),
                    updated_at = NOW()
                WHERE id = %s
            """, (
                f1["numero_cliente"], _coalesce_str(f1.get("numero_contrato","-")),
                _coalesce_str(f1["razon_social"]), _coalesce_str(f1["segmento"]),
                _coalesce_str(f1["tipo_tramite"]), _coalesce_str(f1["tipo_contrato"]),
                _coalesce_str(f1["tipo_servicio"]), _coalesce_str(f1["tipo_cobro"]),
                _coalesce_str(f1.get("importe_maximo_dif","-")),
                _coalesce_str(f1["nombre_ejecutivo"]),
                solicitud_id
            ))
            # Borra hijos
            cur.execute("DELETE FROM unidades WHERE solicitud_id=%s", (solicitud_id,))
            cur.execute("DELETE FROM cuentas WHERE solicitud_id=%s", (solicitud_id,))
            cur.execute("DELETE FROM usuarios WHERE solicitud_id=%s", (solicitud_id,))
            cur.execute("DELETE FROM contactos WHERE solicitud_id=%s", (solicitud_id,))
        else:
            # INSERT maestro
            cur.execute("""
                INSERT INTO solicitudes
                (numero_cliente, numero_contrato, razon_social, segmento,
                 tipo_tramite, tipo_contrato, tipo_servicio, tipo_cobro,
                 importe_maximo_dif, nombre_ejecutivo, fecha_solicitud,
                 created_by, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW(),%s,NOW(),NOW())
                RETURNING id
            """, (
                f1["numero_cliente"], _coalesce_str(f1.get("numero_contrato","-")),
                _coalesce_str(f1["razon_social"]), _coalesce_str(f1["segmento"]),
                _coalesce_str(f1["tipo_tramite"]), _coalesce_str(f1["tipo_contrato"]),
                _coalesce_str(f1["tipo_servicio"]), _coalesce_str(f1["tipo_cobro"]),
                _coalesce_str(f1.get("importe_maximo_dif","-")),
                _coalesce_str(f1["nombre_ejecutivo"]),
                created_by,
            ))
            solicitud_id = cur.fetchone()["id"]
            sess["solicitud_id"] = solicitud_id

        # Hijos: UNIDADES
        for u in unidades:
            cur.execute("""
                INSERT INTO unidades
                (solicitud_id, nombre_unidad, cpae_nombre, tipo_servicio_unidad, etv_nombre,
                 numero_terminal_sef, calle_numero, colonia, municipio_nombre, estado_nombre,
                 codigo_postal, terminal_integradora, terminal_dotacion_centralizada,
                 terminal_certificado_centralizada, tipo_cobro, servicio, tipo_unidad,
                 cpae, tipo_servicio, empresa_traslado, municipio_id, estado)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id,
                _coalesce_str(u.get("nombre_unidad")),
                _coalesce_str(u.get("cpae_nombre")),
                _coalesce_str(u.get("tipo_servicio_unidad") or u.get("tipo_servicio")),
                _coalesce_str(u.get("etv_nombre")),
                _coalesce_str(u.get("numero_terminal_sef")),
                _coalesce_str(u.get("calle_numero")),
                _coalesce_str(u.get("colonia")),
                _coalesce_str(u.get("municipio_nombre")),
                _coalesce_str(u.get("estado_nombre")),
                _coalesce_str(u.get("codigo_postal")),
                _coalesce_str(u.get("terminal_integradora")),
                _coalesce_str(u.get("terminal_dotacion_centralizada")),
                _coalesce_str(u.get("terminal_certificado_centralizada")),
                _coalesce_str(f1.get("tipo_cobro")),
                _coalesce_str(f1.get("tipo_servicio")),
                _coalesce_str(u.get("tipo_unidad")),
                _coalesce_str(u.get("cpae")),
                _coalesce_str(u.get("tipo_servicio")),
                _coalesce_str(u.get("empresa_traslado")),
                u.get("municipio_id"),
                u.get("estado"),
            ))

        # Hijos: CUENTAS
        for c in cuentas:
            cur.execute("""
                INSERT INTO cuentas
                (solicitud_id, servicio, numero_sucursal, numero_cuenta, moneda, terminal_aplicable)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id,
                _coalesce_str(c.get("servicio")),
                _coalesce_str(c.get("sucursal")),
                _coalesce_str(c.get("cuenta")),
                _coalesce_str(c.get("moneda")),
                _coalesce_str(c.get("terminal_aplica")),
            ))

        # Hijos: USUARIOS
        for u in usuarios:
            cur.execute("""
                INSERT INTO usuarios
                (solicitud_id, nombre_usuario, clave_usuario, perfil, maker_checker, correo,
                 telefono, terminal_aplica, tipo_usuario, numero_terminal_sef, role)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'user')
            """, (
                solicitud_id,
                _coalesce_str(u.get("nombre_usuario")),
                _coalesce_str(u.get("clave_usuario")),
                _coalesce_str(u.get("perfil")),
                _coalesce_str(u.get("maker_checker")),
                _coalesce_str(u.get("correo")),
                _coalesce_str(u.get("telefono")),
                _coalesce_str(u.get("terminal_aplica")),
                _coalesce_str(u.get("tipo_usuario")),
                _coalesce_str(u.get("numero_terminal_sef") or u.get("terminal_aplica")),
            ))

        # Hijos: CONTACTOS
        for c in contactos:
            cur.execute("""
                INSERT INTO contactos
                (solicitud_id, numero_terminal_sef, nombre, telefono, correo, tipo_contacto)
                VALUES (%s,%s,%s,%s,%s,%s)
            """, (
                solicitud_id,
                _coalesce_str(c.get("numero_terminal_sef")),
                _coalesce_str(c.get("nombre_contacto")),
                _coalesce_str(c.get("telefono")),
                _coalesce_str(c.get("correo")),
                _list(c.get("tipos_contacto")),
            ))

        # Firmantes (opcional: si existe tabla, persiste; si no, ignora)
        try:
            cur.execute("""
                INSERT INTO solicitudes_firmantes
                (solicitud_id, apoderado_legal, nombre_autorizador, nombre_director_divisional,
                 puesto_autorizador, puesto_director_divisional, fecha_firma, anexo_usd_14k)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (solicitud_id) DO UPDATE SET
                    apoderado_legal = EXCLUDED.apoderado_legal,
                    nombre_autorizador = EXCLUDED.nombre_autorizador,
                    nombre_director_divisional = EXCLUDED.nombre_director_divisional,
                    puesto_autorizador = EXCLUDED.puesto_autorizador,
                    puesto_director_divisional = EXCLUDED.puesto_director_divisional,
                    fecha_firma = EXCLUDED.fecha_firma,
                    anexo_usd_14k = EXCLUDED.anexo_usd_14k
            """, (
                solicitud_id,
                _coalesce_str(firmantes.get("apoderado_legal")),
                _coalesce_str(firmantes.get("nombre_autorizador")),
                _coalesce_str(firmantes.get("nombre_director_divisional")),
                _coalesce_str(firmantes.get("puesto_autorizador")),
                _coalesce_str(firmantes.get("puesto_director_divisional")),
                _coalesce_str(firmantes.get("fecha_firma")),
                bool(firmantes.get("anexo_usd_14k")),
            ))
        except psycopg2.errors.UndefinedTable:
            conn.rollback()  # limpia el error y seguimos sin persistir firmantes
        return solicitud_id


def cargar_solicitud_a_session(solicitud_id: int, sess) -> None:
    """
    Lee solicitud + hijos desde BD y popular session:
      session["solicitud_id"], frame1, unidades, cuentas, usuarios, contactos, firmantes
    """
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT id, numero_cliente, numero_contrato, razon_social, segmento,
                   tipo_tramite, tipo_contrato, tipo_servicio, tipo_cobro,
                   importe_maximo_dif, nombre_ejecutivo,
                   COALESCE(TO_CHAR(updated_at,'YYYY-MM-DD HH24:MI'), TO_CHAR(created_at,'YYYY-MM-DD HH24:MI')) AS actualizado
            FROM solicitudes
            WHERE id=%s
        """, (solicitud_id,))
        s = cur.fetchone()
        if not s:
            raise ValueError("Solicitud no encontrada")

        sess["solicitud_id"] = s["id"]
        sess["frame1"] = {
            "numero_cliente": s["numero_cliente"],
            "numero_contrato": s["numero_contrato"],
            "razon_social": s["razon_social"],
            "segmento": s["segmento"],
            "tipo_tramite": s["tipo_tramite"],
            "tipo_contrato": s["tipo_contrato"],
            "tipo_servicio": s["tipo_servicio"],
            "tipo_cobro": s["tipo_cobro"],
            "importe_maximo_dif": s["importe_maximo_dif"],
            "nombre_ejecutivo": s["nombre_ejecutivo"],
            "fecha_solicitud": _now_iso(),
        }

        cur.execute("SELECT * FROM unidades WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
        sess["unidades"] = list(cur.fetchall())

        cur.execute("SELECT * FROM cuentas WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
        sess["cuentas"] = list(cur.fetchall())

        cur.execute("SELECT * FROM usuarios WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
        sess["usuarios"] = list(cur.fetchall())

        cur.execute("SELECT * FROM contactos WHERE solicitud_id=%s ORDER BY id", (solicitud_id,))
        rows_c = cur.fetchall()
        # normaliza tipo_contacto si viene como texto
        for r in rows_c:
            if isinstance(r.get("tipo_contacto"), str):
                r["tipo_contacto"] = [r["tipo_contacto"]]
        sess["contactos"] = list(rows_c)

        # firmantes (si existe tabla) -> session; si no, deja lo que tenga
        try:
            cur.execute("""
                SELECT apoderado_legal, nombre_autorizador, nombre_director_divisional,
                       puesto_autorizador, puesto_director_divisional,
                       fecha_firma, anexo_usd_14k
                FROM solicitudes_firmantes WHERE solicitud_id=%s
            """, (solicitud_id,))
            f = cur.fetchone()
            if f:
                sess["firmantes"] = {
                    "apoderado_legal": f["apoderado_legal"],
                    "nombre_autorizador": f["nombre_autorizador"],
                    "nombre_director_divisional": f["nombre_director_divisional"],
                    "puesto_autorizador": f["puesto_autorizador"],
                    "puesto_director_divisional": f["puesto_director_divisional"],
                    "fecha_firma": f["fecha_firma"],
                    "anexo_usd_14k": f["anexo_usd_14k"],
                }
        except psycopg2.errors.UndefinedTable:
            pass
