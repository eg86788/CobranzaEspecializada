from flask import request
from app.models import SolicitudSEF, SolicitudSEFUnidad
from app.extensions import db


def handle_step(solicitud, step, form):

    # Obtener o crear registro SEF (1 a 1)
    sef = solicitud.sef

    if not sef:
        sef = SolicitudSEF(solicitud=solicitud)
        db.session.add(sef)
        db.session.flush()  # no commit aún

    # ===============================
    # STEP 2 (Datos generales SEF)
    # ===============================
    if step == 2:

        sef.tipo_contrato = form.get("tipo_contrato")
        sef.tipo_servicio = form.get("tipo_servicio")
        sef.servicio_adicional = form.get("servicio_adicional")
        sef.tipo_cobro = form.get("tipo_cobro")
        sef.cortes_envio = form.get("cortes_envio")

        sef.importe_maximo_dif = form.get("importe_maximo_dif") or None

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

        return 3

    # ===============================
    # STEP 3 (Unidades SEF)
    # ===============================
    if step == 3:

        if request.method == "POST":

            nueva = SolicitudSEFUnidad(
                sef=sef,
                accion_unidad=form.get("accion_unidad"),
                nombre_unidad=form.get("nombre_unidad"),
                cpae_unidad=form.get("cpae_unidad"),
                etv_unidad=form.get("etv_unidad"),
                procesadora_unidad=form.get("procesadora_unidad"),

                servicio_verificacion_tradicional=bool(form.get("servicio_verificacion_tradicional")),
                servicio_verificacion_electronica=bool(form.get("servicio_verificacion_electronica")),
                servicio_cliente_certificado_central=bool(form.get("servicio_cliente_certificado_central")),
                servicio_dotacion_centralizada=bool(form.get("servicio_dotacion_centralizada")),
                servicio_integradora=bool(form.get("servicio_integradora")),
                servicio_dotacion=bool(form.get("servicio_dotacion")),
                servicio_traslado=bool(form.get("servicio_traslado")),
                servicio_cofre=bool(form.get("servicio_cofre")),

                calle_numero=form.get("calle_numero"),
                municipio=form.get("municipio"),
                entidad_federativa=form.get("entidad_federativa"),
                codigo_postal=form.get("codigo_postal"),
            )

            db.session.add(nueva)
            db.session.commit()

            # SIEMPRE cargar unidades después
            unidades = sef.sef_unidades

        return {"sef": sef, "unidades": unidades}, None

