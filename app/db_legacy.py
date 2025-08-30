# app/db.py
# Capa delgada para conexión a PostgreSQL y helpers de consulta.

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import current_app

def conectar():
    cfg = current_app.config["DB_CONFIG"]
    return psycopg2.connect(**cfg)

def fetchall(query, params=None):
    with conectar() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchall()

def fetchone(query, params=None):
    with conectar() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            return cur.fetchone()

def execute(query, params=None, returning=False):
    with conectar() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if returning:
                row = cur.fetchone()
                conn.commit()
                return row
            conn.commit()
