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

class Solicitud(db.Model):
    __tablename__ = "solicitudes"

    id = db.Column(db.Integer, primary_key=True)

    producto = db.Column(db.String(50), nullable=False, index=True)
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

class Producto(db.Model):
    __tablename__ = "catalogo_productos"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
