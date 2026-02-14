# app/services/solicitud_service.py

from datetime import datetime
from app.extensions import db
from app.models import Solicitud


class SolicitudService:

    @staticmethod
    def crear_solicitud(producto, usuario):
        solicitud = Solicitud(
            producto=producto,
            estado_actual="INICIO",
            estatus="BORRADOR",
            usuario_creador=usuario,
            data_json={}
        )

        db.session.add(solicitud)
        db.session.commit()

        return solicitud

    @staticmethod
    def obtener_solicitud(solicitud_id):
        return Solicitud.query.get(solicitud_id)

    @staticmethod
    def actualizar_step(solicitud_id, nuevo_estado, nuevos_datos):
        solicitud = Solicitud.query.get(solicitud_id)

        if not solicitud:
            raise ValueError("Solicitud no encontrada")

        # Mezclar datos acumulados
        data_actual = solicitud.data_json or {}
        data_actual.update(nuevos_datos)

        solicitud.data_json = data_actual
        solicitud.estado_actual = nuevo_estado
        solicitud.fecha_actualizacion = datetime.utcnow()

        db.session.commit()

        return solicitud

    @staticmethod
    def finalizar_solicitud(solicitud_id):
        solicitud = Solicitud.query.get(solicitud_id)

        if not solicitud:
            raise ValueError("Solicitud no encontrada")

        solicitud.estatus = "FINALIZADO"
        solicitud.fecha_actualizacion = datetime.utcnow()

        db.session.commit()

        return solicitud
