# app/errors.py
import uuid
from flask import render_template, request
from werkzeug.exceptions import HTTPException

def register_error_handlers(app):
    def _render(code: int, e):
        error_id = uuid.uuid4().hex[:8]
        # Log detallado en servidor
        try:
            app.logger.exception(f"[{error_id}] {request.method} {request.path}: {e}")
        except Exception:
            pass

        # Mensaje amigable; evita exponer trazas
        message = None
        if code == 404:
            message = "La página que buscas no existe."
        elif code == 403:
            message = "No tienes permisos para acceder a este recurso."
        elif code == 500:
            message = "Error interno del servidor."

        return render_template(
            "error.html",
            error_code=code,
            error_message=message,
            error_id=error_id
        ), code

    @app.errorhandler(403)
    def handle_403(e):
        return _render(403, e)

    @app.errorhandler(404)
    def handle_404(e):
        return _render(404, e)

    @app.errorhandler(500)
    def handle_500(e):
        return _render(500, e)

    # Cualquier excepción no controlada
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return _render(e.code or 500, e)
        return _render(500, e)
