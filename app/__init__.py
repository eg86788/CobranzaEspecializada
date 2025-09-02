# app/__init__.py
import logging
import os
from pathlib import Path
from flask import Flask, session
from app.extensions import db
from .config import Config
from .db_legacy import fetchall  # si lo usas en otros módulos, se queda
from .errors import register_error_handlers
from flask import Flask, redirect, url_for, session
from .blueprints.solicitudes_portal import sol_portal




def create_app():
    project_root = Path(__file__).resolve().parent.parent
    templates_dir = project_root / "templates"
    static_dir = project_root / "static"

    app = Flask(
        __name__,
        template_folder=str(templates_dir),
        static_folder=str(static_dir)
    )

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

    # ----- Extensiones -----
    db.init_app(app)

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

    # ----- Blueprints -----
    from .blueprints.core import core_bp
    from .blueprints.directorio import directorio_bp
    from .blueprints.frames import frames_bp
    from .blueprints.exportar import exportar_bp
    from .blueprints.catalogos import catalogos_bp
    from .blueprints.api import api_bp

    # Login (admin/user) y panel admin
    from .blueprints.auth_admin import auth_bp         # name interno = "auth_admin"
    from .blueprints.admin_portal import admin_portal  # name interno = "admin_portal"

    # Módulos admin protegidos
    from .blueprints.templates_admin import templates_bp
    from .blueprints.adhesiones_admin import adh_bp
    from .blueprints.minutas import minutas_bp

    # (Opcional) Admin de usuarios/roles/permisos
    try:
        from app.blueprints.users_admin import users_admin
        app.register_blueprint(users_admin)
    except Exception:
        # Si aún no tienes el módulo, lo ignoramos sin romper la app.
        pass

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


    # ----- Crear tablas solo si lo activas por config o env var -----
    init_flag = app.config.get("INIT_DB") or os.getenv("INIT_DB") == "1"
    if init_flag:
        with app.app_context():
            try:
                # importa tus modelos para que SQLAlchemy conozca las tablas
                from app import models  # noqa: F401
                db.create_all()
            except Exception:
                # No detenemos el arranque si falla (p.ej. usando Postgres con tablas ya creadas)
                pass

    # === RUTA RAÍZ SIN NUEVO BLUEPRINT ===
    def _root_index():
        user_id = session.get("user_id")
        role = session.get("role")  # "admin" o "user"
        if user_id:
            if role == "admin":
                # ⬇️ Cambia el endpoint por el real de tu panel admin
                return redirect(url_for("admin_portal.dashboard"))
            else:
                # ⬇️ Cambia por el endpoint real de tu “inicio productos”
                return redirect(url_for("inicio_productos.index"))
        # ⬇️ Cambia por el endpoint real de tu login (hoy está en /admin/login)
        return redirect(url_for("admin.login"))

    app.add_url_rule("/", "root_index", _root_index)
    
    register_error_handlers(app)
    

    return app
