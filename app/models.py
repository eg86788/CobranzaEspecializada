# app/models.py
from datetime import datetime
from app.extensions import db
from sqlalchemy.dialects.postgresql import JSONB


# =====================================================
# ADMIN / PERMISOS
# =====================================================

class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    descripcion = db.Column(db.String(150))

    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return self.code


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

    __table_args__ = (
        db.UniqueConstraint("role", "permiso_code", name="uq_role_permiso"),
    )


class RoleProductAccess(db.Model):
    __tablename__ = "role_product_access"

    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False, index=True)
    producto_code = db.Column(db.String(50), nullable=False, index=True)
    habilitado = db.Column(db.Boolean, nullable=False, default=True)


# =====================================================
# PRODUCTOS
# =====================================================

class Producto(db.Model):
    __tablename__ = "catalogo_productos"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# =====================================================
# SOLICITUD BASE
# =====================================================

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

    # 1 a 1 con SEF
    sef = db.relationship(
        "SolicitudSEF",
        back_populates="solicitud",
        uselist=False,
        cascade="all, delete-orphan"
    )


# =====================================================
# SOLICITUD SEF (1 a 1 con Solicitud)
# =====================================================

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
    # Datos específicos SEF
    # =============================

    tipo_contrato = db.Column(db.String(100))
    tipo_servicio = db.Column(db.String(150))
    servicio_adicional = db.Column(db.String(150))
    cortes_envio = db.Column(db.String(250))
    tipo_cobro = db.Column(db.String(50))
    importe_maximo_dif = db.Column(db.Numeric(15, 2))

    segmento = db.Column(db.String(50))
    tipo_persona = db.Column(db.String(150))

    apoderado_legal = db.Column(db.String(150))
    correo_apoderado_legal = db.Column(db.String(150))
    telefono_cliente = db.Column(db.String(20))
    domicilio_cliente = db.Column(db.String(250))

    # Sustitución – Modificar
    sust_mod_unidades = db.Column(db.Boolean, default=False)
    sust_mod_cuentas = db.Column(db.Boolean, default=False)
    sust_mod_usuarios = db.Column(db.Boolean, default=False)
    sust_mod_contactos = db.Column(db.Boolean, default=False)
    sust_mod_tipocobro = db.Column(db.Boolean, default=False)
    sust_mod_impdif = db.Column(db.Boolean, default=False)

    # Sustitución – Crear
    sust_crea_unidades = db.Column(db.Boolean, default=False)
    sust_crea_cuentas = db.Column(db.Boolean, default=False)
    sust_crea_usuarios = db.Column(db.Boolean, default=False)
    sust_crea_contactos = db.Column(db.Boolean, default=False)

    # Relación padre
    solicitud = db.relationship(
        "Solicitud",
        back_populates="sef", uselist=False, cascade="all, delete"
    )

    # 1 a N con Unidades
    sef_unidades = db.relationship(
        "SolicitudSEFUnidad",
        back_populates="sef",
        cascade="all, delete-orphan"
    )


# =====================================================
# SEF - UNIDADES (HIJAS DE SOLICITUDSEF)
# =====================================================

class SolicitudSEFUnidad(db.Model):
    __tablename__ = "solicitudes_sef_unidades"

    id = db.Column(db.Integer, primary_key=True)

    sef_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitudes_sef.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    accion_unidad = db.Column(db.String(20))
    nombre_unidad = db.Column(db.String(150))

    cpae_id = db.Column(db.Integer, db.ForeignKey("catalogo_cpae.id"))
    etv_id = db.Column(db.Integer, db.ForeignKey("catalogo_etv.id"))
    procesadora_id = db.Column(db.Integer, db.ForeignKey("catalogo_procesadora.id"))
    entidad_id = db.Column(db.Integer, db.ForeignKey("catalogo_entidad.id"))
    municipio_id = db.Column(db.Integer, db.ForeignKey("catalogo_municipio.id"))

    servicio_verificacion_tradicional = db.Column(db.Boolean, default=False, nullable=False)
    servicio_verificacion_electronica = db.Column(db.Boolean, default=False, nullable=False)
    servicio_cliente_certificado_central = db.Column(db.Boolean, default=False, nullable=False)
    servicio_dotacion_centralizada = db.Column(db.Boolean, default=False, nullable=False)
    servicio_integradora = db.Column(db.Boolean, default=False, nullable=False)
    servicio_dotacion = db.Column(db.Boolean, default=False, nullable=False)
    servicio_traslado = db.Column(db.Boolean, default=False, nullable=False)
    servicio_cofre = db.Column(db.Boolean, default=False, nullable=False)

    cofre_modelo = db.Column(db.String(50))
    relacion_dot_centralizada = db.Column(db.String(50))
    relacion_cc_centralizada = db.Column(db.String(50))

    calle_numero = db.Column(db.String(255))

    codigo_postal = db.Column(db.String(10))

    # Relación inversa
    sef = db.relationship(
        "SolicitudSEF",
        back_populates="sef_unidades")
    
    cpae = db.relationship("CatalogoCPAE")
    etv = db.relationship("CatalogoETV")
    procesadora = db.relationship("CatalogoProcesadora")
    entidad = db.relationship("CatalogoEntidad")
    municipio = db.relationship("CatalogoMunicipio")

# =====================================================
# SEF - CUENTAS (HIJAS DE SOLICITUDSEF)
# =====================================================

class SolicitudSEFCuenta(db.Model):
    __tablename__ = "solicitudes_sef_cuentas"

    id = db.Column(db.Integer, primary_key=True)

    sef_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitudes_sef.id", ondelete="CASCADE"),
        nullable=False
    )

    unidad_id = db.Column(
        db.Integer,
        db.ForeignKey("solicitudes_sef_unidades.id"),
        nullable=True
    )

    sucursal = db.Column(db.String(10))
    numero_cuenta = db.Column(db.String(20))
    moneda = db.Column(db.String(10))
    tipo_cuenta = db.Column(db.String(50))
     
    sef = db.relationship("SolicitudSEF", backref="sef_cuentas")
    unidad = db.relationship("SolicitudSEFUnidad")

# ==========================================
# CPAE
# ==========================================
class CatalogoCPAE(db.Model):
    __tablename__ = "catalogo_cpae"

    id = db.Column(db.Integer, primary_key=True)
    clave = db.Column(db.String(10), nullable=False)
    descripcion = db.Column(db.String(150), nullable=False)
    abreviatura = db.Column(db.String(10), nullable=False)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"{self.clave} - {self.descripcion}"

# ==========================================
# ETV (Empresas de Traslado de Valores)
# ==========================================
class CatalogoETV(db.Model):
    __tablename__ = "catalogo_etv"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"{self.nombre}"


# ==========================================
# DOCUMENT TEMPLATES
# ==========================================
class DocumentTemplate(db.Model):
    __tablename__ = "document_templates"

    id = db.Column(db.Integer, primary_key=True)

    slug = db.Column(db.Text, nullable=False)
    name = db.Column(db.Text, nullable=False)
    content_html = db.Column(db.Text, nullable=False)
    css = db.Column(db.Text, nullable=False, default="")
    cascaron = db.Column(db.Text, nullable=False)

    version = db.Column(db.Integer, nullable=False, default=1)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    updated_by = db.Column(db.Text, nullable=True)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("slug", "version", name="uq_document_templates_slug_version"),
        db.Index(
            "idx_document_templates_active",
            "slug",
            postgresql_where=db.text("is_active = TRUE")
        ),
    )

    def __repr__(self):
        return f"{self.slug} v{self.version}"


# ==========================================
# ADHESIONES
# ==========================================
class CatalogoAdhesion(db.Model):
    __tablename__ = "catalogo_adhesiones"

    id = db.Column(db.Integer, primary_key=True)

    clave = db.Column(db.String(100), nullable=False, index=True)
    numero = db.Column(db.String(100), nullable=False)

    vigente_desde = db.Column(db.Date, nullable=False)
    vigente_hasta = db.Column(db.Date, nullable=True)

    activo = db.Column(db.Boolean, nullable=False, default=True)

    updated_by = db.Column(db.String(120), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    __table_args__ = (
        db.Index("idx_adhesiones_clave", "clave"),
    )

    def __repr__(self):
        return f"{self.clave} - {self.numero}"


# ==========================================
# PROCESADORA
# ==========================================
class CatalogoProcesadora(db.Model):
    __tablename__ = "catalogo_procesadora"

    id = db.Column(db.Integer, primary_key=True)

    clave = db.Column(db.String(10), nullable=True)
    nombre = db.Column(db.String(150), nullable=False)

    etv_id = db.Column(
        db.Integer,
        db.ForeignKey("catalogo_etv.id"),
        nullable=True
    )

    cpae_id = db.Column(
        db.Integer,
        db.ForeignKey("catalogo_cpae.id"),
        nullable=True
    )

    cpae = db.relationship("CatalogoCPAE")


    etv = db.relationship("CatalogoETV", backref="procesadoras")

    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"{self.nombre}"


# ==========================================
# ENTIDAD FEDERATIVA (INEGI)
# ==========================================
class CatalogoEntidad(db.Model):
    __tablename__ = "catalogo_entidad"

    id = db.Column(db.Integer, primary_key=True)

    clave_inegi = db.Column(db.String(5), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)

    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"{self.nombre}"


# ==========================================
# MUNICIPIO (INEGI)
# ==========================================
class CatalogoMunicipio(db.Model):
    __tablename__ = "catalogo_municipio"

    id = db.Column(db.Integer, primary_key=True)

    clave_inegi = db.Column(db.String(10), nullable=True)
    nombre = db.Column(db.String(150), nullable=False)

    entidad_id = db.Column(
        db.Integer,
        db.ForeignKey("catalogo_entidad.id"),
        nullable=False
    )

    entidad = db.relationship("CatalogoEntidad", backref="municipios")

    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f"{self.nombre}"


# ==========================================
# MINUTAS
# ==========================================

class MeetingMinutes(db.Model):
    __tablename__ = "meeting_minutes"

    id = db.Column(db.Integer, primary_key=True)
    fecha_reunion = db.Column(db.Date, nullable=False)
    asunto = db.Column(db.Text, nullable=False)
    notas = db.Column(db.Text, nullable=True)
    acuerdos = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    # Relaciones
    attendees = db.relationship(
        "MeetingAttendee",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )

    commitments = db.relationship(
        "MeetingCommitment",
        back_populates="meeting",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"Minuta {self.id} - {self.asunto}"


class MeetingAttendee(db.Model):
    __tablename__ = "meeting_attendees"

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer,
        db.ForeignKey("meeting_minutes.id", ondelete="CASCADE"),
        nullable=False
    )

    nombre = db.Column(db.Text, nullable=False)
    cargo = db.Column(db.Text, nullable=True)

    meeting = db.relationship(
        "MeetingMinutes",
        back_populates="attendees"
    )

    def __repr__(self):
        return f"{self.nombre}"


class MeetingCommitment(db.Model):
    __tablename__ = "meeting_commitments"

    id = db.Column(db.Integer, primary_key=True)

    meeting_id = db.Column(
        db.Integer,
        db.ForeignKey("meeting_minutes.id", ondelete="CASCADE"),
        nullable=False
    )

    descripcion = db.Column(db.Text, nullable=False)
    responsable = db.Column(db.Text, nullable=False)
    eta = db.Column(db.Date, nullable=True)
    estatus = db.Column(
        db.Text,
        nullable=False,
        default="PENDIENTE"
    )

    meeting = db.relationship(
        "MeetingMinutes",
        back_populates="commitments"
    )

    def __repr__(self):
        return f"{self.descripcion} - {self.estatus}"
