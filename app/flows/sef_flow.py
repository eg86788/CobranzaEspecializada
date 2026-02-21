import re
from decimal import Decimal, InvalidOperation
from flask import request, flash
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


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _norm(value):
    return (value or "").strip()


def _telefono_10(value):
    return re.sub(r"\D", "", value or "")


def _email_valido(value):
    return bool(EMAIL_RE.fullmatch(_norm(value)))


def _list_from_form(form, name):
    return [_norm(v) for v in form.getlist(name) if _norm(v)]


def _normalize_money(value):
    raw = _norm(value).replace("$", "").replace(",", "")
    if not raw:
        return None
    return raw


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
            tipo_tramite = (solicitud.tipo_tramite or "").upper()

            valid_tipo_contrato = {"CPAE TRADICIONAL", "SEF ELECTRÓNICO"}
            valid_tipo_servicio = {
                "DEPÓSITO TRADICIONAL",
                "DEPÓSITO ELECTRÓNICO",
                "DOTACIÓN ELECTRÓNICA"
            }
            valid_servicio_adicional = {
                "TRASLADO DE VALORES",
                "RENTA DE COFRE ELECTRÓNICO"
            }
            valid_cortes = {"08:00 H", "14:00 H", "18:00 H", "T+1"}
            valid_tipo_cobro = {"LOCAL", "CENTRAL"}
            valid_segmento = {"PYME", "INSTITUCIONES Y GOBIERNO", "CORPORATIVO"}
            valid_tipo_persona = {
                "PERSONA FÍSICA CON ACTIVIDAD EMPRESARIAL",
                "PERSONA MORAL"
            }

            tipo_contrato_vals = _list_from_form(form, "tipo_contrato")
            tipo_servicio_vals = _list_from_form(form, "tipo_servicio")
            servicio_adicional_vals = _list_from_form(form, "servicio_adicional")
            cortes_envio_vals = _list_from_form(form, "cortes_envio")

            tipo_cobro = _norm(form.get("tipo_cobro")).upper()
            segmento = _norm(form.get("segmento")).upper()
            tipo_persona = _norm(form.get("tipo_persona")).upper()
            apoderado_legal = _norm(form.get("apoderado_legal"))
            correo_apoderado_legal = _norm(form.get("correo_apoderado_legal"))
            telefono_cliente = _telefono_10(form.get("telefono_cliente"))
            domicilio_cliente = _norm(form.get("domicilio_cliente"))

            errores = []

            if tipo_tramite == "BAJA":
                # En BAJA estos campos se consideran deshabilitados y no aplican.
                servicio_adicional_vals = []
                cortes_envio_vals = []
                tipo_cobro = ""
                segmento = ""
                tipo_persona = ""
                telefono_cliente = ""
                domicilio_cliente = ""

            # Tipo Contrato: obligatorio, 1 a 2
            if len(tipo_contrato_vals) < 1 or len(tipo_contrato_vals) > 2:
                errores.append("Tipo Contrato: selecciona al menos 1 y máximo 2 opciones.")
            if any(v not in valid_tipo_contrato for v in tipo_contrato_vals):
                errores.append("Tipo Contrato contiene valores inválidos.")

            # Tipo Servicio: 1 a 3 cuando aplique
            if len(tipo_servicio_vals) > 3:
                errores.append("Tipo Servicio: selecciona máximo 3 opciones.")
            if any(v not in valid_tipo_servicio for v in tipo_servicio_vals):
                errores.append("Tipo Servicio contiene valores inválidos.")

            # Servicio adicional: 1 a 2 cuando aplique (en BAJA se deshabilita)
            if tipo_tramite != "BAJA" and len(servicio_adicional_vals) < 1:
                errores.append("Servicio Adicional: selecciona al menos 1 opción.")
            if len(servicio_adicional_vals) > 2:
                errores.append("Servicio Adicional: máximo 2 opciones.")
            if any(v not in valid_servicio_adicional for v in servicio_adicional_vals):
                errores.append("Servicio Adicional contiene valores inválidos.")

            # Cortes: máximo 4 (obligatorio se valida por tipo de trámite)
            if len(cortes_envio_vals) > 4:
                errores.append("Cortes de envío: selecciona máximo 4 opciones.")
            if any(v not in valid_cortes for v in cortes_envio_vals):
                errores.append("Cortes de envío contiene valores inválidos.")

            # Alta: reglas condicionales
            if tipo_tramite == "ALTA":
                # Tipo Servicio obligatorio cuando hay Tipo Contrato seleccionado
                if tipo_contrato_vals and len(tipo_servicio_vals) < 1:
                    errores.append("Tipo Servicio es obligatorio para ALTA.")

                if len(cortes_envio_vals) < 1:
                    errores.append("Cortes de envío es obligatorio para ALTA.")

                if tipo_cobro not in valid_tipo_cobro:
                    errores.append("Tipo de Cobro es obligatorio y debe ser Local o Central.")
                if segmento not in valid_segmento:
                    errores.append("Segmento es obligatorio.")
                if tipo_persona not in valid_tipo_persona:
                    errores.append("Tipo de Persona es obligatorio.")
                if not apoderado_legal:
                    errores.append("Apoderado Legal es obligatorio.")
                if not correo_apoderado_legal:
                    errores.append("Correo Apoderado Legal es obligatorio.")
                elif not _email_valido(correo_apoderado_legal):
                    errores.append("Correo Apoderado Legal con formato inválido.")
                if len(telefono_cliente) != 10:
                    errores.append("Teléfono debe tener 10 dígitos.")
                if not domicilio_cliente:
                    errores.append("Domicilio del cliente es obligatorio.")

                raw_importe = _normalize_money(form.get("importe_maximo_dif"))
                if raw_importe is None:
                    importe_maximo_dif = None
                    errores.append("Importe Máximo Diferencia es obligatorio.")
                else:
                    try:
                        importe_maximo_dif = Decimal(raw_importe)
                    except InvalidOperation:
                        importe_maximo_dif = None
                        errores.append("Importe Máximo Diferencia debe tener formato válido (ej. 200.00).")
                    else:
                        if importe_maximo_dif < 0:
                            errores.append("Importe Máximo Diferencia no puede ser negativo.")
            elif tipo_tramite == "MODIFICACION":
                if len(tipo_servicio_vals) < 1:
                    errores.append("Tipo Servicio es obligatorio para MODIFICACIÓN.")
                if segmento not in valid_segmento:
                    errores.append("Segmento es obligatorio.")
                if not apoderado_legal:
                    errores.append("Apoderado Legal es obligatorio.")
                if not correo_apoderado_legal:
                    errores.append("Correo Apoderado Legal es obligatorio.")
                elif not _email_valido(correo_apoderado_legal):
                    errores.append("Correo Apoderado Legal con formato inválido.")

                if tipo_cobro and tipo_cobro not in valid_tipo_cobro:
                    errores.append("Tipo de Cobro inválido.")
                if tipo_persona and tipo_persona not in valid_tipo_persona:
                    errores.append("Tipo de Persona inválido.")
                if telefono_cliente and len(telefono_cliente) != 10:
                    errores.append("Teléfono debe tener 10 dígitos.")

                raw_importe = _normalize_money(form.get("importe_maximo_dif"))
                if raw_importe is None:
                    importe_maximo_dif = None
                else:
                    try:
                        importe_maximo_dif = Decimal(raw_importe)
                    except InvalidOperation:
                        importe_maximo_dif = None
                        errores.append("Importe Máximo Diferencia debe tener formato válido (ej. 200.00).")
                    else:
                        if importe_maximo_dif < 0:
                            errores.append("Importe Máximo Diferencia no puede ser negativo.")
            elif tipo_tramite == "BAJA":
                if len(tipo_servicio_vals) < 1:
                    errores.append("Tipo Servicio es obligatorio para BAJA.")
                if not apoderado_legal:
                    errores.append("Apoderado Legal es obligatorio.")
                if not correo_apoderado_legal:
                    errores.append("Correo Apoderado Legal es obligatorio.")
                elif not _email_valido(correo_apoderado_legal):
                    errores.append("Correo Apoderado Legal con formato inválido.")
                importe_maximo_dif = None
            else:
                importe_maximo_dif = None

            if errores:
                for err in errores:
                    flash(err, "danger")
                return {"sef": sef}

            # Guardado normalizado (multiselect como texto separado por '|')
            sef.tipo_contrato = " | ".join(tipo_contrato_vals)
            sef.tipo_servicio = " | ".join(tipo_servicio_vals)
            sef.servicio_adicional = " | ".join(servicio_adicional_vals)
            sef.cortes_envio = " | ".join(cortes_envio_vals)
            sef.tipo_cobro = tipo_cobro
            sef.importe_maximo_dif = importe_maximo_dif
            sef.segmento = segmento
            sef.tipo_persona = tipo_persona
            sef.apoderado_legal = apoderado_legal
            sef.correo_apoderado_legal = correo_apoderado_legal
            sef.telefono_cliente = telefono_cliente
            sef.domicilio_cliente = domicilio_cliente

            # Sustitución - modificar
            # Solo habilitadas para MODIFICACION
            can_use_sust = tipo_tramite == "MODIFICACION"
            sef.sust_mod_unidades = can_use_sust and bool(form.get("smod_unidades"))
            sef.sust_mod_cuentas = can_use_sust and bool(form.get("smod_cuentas"))
            sef.sust_mod_usuarios = can_use_sust and bool(form.get("smod_usuarios"))
            sef.sust_mod_contactos = can_use_sust and bool(form.get("smod_contactos"))
            sef.sust_mod_tipocobro = can_use_sust and bool(form.get("smod_tipocobro"))
            sef.sust_mod_impdif = can_use_sust and bool(form.get("smod_impdif"))

            # Sustitución - crear
            sef.sust_crea_unidades = can_use_sust and bool(form.get("screa_unidades"))
            sef.sust_crea_cuentas = can_use_sust and bool(form.get("screa_cuentas"))
            sef.sust_crea_usuarios = can_use_sust and bool(form.get("screa_usuarios"))
            sef.sust_crea_contactos = can_use_sust and bool(form.get("screa_contactos"))

            db.session.commit()
            return 3

        return {"sef": sef}

    # =====================================================
    # STEP 3 (Unidades)
    # =====================================================
    if step == 3:

        if form and form.get("continuar_step_3"):
            if not sef.sef_unidades:
                flash("Verifica que todos los campos obligatorios estén llenados antes de continuar.", "danger")
                return None
            return 4

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

            unidad.accion_unidad = _norm(form.get("accion_unidad"))
            unidad.nombre_unidad = _norm(form.get("nombre_unidad"))

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

            if not any([
                unidad.servicio_verificacion_tradicional,
                unidad.servicio_verificacion_electronica,
                unidad.servicio_cliente_certificado_central,
                unidad.servicio_dotacion_centralizada,
                unidad.servicio_integradora,
                unidad.servicio_dotacion,
                unidad.servicio_traslado,
                unidad.servicio_cofre
            ]):
                flash("Verifica que todos los campos obligatorios estén llenados antes de continuar.", "danger")
                return None

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

        if form and form.get("continuar_step_5"):
            if not sef.sef_contactos:
                flash("Verifica que todos los campos obligatorios estén llenados antes de continuar.", "danger")
                return None
            return 6

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
            contacto.nombre = _norm(form.get("nombre"))
            contacto.paterno = _norm(form.get("paterno"))
            contacto.materno = _norm(form.get("materno"))
            contacto.correo = _norm(form.get("correo"))
            telefono_limpio = _telefono_10(form.get("telefono"))
            contacto.telefono = telefono_limpio
            contacto.extension = _norm(form.get("extension"))

            errores = []
            if not contacto.unidad_id:
                errores.append("Unidad es obligatoria.")
            if not contacto.perfil_id:
                errores.append("Perfil es obligatorio.")
            if not contacto.entidad_id:
                errores.append("Entidad es obligatoria.")
            if not contacto.nombre:
                errores.append("Nombre es obligatorio.")
            if not contacto.paterno:
                errores.append("Apellido paterno es obligatorio.")
            if not contacto.materno:
                errores.append("Apellido materno es obligatorio.")
            if not contacto.correo:
                errores.append("Correo es obligatorio.")
            elif not _email_valido(contacto.correo):
                errores.append("Correo con formato inválido.")
            if not telefono_limpio:
                errores.append("Teléfono es obligatorio.")
            elif len(telefono_limpio) != 10:
                errores.append("Teléfono debe tener 10 dígitos.")
            if not contacto.extension:
                errores.append("Extensión es obligatoria.")

            if errores:
                for err in errores:
                    flash(err, "danger")
                return None

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

        if form and form.get("continuar_step_6"):
            if not sef.sef_usuarios:
                flash("Verifica que todos los campos obligatorios estén llenados antes de continuar.", "danger")
                return None
            return 7

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

            usuario.username = _norm(form.get("username"))
            usuario.nombre = _norm(form.get("nombre"))
            usuario.correo = _norm(form.get("correo"))
            usuario.activo = bool(form.get("activo"))

            errores = []
            if not usuario.unidad_id:
                errores.append("Unidad es obligatoria.")
            if not usuario.perfil_producto_id:
                errores.append("Perfil es obligatorio.")
            if not usuario.username:
                errores.append("Usuario es obligatorio.")
            if not usuario.nombre:
                errores.append("Nombre es obligatorio.")
            if not usuario.correo:
                errores.append("Correo es obligatorio.")
            elif not _email_valido(usuario.correo):
                errores.append("Correo con formato inválido.")

            if errores:
                for err in errores:
                    flash(err, "danger")
                return None

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
