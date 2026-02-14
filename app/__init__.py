# app/__init__.py
import os
from pathlib import Path
from datetime import timedelta

from flask import Flask
from flask_migrate import Migrate
from app.extensions import db

# Crear instancia de Migrate
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # CONFIGURACIÓN DIRECTA
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://edgargarcia:Robert2025@localhost:5432/postgres"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev"

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # Importar modelos para que Alembic los detecte
    from app import models  # noqa

    # Registrar blueprints
    from .blueprints.frames import frames_bp
    from .blueprints.minutas import minutas_bp
    from .blueprints.solicitudes_portal import solicitudes_portal_bp

    app.register_blueprint(frames_bp)
    app.register_blueprint(minutas_bp)
    app.register_blueprint(solicitudes_portal_bp)

    return app
