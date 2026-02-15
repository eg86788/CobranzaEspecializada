
from flask import request
from app.forms.SEF.steps import unidades
from app.models import SolicitudSEF, SolicitudSEFUnidad
from app.extensions import db


def handle_step(solicitud, step, form):

    # Crear registro SEF si no existe
    if not solicitud.sef:
        sef = SolicitudSEF(solicitud_id=solicitud.id)
        db.session.add(sef)
        db.session.commit()
    else:
        sef = solicitud.sef


        # ---------- STEP 3 (SEF UNIDADES) ----------
        sef = solicitud.sef  # relación 1 a 1
        
        if step == 3:
            if not sef:
                # si no existe todavía, créalo
                sef = SolicitudSEF(solicitud=solicitud)
                db.session.add(sef)
                db.session.flush()  # para obtener ID
            nueva = SolicitudSEFUnidad(
                sef=sef,
                accion_unidad=request.form.get("accion_unidad"),
                nombre_unidad=request.form.get("nombre_unidad"),
                cpae_unidad=request.form.get("cpae_unidad"),
                etv_unidad=request.form.get("etv_unidad"),
                procesadora_unidad=request.form.get("procesadora_unidad"),

                servicio_verificacion_tradicional=bool(request.form.get("servicio_verificacion_tradicional")),
                servicio_verificacion_electronica=bool(request.form.get("servicio_verificacion_electronica")),
                servicio_cliente_certificado_central=bool(request.form.get("servicio_cliente_certificado_central")),
                servicio_dotacion_centralizada=bool(request.form.get("servicio_dotacion_centralizada")),
                servicio_integradora=bool(request.form.get("servicio_integradora")),
                servicio_dotacion=bool(request.form.get("servicio_dotacion")),
                servicio_traslado=bool(request.form.get("servicio_traslado")),
                servicio_cofre=bool(request.form.get("servicio_cofre")),

                calle_numero=request.form.get("calle_numero"),
                municipio=request.form.get("municipio"),
                entidad_federativa=request.form.get("entidad_federativa"),
                codigo_postal=request.form.get("codigo_postal"),
            )

            db.session.add(nueva)
            db.session.commit()

            return render_template(
                "solicitudes/flows/sef/step_3.html",
                solicitud=solicitud,
                sef=sef,
                unidades=unidades
            )
    # ===============================
    # STEP 2  (Frame 1 anterior)
    # ===============================
    if step == 2:

        sef.nombre_ejecutivo = form.get("nombre_ejecutivo")
        sef.tipo_contrato = form.get("tipo_contrato")
        sef.tipo_servicio = form.get("tipo_servicio")
        sef.servicio_adicional = form.get ("servicio_adicional")
        sef.tipo_cobro = form.get("tipo_cobro")
        sef.cortes_envio = form.get("cortes_envio")

        sef.importe_maximo_dif = (
            form.get("importe_maximo_dif") or None
        )

        sef.segmento = form.get("segmento")
        sef.tipo_persona = form.get("tipo_persona")

        sef.apoderado_legal = form.get("apoderado_legal")
        sef.correo_apoderado_legal = form.get("correo_apoderado_legal")
        sef.telefono_cliente = form.get("telefono_cliente")
        sef.domicilio_cliente = form.get("domicilio_cliente")

        # Sustitución - modificar
        sef.sust_mod_unidades = bool(form.get("smod_unidades"))
        sef.sust_mod_cuentas = bool(form.get("smod_cuentas"))
        sef.sust_mod_usuarios = bool(form.get("smod_usuarios"))
        sef.sust_mod_contactos = bool(form.get("smod_contactos"))
        sef.sust_mod_tipocobro = bool(form.get("smod_tipocobro"))
        sef.sust_mod_impdif = bool(form.get("smod_impdif"))

        # Sustitución - crear
        sef.sust_crea_unidades = bool(form.get("screa_unidades"))
        sef.sust_crea_cuentas = bool(form.get("screa_cuentas"))
        sef.sust_crea_usuarios = bool(form.get("screa_usuarios"))
        sef.sust_crea_contactos = bool(form.get("screa_contactos"))

        db.session.commit()

        return 3  # siguiente step

    return None
