# app/models.py
from datetime import datetime
from app.extensions import db

class AdminUser(db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False, index=True)
    fullname = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    role = db.Column(db.String(20), nullable=False, default="user", index=True)

class Permiso(db.Model):
    __tablename__ = "permisos"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    descripcion = db.Column(db.Text)

class RolePermiso(db.Model):
    __tablename__ = "role_permisos"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    permiso_code = db.Column(db.String(50), db.ForeignKey("permisos.code"), nullable=False, index=True)
    permiso = db.relationship("Permiso", lazy="joined")

    __table_args__ = (db.UniqueConstraint("role", "permiso_code", name="uq_role_permiso"),)

class RoleProductAccess(db.Model):
    __tablename__ = "role_product_access"
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    producto_code = db.Column(db.String(50), nullable=False, index=True)
    habilitado = db.Column(db.Boolean, nullable=False, default=True)
    # Si tienes FK real a catalogo_productos.code en tu DB, puedes agregar:
    # db.ForeignKey("catalogo_productos.code")

from sqlalchemy.dialects.postgresql import JSONB

class Producto(db.Model):
    __tablename__ = "catalogo_productos"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class Solicitud(db.Model):
    __tablename__ = "solicitudes"

    id = db.Column(db.Integer, primary_key=True)

    producto = db.Column(db.String(50), nullable=False, index=True)
    tipo_tramite = db.Column(db.String(50))
    estado_actual = db.Column(db.String(50), nullable=False)
    estatus = db.Column(db.String(20), nullable=False, default="BORRADOR", index=True)

    usuario_creador = db.Column(db.String(50), nullable=False)

    data_json = db.Column(JSONB, nullable=False, default=dict)

    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fecha_actualizacion = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    numero_cliente = db.Column(db.String(50))
    numero_contrato = db.Column(db.String(20))
    razon_social = db.Column(db.String(255))
    observaciones = db.Column(db.Text)
    rfc = db.Column(db.String(20))

class SolicitudSEF(db.Model):
    __tablename__ = "solicitudes_sef"

    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitudes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # =============================
    # Datos de la solicitud (SEF)
    # =============================

    tipo_contrato = db.Column(db.String(100)) #SEF TRADICIONAL O ELECTRONICO
    tipo_servicio = db.Column(db.String(150)) #DEPOSITO, DOTACION O AMBOS
    servicio_adicional = db.Column(db.String(150)) #TRASLADO DE VALORES, COFRE ELECRONICO, AMBOS
    cortes_envio = db.Column(db.String(250)) # NUMERO DE CORTES Y HORARIOS
    tipo_cobro = db.Column(db.String(50)) #LOCAL O CENTRAL

    importe_maximo_dif = db.Column(db.Numeric(15, 2)) 

    # =============================
    # Segmentación cliente
    # =============================
    segmento = db.Column(db.String(50)) #BEI, PYME 
    tipo_persona = db.Column(db.String(150)) #PM O PFAE

    apoderado_legal = db.Column(db.String(150))
    correo_apoderado_legal = db.Column(db.String(150))
    telefono_cliente = db.Column(db.String(20))
    domicilio_cliente = db.Column(db.String(250))

    # =============================
    # Sustitución – Modificar
    # =============================
    sust_mod_unidades = db.Column(db.Boolean, default=False)
    sust_mod_cuentas = db.Column(db.Boolean, default=False)
    sust_mod_usuarios = db.Column(db.Boolean, default=False)
    sust_mod_contactos = db.Column(db.Boolean, default=False)
    sust_mod_tipocobro = db.Column(db.Boolean, default=False)
    sust_mod_impdif = db.Column(db.Boolean, default=False)

    # =============================
    # Sustitución – Crear
    # =============================
    sust_crea_unidades = db.Column(db.Boolean, default=False)
    sust_crea_cuentas = db.Column(db.Boolean, default=False)
    sust_crea_usuarios = db.Column(db.Boolean, default=False)
    sust_crea_contactos = db.Column(db.Boolean, default=False)

    # Relación con Solicitud
    solicitud = db.relationship(
        "Solicitud",
        backref=db.backref("sef", uselist=False, cascade="all, delete")
    )

    sef_unidades = db.relationship(
    "SolicitudSEFUnidad",
    back_populates="sef",
    cascade="all, delete-orphan"
    )

    # =============================
    # SEF - Unidad de Negocio
    # =============================

class SolicitudSEFUnidad(db.Model):
        __tablename__ = "solicitudes_sef_unidades"

        id = db.Column(db.Integer, primary_key=True)

        solicitud_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitudes_sef.id"),
        nullable=False,
        index=True
    )


        accion_unidad = db.Column(db.String(20)) #ALTA, MODIFICACION O BAJA
        nombre_unidad = db.Column(db.String(150))
        cpae_unidad = db.Column(db.String(50))
        etv_unidad = db.Column(db.String(50))
        procesadora_unidad = db.Column(db.String(50)) #Caja que Procesa
        servicio_verificacion_tradicional = db.Column(db.Boolean, default=False, nullable = False) #CheckBox Deposito Tradicional (CPAE)
        servicio_verificacion_electronica = db.Column(db.Boolean, default=False, nullable = False) # Checkbox Depósito Electronico (SEF)
        servicio_cliente_certificado_central = db.Column(db.Boolean, default=False, nullable = False)  # Checkbox Cliente Certificado (SEF)
        servicio_dotacion_centralizada = db.Column(db.Boolean, default=False, nullable = False)  # Checkbox Es Unidad de Dotacion Centralizada (SEF)
        servicio_integradora=  db.Column(db.Boolean, default=False, nullable = False)   # Checkbox Es Unidad Integradora (SEF)
        servicio_dotacion = db.Column(db.Boolean, default=False, nullable = False) # Checkbox Es Unidad de Dotacion Electrónica (SEF)
        servicio_traslado = db.Column(db.Boolean, default=False, nullable = False) # Checkbox Traslado de Valores (SEF)
        servicio_cofre = db.Column(db.Boolean, default=False, nullable = False) # Checkbox Tiene renta de cofre (SEF)
        cofre_modelo = db.Column(db.String(50)) # ID Catálogo de Cofres
        relacion_dot_centralizada = db.Column(db.String(50)) # A qué unidad de Dotacion Centralizada se relaciona
        relacion_cc_centralizada = db.Column(db.String(50)) # A qué unidad de Cliente Certificado Padre se relaciona
        calle_numero = db.Column(db.String(255)) 
        municipio = db.Column(db.Integer) #Id Catalogo Municipio
        entidad_federativa = db.Column(db.Integer) # Id Catálogo Entidades
        codigo_postal = db.Column(db.String(10))

        solicitud = db.relationship("SolicitudSEF", back_populates="sef_unidades")
