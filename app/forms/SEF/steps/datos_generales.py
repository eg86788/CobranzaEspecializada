# app/forms/cobranza_especializada/steps/datos_generales.py

from app.forms.base.base_step import BaseStep

class DatosGeneralesStep(BaseStep):

    name = "datos_generales"
    template = "cobranza/datos_generales.html"

    def validate(self, data):
        errors = []

        if not data.get("cliente"):
            errors.append("Cliente obligatorio")

        if not data.get("tipo_tramite"):
            errors.append("Tipo de trámite obligatorio")

        return errors

    def process(self, data, accumulated_data):
        accumulated_data.update({
            "cliente": data.get("cliente"),
            "tipo_tramite": data.get("tipo_tramite"),
        })
        return accumulated_data
