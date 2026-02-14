from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Solicitud
from app.extensions import db

flow_bp = Blueprint(
    "solicitudes_flow",
    __name__,
    url_prefix="/solicitudes"
)


@flow_bp.route("/<int:solicitud_id>/step/<int:step>", methods=["GET", "POST"])
def step(solicitud_id, step):

    solicitud = Solicitud.query.get_or_404(solicitud_id)

    # ===== POST (guardar datos) =====
    if request.method == "POST":

        if step == 1:
            solicitud.numero_cliente = request.form.get("numero_cliente")
            solicitud.numero_contrato = request.form.get("numero_contrato")
            solicitud.razon_social = request.form.get("razon_social")
            solicitud.observaciones = request.form.get("observaciones")
            solicitud.rfc = request.form.get("rfc")

            db.session.commit()

            return redirect(
                url_for(
                    "solicitudes_flow.step",
                    solicitud_id=solicitud.id,
                    step=2
                )
            )

    # ===== Render template =====
    template_producto = f"solicitudes/flows/{solicitud.producto}/step_{step}.html"
    template_base = f"solicitudes/flows/base/step_{step}.html"

    try:
        return render_template(template_producto, solicitud=solicitud, step=step)
    except:
        return render_template(template_base, solicitud=solicitud, step=step)
