# app/db_legacy.py
import os
import re
from contextlib import contextmanager
import psycopg2
import psycopg2.extras

try:
    from flask import current_app
except Exception:
    current_app = None  # por si se usa fuera de Flask


def _get_config(key, default=None):
    """Busca primero en app.config, luego en variables de entorno."""
    try:
        if current_app:
            app = current_app._get_current_object()
            if key in app.config and app.config[key] is not None:
                return app.config[key]
    except Exception:
        pass
    return os.getenv(key, default)


def _normalize_database_url(url: str) -> str:
    """
    Normaliza DATABASE_URL para que psycopg2 lo acepte.
    - postgresql+psycopg2://...  -> postgresql://...
    - postgres://...            -> postgresql://...
    """
    if not url:
        return url

    u = url.strip()

    # Formato SQLAlchemy: postgresql+psycopg2://...
    u = re.sub(r"^postgresql\+psycopg2://", "postgresql://", u, flags=re.IGNORECASE)

    # Formato antiguo: postgres://...
    u = re.sub(r"^postgres://", "postgresql://", u, flags=re.IGNORECASE)

    return u


def _build_dsn_from_parts():
    host = _get_config("DB_HOST", "127.0.0.1")
    port = _get_config("DB_PORT", "5432")
    name = _get_config("DB_NAME", None)
    user = _get_config("DB_USER", None)
    pwd = _get_config("DB_PASSWORD", None)

    parts = [f"host={host}", f"port={port}"]
    if name:
        parts.append(f"dbname={name}")
    if user:
        parts.append(f"user={user}")
    if pwd:
        parts.append(f"password={pwd}")
    return " ".join(parts)


def _get_dsn():
    # 1) Cadena completa si existe (preferida)
    url = _get_config("DATABASE_URL", None)

    # 1b) Fallback: algunas configuraciones solo definen SQLALCHEMY_DATABASE_URI
    if not url:
        url = _get_config("SQLALCHEMY_DATABASE_URI", None)

    if url:
        return _normalize_database_url(url)

    # 2) Construir DSN por partes
    return _build_dsn_from_parts()


@contextmanager
def conectar():
    dsn = _get_dsn()
    conn = psycopg2.connect(dsn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetchall(sql, params=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetchone(sql, params=()):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def execute(sql, params=(), returning=False):
    with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, params)
        if returning:
            return cur.fetchone()
        return None
