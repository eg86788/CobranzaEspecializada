# app/__init__.py
import os
from pathlib import Path
from datetime import timedelta
from flask_migrate import Migrate
from app.extensions import db


import psycopg2.extras
from flask import Flask, session, redirect, url_for

from app.extensions import db
from .config import Config
from .db_legacy import conectar, fetchall  # si lo usas en otros módulos, se queda
from .errors import register_error_handlers
from .blueprints.solicitudes_portal import sol_portal
from .blueprints.params_admin import params_bp  # módulo de parámetros
from app.blueprints.config_campos_admin import config_campos_admin_bp

def create_app():
    app = Flask(__name__)

    # CONFIGURACIÓN DIRECTA
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://edgargarcia:Robert2025@localhost:5432/postgres"

    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev"

    db.init_app(app)
    Migrate.init_app(app, db)

    from app import models  # importante

    # blueprints...
    from .blueprints.frames import frames_bp
    from .blueprints.minutas import minutas_bp
    from .blueprints.solicitudes_portal import solicitudes_portal_bp

    app.register_blueprint(frames_bp)
    app.register_blueprint(minutas_bp)
    app.register_blueprint(solicitudes_portal_bp)

    return app
