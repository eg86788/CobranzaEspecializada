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

migrate = Migrate()

def create_app():
    app = Flask(__name__)

    db.init_app(app)
    migrate.init_app(app, db)

    return app

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
    app.permanent_session_lifetime = timedelta(minutes=15)  # fallback por si no hay DB

    app.config.setdefault(
        "SQLALCHEMY_DATABASE_URI",
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

    # ----- Context processors (user info) -----
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
    app.register_blueprint(params_bp)        # /admin/parametros
    app.register_blueprint(config_campos_admin_bp)


    # ---------------- TIMEOUT desde parámetros de BD ----------------
    def _load_timeout_minutes() -> int:
        """Lee el tiempo de inactividad (minutos) desde system_params."""
        try:
            with conectar() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT value FROM system_params WHERE key=%s LIMIT 1",
                    ("session_timeout_minutes",),
                )
                row = cur.fetchone()
                if row and row.get("value"):
                    return int(row["value"])
        except Exception:
            pass
        return 15  # fallback

    @app.before_request
    def _apply_session_timeout():
        mins = _load_timeout_minutes()
        app.permanent_session_lifetime = timedelta(minutes=mins)
        # asegúrate de que la sesión activa sea permanente para que la cookie respete el lifetime
        if "user_id" in session:
            session.permanent = True

    @app.context_processor
    def inject_timeout():
        # Expone a Jinja el valor para el JS de autologout
        return {"inactivity_minutes": _load_timeout_minutes()}

    # ----- Crear tablas solo si lo activas por config o env var -----
    init_flag = app.config.get("INIT_DB") or os.getenv("INIT_DB") == "1"
    if init_flag:
        with app.app_context():
            try:
                from app import models  # noqa: F401
                db.create_all()
            except Exception:
                pass

    # === RUTA RAÍZ ===
    def _root_index():
        user_id = session.get("user_id")
        role = session.get("role")  # "admin" o "user"
        if user_id:
            if role == "admin":
                return redirect(url_for("admin_portal.dashboard"))
            else:
                return redirect(url_for("core.inicio_productos"))
        # login correcto del blueprint auth_admin
        return redirect(url_for("auth_admin.login"))

    app.add_url_rule("/", "root_index", _root_index)

    register_error_handlers(app)
    return app
