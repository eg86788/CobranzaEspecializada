# app/models.py
from datetime import datetime
from app.extensions import db

from datetime import datetime
from app import db

class Solicitud(db.Model):
    __tablename__ = "solicitudes"

    id = db.Column(db.Integer, primary_key=True)

    # Identificación del producto
    producto = db.Column(db.String(50), nullable=False, index=True)

    # Estado del workflow (nombre del step actual)
    estado_actual = db.Column(db.String(50), nullable=False)

    # Estatus de vida del trámite
    estatus = db.Column(
        db.String(20),
        nullable=False,
        default="BORRADOR",
        index=True
    )

    # Control de usuario
    usuario_creador = db.Column(db.String(50), nullable=False)

    # Datos acumulados dinámicos
    data_json = db.Column(db.JSON, nullable=False, default=dict)

    # Auditoría
    fecha_creacion = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    fecha_actualizacion = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
