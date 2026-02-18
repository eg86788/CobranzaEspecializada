from flask import request
from app.models import (
    CatalogoEntidad,
    CatalogoProcesadora,
    SolicitudSEF,
    SolicitudSEFUnidad,
    SolicitudSEFCuenta
)

from app.extensions import db


def handle_step(solicitud, step, form):

    # Obtener o crear registro SEF (1 a 1)
    sef = solicitud.sef

    if not sef:
        sef = SolicitudSEF(solicitud=solicitud)
        db.session.add(sef)
        db.session.flush()

    # =====================================================
    # STEP 2 (Datos generales SEF)
    # =====================================================
    if step == 2 and form:

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

    # =====================================================
    # STEP 3 (Unidades SEF)
    # =====================================================
    if step == 3:

        # ==========================================
        # ELIMINAR UNIDAD
        # ==========================================
        if form and form.get("eliminar_unidad_id"):

            unidad = SolicitudSEFUnidad.query.get(
                form.get("eliminar_unidad_id")
            )

            if unidad and unidad.sef_id == sef.id:
                db.session.delete(unidad)
                db.session.commit()

            return None

        # ==========================================
        # CREAR / EDITAR UNIDAD
        # ==========================================
        if form and form.get("guardar_unidad"):

            unidad_id = form.get("unidad_id")

            if unidad_id:
                unidad = SolicitudSEFUnidad.query.get(unidad_id)
            else:
                unidad = SolicitudSEFUnidad(sef=sef)
                db.session.add(unidad)

            # ==========================
            # CAMPOS BASE
            # ==========================
            unidad.accion_unidad = form.get("accion_unidad")
            unidad.nombre_unidad = form.get("nombre_unidad")

            # ==========================
            # IDS DE CATÁLOGOS
            # ==========================
            unidad.cpae_id = form.get("cpae_id") or None
            unidad.etv_id = form.get("etv_id") or None
            unidad.procesadora_id = form.get("procesadora_id") or None
            unidad.entidad_id = form.get("entidad_id") or None
            unidad.municipio_id = form.get("municipio_id") or None

            # ==========================
            # VALIDACIÓN PROCESADORA
            # ==========================
            if unidad.procesadora_id:

                proc = CatalogoProcesadora.query.get(
                    unidad.procesadora_id
                )

                if proc:

                    if unidad.etv_id and proc.etv_id != int(unidad.etv_id):
                        raise ValueError(
                            "Procesadora no corresponde a la ETV seleccionada"
                        )

                    if unidad.cpae_id and proc.cpae_id and proc.cpae_id != int(unidad.cpae_id):
                        raise ValueError(
                            "Procesadora no corresponde al CPAE seleccionado"
                        )

            # ==========================
            # SERVICIOS
            # ==========================
            unidad.servicio_verificacion_tradicional = bool(
                form.get("servicio_verificacion_tradicional")
            )
            unidad.servicio_verificacion_electronica = bool(
                form.get("servicio_verificacion_electronica")
            )
            unidad.servicio_cliente_certificado_central = bool(
                form.get("servicio_cliente_certificado_central")
            )
            unidad.servicio_dotacion_centralizada = bool(
                form.get("servicio_dotacion_centralizada")
            )
            unidad.servicio_integradora = bool(
                form.get("servicio_integradora")
            )
            unidad.servicio_dotacion = bool(
                form.get("servicio_dotacion")
            )
            unidad.servicio_traslado = bool(
                form.get("servicio_traslado")
            )
            unidad.servicio_cofre = bool(
                form.get("servicio_cofre")
            )

            # ==========================
            # DOMICILIO
            # ==========================
            unidad.calle_numero = form.get("calle_numero")
            unidad.codigo_postal = form.get("codigo_postal")

            db.session.commit()

            return None

        # ==========================================
        # GET
        # ==========================================
        unidades = sef.sef_unidades

        entidades = CatalogoEntidad.query.order_by(
            CatalogoEntidad.nombre
        ).all()

        unidad_editar = None
        if request.args.get("editar"):
            unidad_editar = SolicitudSEFUnidad.query.get(
                request.args.get("editar")
            )

        return {
            "sef": sef,
            "unidades": unidades,
            "entidades": entidades,
            "unidad_editar": unidad_editar
        }
     # ===============================
    # STEP 4 (Cuentas SEF)
    # ===============================
    if step == 4:

        # ===================================
        # ELIMINAR CUENTA
        # ===================================
        if form and form.get("eliminar_cuenta_id"):
            cuenta = SolicitudSEFCuenta.query.get(form.get("eliminar_cuenta_id"))
            if cuenta and cuenta.sef_id == sef.id:
                db.session.delete(cuenta)
                db.session.commit()
            return None

        # ===================================
        # CREAR / EDITAR CUENTA
        # ===================================
        if form and form.get("guardar_cuenta"):

            cuenta_id = form.get("cuenta_id")

            if cuenta_id:
                cuenta = SolicitudSEFCuenta.query.get(cuenta_id)
            else:
                cuenta = SolicitudSEFCuenta(sef=sef)
                db.session.add(cuenta)

            cuenta.unidad_id = form.get("unidad_id") or None
            cuenta.sucursal = form.get("sucursal")
            cuenta.numero_cuenta = form.get("numero_cuenta")
            cuenta.moneda = form.get("moneda")
            cuenta.tipo_cuenta = form.get("tipo_cuenta")

            db.session.commit()
            return None

        # ===================================
        # GET
        # ===================================
        cuentas = sef.sef_cuentas
        unidades = sef.sef_unidades

        cuenta_editar = None
        if request.args.get("editar"):
            cuenta_editar = SolicitudSEFCuenta.query.get(request.args.get("editar"))

        return {
            "sef": sef,
            "cuentas": cuentas,
            "unidades": unidades,
            "cuenta_editar": cuenta_editar
        }
