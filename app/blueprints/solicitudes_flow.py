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

    # ==========================================
    # POST
    # ==========================================
    if request.method == "POST":

        # ---------- STEP 1 ----------
        if step == 1:
            solicitud.numero_cliente = request.form.get("numero_cliente")
            solicitud.numero_contrato = request.form.get("numero_contrato")
            solicitud.razon_social = request.form.get("razon_social")
            solicitud.observaciones = request.form.get("observaciones")
            solicitud.rfc = request.form.get("rfc")
            solicitud.tipo_tramite = request.form.get("tipo_tramite")

            db.session.commit()

            return redirect(
                url_for(
                    "solicitudes_flow.step",
                    solicitud_id=solicitud.id,
                    step=2
                )
            )

        # ---------- PRODUCTOS ----------
        if solicitud.producto == "sef":
            from app.flows.sef_flow import handle_step

            next_step = handle_step(solicitud, step, request.form)

            if next_step:
                return redirect(
                    url_for(
                        "solicitudes_flow.step",
                        solicitud_id=solicitud.id,
                        step=next_step
                    )
                )

    # ==========================================
    # GET (delegar al flow si es producto)
    # ==========================================

    # Step 1 siempre usa base
    if step == 1:
        template_base = f"solicitudes/flows/base/step_{step}.html"
        return render_template(template_base, solicitud=solicitud, step=step)

    # Para productos específicos desde step 2
    if solicitud.producto == "sef":
        from app.flows.sef_flow import handle_step

        context = handle_step(solicitud, step, None) or {}  

        template = f"solicitudes/flows/sef/step_{step}.html"

        return render_template(
            template,
            solicitud=solicitud,
            step=step,
            **(context or {})
        )

    # ==========================================
    # BASE (productos sin flow específico)
    # ==========================================

    template_producto = f"solicitudes/flows/{solicitud.producto}/step_{step}.html"
    template_base = f"solicitudes/flows/base/step_{step}.html"

    try:
        return render_template(template_producto, solicitud=solicitud, step=step)
    except:
        return render_template(template_base, solicitud=solicitud, step=step)

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def config_cambio(solicitud, form):
    return (
        solicitud.tipo_tramite != form.get("tipo_tramite") or
        solicitud.tipo_contrato != form.get("tipo_contrato") or
        solicitud.tipo_servicio != form.get("tipo_servicio")
    )


def borrar_registros_dependientes(solicitud_id):
    from app.models import (
        SolicitudSEFUnidad,
        SolicitudSEFCuenta,
        SolicitudSEFUsuario,
        SolicitudSEFContacto
    )

    SolicitudSEFUnidad.query.filter_by(solicitud_id=solicitud_id).delete()
    SolicitudSEFCuenta.query.filter_by(solicitud_id=solicitud_id).delete()
    SolicitudSEFUsuario.query.filter_by(solicitud_id=solicitud_id).delete()
    SolicitudSEFContacto.query.filter_by(solicitud_id=solicitud_id).delete()
    db.session.commit()
