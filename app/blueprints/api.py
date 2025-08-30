# app/blueprints/api.py
# Endpoints tipo API: municipios por estado y lo que vayas sumando.

from flask import Blueprint
from ..db_legacy import fetchall

api_bp = Blueprint("api", __name__)

@api_bp.route("/municipios/<estado_id>")
def municipios(estado_id):
    rows = fetchall(
        "SELECT id, nombre FROM catalogo_municipios WHERE estado_id=%s ORDER BY nombre",
        (estado_id,),
    )
    return {"municipios": rows}
