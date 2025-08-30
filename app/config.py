# app/config.py
# Configuración centralizada de la app (keys, DB y flags).

import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    DB_CONFIG = {
        "dbname": os.getenv("DB_NAME", "postgres"),
        "user": os.getenv("DB_USER", "edgargarcia"),
        "password": os.getenv("DB_PASSWORD", "Robert2025"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
    }
    # Modo debug lo decides en run.py
