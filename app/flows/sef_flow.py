from flask import request
from app.models import (
    CatalogoEntidad,
    CatalogoProcesadora,
    SolicitudSEF,
    SolicitudSEFUnidad,
    SolicitudSEFCuenta,
    SolicitudSEFUsuario,
    CatalogoPerfilProducto,
    Producto,
    Role
)

from app.extensions import db


def to_int(value):
    if not value or value == "None":
        return None
    return int(value)


def handle_step(solicitud, step, form):

    # =====================================================
    # Obtener o crear registro SEF (1 a 1)
    # =====================================================
    sef = solicitud.sef

    if not sef:
        sef = SolicitudSEF(solicitud=solicitud)
        db.session.add(sef)
        db.session.flush()

    # =====================================================
    # STEP 2
    # =====================================================
    if step == 2:

        if form:
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

        return {"sef": sef}

    # =====================================================
    # STEP 3 (Unidades)
    # =====================================================
    if step == 3:

        if form and form.get("eliminar_unidad_id"):

            unidad = SolicitudSEFUnidad.query.get(
                to_int(form.get("eliminar_unidad_id"))
            )

            if unidad and unidad.sef_id == sef.id:
                db.session.delete(unidad)
                db.session.commit()

            return None

        if form and form.get("guardar_unidad"):

            unidad_id = form.get("unidad_id")

            if unidad_id:
                unidad = SolicitudSEFUnidad.query.get(to_int(unidad_id))
            else:
                unidad = SolicitudSEFUnidad(sef=sef)
                db.session.add(unidad)

            unidad.accion_unidad = form.get("accion_unidad")
            unidad.nombre_unidad = form.get("nombre_unidad")

            unidad.cpae_id = to_int(form.get("cpae_id"))
            unidad.etv_id = to_int(form.get("etv_id"))
            unidad.procesadora_id = to_int(form.get("procesadora_id"))
            unidad.entidad_id = to_int(form.get("entidad_id"))
            unidad.municipio_id = to_int(form.get("municipio_id"))

            if unidad.procesadora_id:
                proc = CatalogoProcesadora.query.get(unidad.procesadora_id)

                if proc:
                    if unidad.etv_id and proc.etv_id != unidad.etv_id:
                        raise ValueError("Procesadora no corresponde a la ETV seleccionada")

                    if unidad.cpae_id and proc.cpae_id and proc.cpae_id != unidad.cpae_id:
                        raise ValueError("Procesadora no corresponde al CPAE seleccionado")

            unidad.servicio_verificacion_tradicional = bool(form.get("servicio_verificacion_tradicional"))
            unidad.servicio_verificacion_electronica = bool(form.get("servicio_verificacion_electronica"))
            unidad.servicio_cliente_certificado_central = bool(form.get("servicio_cliente_certificado_central"))
            unidad.servicio_dotacion_centralizada = bool(form.get("servicio_dotacion_centralizada"))
            unidad.servicio_integradora = bool(form.get("servicio_integradora"))
            unidad.servicio_dotacion = bool(form.get("servicio_dotacion"))
            unidad.servicio_traslado = bool(form.get("servicio_traslado"))
            unidad.servicio_cofre = bool(form.get("servicio_cofre"))

            unidad.calle_numero = form.get("calle_numero")
            unidad.codigo_postal = form.get("codigo_postal")

            db.session.commit()
            return None

        unidades = sef.sef_unidades
        entidades = CatalogoEntidad.query.order_by(CatalogoEntidad.nombre).all()

        unidad_editar = None
        if request.args.get("editar"):
            unidad_editar = SolicitudSEFUnidad.query.get(
                to_int(request.args.get("editar"))
            )

        return {
            "sef": sef,
            "unidades": unidades,
            "entidades": entidades,
            "unidad_editar": unidad_editar
        }

    # =====================================================
    # STEP 4 (Cuentas)
    # =====================================================
    if step == 4:

        if form and form.get("eliminar_cuenta_id"):

            cuenta = SolicitudSEFCuenta.query.get(
                to_int(form.get("eliminar_cuenta_id"))
            )

            if cuenta and cuenta.sef_id == sef.id:
                db.session.delete(cuenta)
                db.session.commit()

            return None

        if form and form.get("guardar_cuenta"):

            cuenta_id = form.get("cuenta_id")

            if cuenta_id:
                cuenta = SolicitudSEFCuenta.query.get(to_int(cuenta_id))
            else:
                cuenta = SolicitudSEFCuenta(sef=sef)
                db.session.add(cuenta)

            cuenta.unidad_id = to_int(form.get("unidad_id"))
            cuenta.sucursal = form.get("sucursal")
            cuenta.numero_cuenta = form.get("numero_cuenta")
            cuenta.moneda = form.get("moneda")
            cuenta.tipo_cuenta = form.get("tipo_cuenta")

            db.session.commit()
            return None

        cuentas = sef.sef_cuentas
        unidades = sef.sef_unidades

        cuenta_editar = None
        if request.args.get("editar"):
            cuenta_editar = SolicitudSEFCuenta.query.get(
                to_int(request.args.get("editar"))
            )

        return {
            "sef": sef,
            "cuentas": cuentas,
            "unidades": unidades,
            "cuenta_editar": cuenta_editar
        }

    # =====================================================
    # STEP 5 (Contactos)
    # =====================================================
    if step == 5:

        from app.models import SolicitudSEFContacto, Role

        if form and form.get("eliminar_contacto_id"):

            contacto = SolicitudSEFContacto.query.get(
                to_int(form.get("eliminar_contacto_id"))
            )

            if contacto and contacto.sef_id == sef.id:
                db.session.delete(contacto)
                db.session.commit()

            return None

        if form and form.get("guardar_contacto"):

            contacto_id = form.get("contacto_id")

            if contacto_id:
                contacto = SolicitudSEFContacto.query.get(to_int(contacto_id))
            else:
                contacto = SolicitudSEFContacto(sef=sef)
                db.session.add(contacto)

            # Llaves foráneas (listas)
            contacto.unidad_id = to_int(form.get("unidad_id"))
            contacto.perfil_id = to_int(form.get("perfil_id"))
            contacto.entidad_id = to_int(form.get("entidad_id"))

            # Datos generales
            contacto.nombre = form.get("nombre")
            contacto.paterno = form.get("paterno")
            contacto.materno = form.get("materno")
            contacto.correo = form.get("correo")
            contacto.telefono = form.get("telefono")
            contacto.extension = form.get("extension")

            db.session.commit()
            return None

        contactos = sef.sef_contactos
        unidades = sef.sef_unidades
        perfiles = Role.query.order_by(Role.descripcion).all()
        entidades = CatalogoEntidad.query.order_by(CatalogoEntidad.nombre).all()

        contacto_editar = None
        if request.args.get("editar"):
            contacto_editar = SolicitudSEFContacto.query.get(
                to_int(request.args.get("editar"))
            )

        return {
            "sef": sef,
            "contactos": contactos,
            "unidades": unidades,
            "perfiles": perfiles,
            "entidades": entidades,
            "contacto_editar": contacto_editar
        }

    # =====================================================
    # STEP 6 (Usuarios SEF)
    # =====================================================
    if step == 6:

        # Obtener producto SEF
        producto_sef = Producto.query.filter_by(code="sef").first()

        if form and form.get("eliminar_usuario_id"):

            usuario = SolicitudSEFUsuario.query.get(
                to_int(form.get("eliminar_usuario_id"))
            )

            if usuario and usuario.sef_id == sef.id:
                db.session.delete(usuario)
                db.session.commit()

            return None

        if form and form.get("guardar_usuario"):

            usuario_id = form.get("usuario_id")

            if usuario_id:
                usuario = SolicitudSEFUsuario.query.get(to_int(usuario_id))
            else:
                usuario = SolicitudSEFUsuario(sef=sef)
                db.session.add(usuario)

            usuario.unidad_id = to_int(form.get("unidad_id"))
            usuario.perfil_producto_id = to_int(form.get("perfil_producto_id"))

            usuario.username = form.get("username")
            usuario.nombre = form.get("nombre")
            usuario.correo = form.get("correo")
            usuario.activo = bool(form.get("activo"))

            db.session.commit()
            return None

        usuarios = sef.sef_usuarios
        unidades = sef.sef_unidades

        perfiles_producto = []
        if producto_sef:
            perfiles_producto = CatalogoPerfilProducto.query \
                .filter_by(producto_id=producto_sef.id, activo=True) \
                .order_by(CatalogoPerfilProducto.descripcion) \
                .all()

        usuario_editar = None
        if request.args.get("editar"):
            usuario_editar = SolicitudSEFUsuario.query.get(
                to_int(request.args.get("editar"))
            )

        return {
            "sef": sef,
            "usuarios": usuarios,
            "unidades": unidades,
            "perfiles_producto": perfiles_producto,
            "usuario_editar": usuario_editar
        }

    return {"sef": sef}
