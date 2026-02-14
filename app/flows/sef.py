def handle_post(solicitud, step, form):

    if step == 2:
        solicitud.nombre_ejecutivo = form.get("nombre_ejecutivo")
        solicitud.tipo_contrato = form.get("tipo_contrato")
        solicitud.tipo_servicio = form.get("tipo_servicio")
        solicitud.tipo_cobro = form.get("tipo_cobro")
        solicitud.segmento = form.get("segmento")
        # etc...

def get_template(step):
    return f"solicitudes/flows/sef/step_{step}.html"
