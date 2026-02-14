# app/__init__.py
import os
from pathlib import Path
from datetime import timedelta
from .config import Config

from flask import Flask, redirect, session, url_for
from flask_migrate import Migrate
from app.extensions import db

# Crear instancia de Migrate
migrate = Migrate()

def create_app():
    from pathlib import Path



    BASE_DIR = Path(__file__).resolve().parent

    app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static")
    )

    print("TEMPLATE FOLDER:", app.template_folder)

  # ----- Config -----
    app.config.from_object(Config)

    # Usa la URI de Config si ya la tienes; si no, toma una por defecto.
    # OJO: NUNCA dejes espacios en blanco en la URI.
    app.config.setdefault(
        "SQLALCHEMY_DATABASE_URI",
        # Ejemplo correcto SIN espacios:
        os.getenv("DATABASE_URL", "postgresql+psycopg2://edgargarcia:@localhost:5432/postgres")
    )
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    app.config.setdefault("INIT_DB", False)

    # Sesión
    app.secret_key = app.config.get("SECRET_KEY", "clave-super-secreta")
    app.config["SESSION_PERMANENT"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False  # ponlo True si usas HTTPS

    # CONFIGURACIÓN DIRECTA
    app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://edgargarcia:Robert2025@localhost:5432/postgres"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "dev"

    # Inicializar extensiones
    db.init_app(app)
    migrate.init_app(app, db)

    # ----- Filtros Jinja -----
    from .filters import register_filters
    register_filters(app)

        # ----- Context processors (disponibles en todos los templates) -----
    @app.context_processor
    def inject_user():
        return {
            "current_role": session.get("role"),
            "current_user_name": session.get("fullname") or session.get("username")
        }
    
    # Importar modelos para que Alembic los detecte
    from app import models  # noqa

    # Registrar blueprints

  # ----- Blueprints -----
    from .blueprints.core import core_bp
    from .blueprints.directorio import directorio_bp
    from .blueprints.frames import frames_bp
    from .blueprints.exportar import exportar_bp
    from .blueprints.catalogos import catalogos_bp
    from .blueprints.api import api_bp
    from .blueprints.users_admin import users_admin


    # Login (admin/user) y panel admin
    from .blueprints.auth_admin import auth_bp         # name interno = "auth_admin"
    from .blueprints.admin_portal import admin_portal  # name interno = "admin_portal"

    from .blueprints.frames import frames_bp
    from .blueprints.minutas import minutas_bp
    from .blueprints.templates_admin import templates_bp
    from .blueprints.adhesiones_admin import adh_bp
    from .blueprints.solicitudes_portal import sol_portal
    from .blueprints.params_admin import params_bp  # módulo de parámetros
    from .blueprints.solicitudes_flow import flow_bp
    from .blueprints.productos_admin import productos_admin_bp





    # Registro
    app.register_blueprint(core_bp)
    app.register_blueprint(directorio_bp, url_prefix="/directorio")
    app.register_blueprint(frames_bp)
    app.register_blueprint(exportar_bp)
    app.register_blueprint(catalogos_bp)
    app.register_blueprint(auth_bp)          # /admin/login, /admin/logout
    app.register_blueprint(admin_portal)     # /admin/panel
    app.register_blueprint(templates_bp)     # /admin/templates
    app.register_blueprint(adh_bp)           # /admin/adhesiones
    app.register_blueprint(minutas_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(sol_portal)
    app.register_blueprint(params_bp)        # /admin/parametros
    app.register_blueprint(users_admin)
    app.register_blueprint(flow_bp)
    app.register_blueprint(productos_admin_bp)

    @app.route("/sol")
    def home():
        return redirect(url_for("sol_portal.lista"))


    return app
