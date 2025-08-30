import psycopg2.extras
from ..db_legacy import conectar
from datetime import datetime

def numero_adhesion(clave: str, fecha_str: str | None) -> str | None:
    """Devuelve el número vigente para 'clave' en 'fecha_str' (YYYY-MM-DD)."""
    fecha = (fecha_str or "").strip() or datetime.now().strftime("%Y-%m-%d")
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT numero FROM catalogo_adhesiones
            WHERE clave=%s
              AND activo=TRUE
              AND vigente_desde <= %s
              AND (vigente_hasta IS NULL OR vigente_hasta >= %s)
            ORDER BY vigente_desde DESC
            LIMIT 1
        """, (clave, fecha, fecha))
        row = cur.fetchone()
        if row: return row["numero"]
        # sin match exacto: trae el más reciente activo como fallback
        cur.execute("""
            SELECT numero FROM catalogo_adhesiones
            WHERE clave=%s AND activo=TRUE
            ORDER BY vigente_desde DESC
            LIMIT 1
        """, (clave,))
        row = cur.fetchone()
        return row["numero"] if row else None
