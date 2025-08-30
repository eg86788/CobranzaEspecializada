from functools import wraps
from flask import session, redirect, url_for, flash, request
from ..db_legacy import fetchall

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            flash("Inicia sesión.", "warning")
            return redirect(url_for("auth_admin.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def role_required(*roles):
    def deco(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Inicia sesión.", "warning")
                return redirect(url_for("auth.login", next=request.path))
            if session.get("role") not in roles:
                flash("No tienes permisos.", "danger")
                return redirect(url_for("core.inicio"))
            return view(*args, **kwargs)
        return wrapped
    return deco

def permiso_required(code):
    def deco(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get("user_id"):
                flash("Inicia sesión.", "warning")
                return redirect(url_for("auth_admin.login", next=request.path))
            role = session.get("role")
            if not role:
                flash("No tienes permisos.", "danger")
                return redirect(url_for("core.inicio"))
            # consulta permisos por rol (cacheable si quieres)
            rows = fetchall("SELECT permiso_code FROM role_permisos WHERE role=%s", (role,))
            granted = {r["permiso_code"] for r in rows}
            if code not in granted:
                flash("No tienes permisos.", "danger")
                return redirect(url_for("core.inicio"))
            return view(*args, **kwargs)
        return wrapped
    return deco
