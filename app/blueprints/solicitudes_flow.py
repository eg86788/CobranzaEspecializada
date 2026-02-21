import re
from flask import Blueprint, render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound
from app.models import Solicitud, Role
from app.extensions import db

flow_bp = Blueprint(
    "solicitudes_flow",
    __name__,
    url_prefix="/solicitudes"
)


@flow_bp.route("/<int:solicitud_id>/step/<int:step>", methods=["GET", "POST"])
def step(solicitud_id, step):

    solicitud = Solicitud.query.get_or_404(solicitud_id)
    producto_code = (solicitud.producto or "").strip().lower()

    # ==========================================
    # POST
    # ==========================================
    if request.method == "POST":

        # ---------- STEP 1 ----------
        if step == 1:
            numero_cliente = re.sub(r"\D", "", (request.form.get("numero_cliente") or "").strip())
            numero_contrato = re.sub(r"\D", "", (request.form.get("numero_contrato") or "").strip())
            razon_social = (request.form.get("razon_social") or "").strip()
            observaciones = request.form.get("observaciones")
            rfc = (request.form.get("rfc") or "").strip().upper()
            tipo_tramite = (request.form.get("tipo_tramite") or "").strip().upper()

            errores = []

            if not numero_cliente:
                errores.append("Número Cliente es obligatorio.")
            elif len(numero_cliente) > 10:
                errores.append("Número Cliente debe contener máximo 10 dígitos.")
            else:
                numero_cliente = numero_cliente.zfill(10)

            if not re.fullmatch(r"^[A-ZÑ&]{4}\d{6}[A-Z0-9]{3}$", rfc):
                errores.append("RFC debe contener exactamente 13 caracteres con formato válido.")

            if tipo_tramite not in {"ALTA", "MODIFICACION", "BAJA"}:
                errores.append("Debe seleccionar un tipo de trámite válido.")

            if tipo_tramite == "ALTA":
                numero_contrato = ""
            elif tipo_tramite in {"MODIFICACION", "BAJA"}:
                if not numero_contrato:
                    errores.append("Número Contrato es obligatorio en MODIFICACIÓN y BAJA.")
                elif len(numero_contrato) > 12:
                    errores.append("Número Contrato debe contener máximo 12 dígitos.")
                elif len(numero_contrato) < 10:
                    numero_contrato = numero_contrato.zfill(10)

            if not razon_social:
                errores.append("Razón Social es obligatoria.")
            elif len(razon_social) > 250:
                errores.append("Razón Social debe contener máximo 250 caracteres.")
            elif not re.fullmatch(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ\s.,\-_/&()]+", razon_social):
                errores.append("Razón Social solo acepta caracteres alfanuméricos.")

            if errores:
                for err in errores:
                    flash(err, "danger")
                return redirect(
                    url_for(
                        "solicitudes_flow.step",
                        solicitud_id=solicitud.id,
                        step=1
                    )
                )

            solicitud.numero_cliente = numero_cliente
            solicitud.numero_contrato = numero_contrato
            solicitud.razon_social = razon_social
            solicitud.observaciones = observaciones
            solicitud.rfc = rfc
            solicitud.tipo_tramite = tipo_tramite

            db.session.commit()

            return redirect(
                url_for(
                    "solicitudes_flow.step",
                    solicitud_id=solicitud.id,
                    step=2
                )
            )

        # ---------- PRODUCTOS ----------
        if producto_code == "sef":
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

        total_steps = None
        if producto_code == "sef":
            total_steps = 6  # Total de pasos del flujo SEF

        return render_template(
            template_base,
            solicitud=solicitud,
            step=step,
            total_steps=total_steps
        )

    # Para productos específicos desde step 2
    if producto_code == "sef":
        from app.flows.sef_flow import handle_step

        context = handle_step(solicitud, step, None) or {}

        template = f"solicitudes/flows/sef/step_{step}.html"

        total_steps = 7  # Total de pasos del flujo SEF

        return render_template(
            template,
            solicitud=solicitud,
            step=step,
            total_steps=total_steps,
            **(context or {})
        )

    # ==========================================
    # BASE (productos sin flow específico)
    # ==========================================

    template_producto = f"solicitudes/flows/{producto_code}/step_{step}.html"
    template_base = f"solicitudes/flows/base/step_{step}.html"

    try:
        return render_template(template_producto, solicitud=solicitud, step=step)
    except TemplateNotFound:
        try:
            return render_template(template_base, solicitud=solicitud, step=step)
        except TemplateNotFound:
            flash("No existe plantilla para este paso del flujo.", "danger")
            return redirect(url_for("solicitudes_flow.step", solicitud_id=solicitud.id, step=1))

# ==========================================
# CANCELAR SOLICITUD
# ==========================================
@flow_bp.route("/<int:solicitud_id>/cancelar", methods=["POST"])
def cancelar(solicitud_id):

    solicitud = Solicitud.query.get_or_404(solicitud_id)

    # Si ya está cancelada, no hacer nada
    if solicitud.estatus == "Cancelada":
        return redirect(url_for("sol_portal.lista"))

    # Cambiar estatus
    solicitud.estatus = "Cancelada"

    # Opcional: limpiar registros dependientes si es SEF
    if solicitud.producto == "sef":
        borrar_registros_dependientes(solicitud.id)

    db.session.commit()

    return redirect(url_for("sol_portal.lista"))

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
        SolicitudSEF,
        SolicitudSEFUnidad,
        SolicitudSEFCuenta,
        SolicitudSEFUsuario,
        SolicitudSEFContacto
    )

    # Obtener registro SEF asociado a la solicitud
    sef = SolicitudSEF.query.filter_by(solicitud_id=solicitud_id).first()

    if not sef:
        return

    # Primero borrar dependientes de unidad (cuentas)
    SolicitudSEFCuenta.query.filter_by(sef_id=sef.id).delete()

    # Luego borrar usuarios y contactos
    SolicitudSEFUsuario.query.filter_by(sef_id=sef.id).delete()
    SolicitudSEFContacto.query.filter_by(sef_id=sef.id).delete()

    # Finalmente borrar unidades
    SolicitudSEFUnidad.query.filter_by(sef_id=sef.id).delete()

    db.session.commit()
