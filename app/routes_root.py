from flask import redirect, session, url_for

def init_root_routes(app):
    """
    Registra la ruta raíz "/" con redirección según sesión/rol:
      - Sin sesión -> /admin/login
      - Rol admin  -> /admin/panel
      - Rol user   -> /productos
    """
    @app.route("/")
    def root_redirect():
        role = (session.get("role") or session.get("user_role") or "").lower()
        user_id = session.get("user_id")

        # Sin sesión activa
        if not user_id or not role:
            # usa url_for si existe el endpoint "admin.login", si no ruta literal
            if "admin.login" in app.view_functions:
                return redirect(url_for("admin.login"))
            return redirect("/admin/login")

        # Sesión activa: decide por rol
        if role == "admin":
            if "admin.panel" in app.view_functions:
                return redirect(url_for("admin.panel"))
            return redirect("/admin/panel")

        # Cualquier otro rol (user por defecto)
        if "productos.index" in app.view_functions:
            return redirect(url_for("productos.index"))
        return redirect("/productos")
