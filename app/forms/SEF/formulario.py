# app/forms/SEF/formulario.py

from app.forms.base.base_formulario import BaseFormulario
from .steps.datos_generales import DatosGeneralesStep
from .steps.unidades import UnidadesStep
from .steps.usuarios import UsuariosStep

class FormularioCobranza(BaseFormulario):

    def define_steps(self):
        return [
            DatosGeneralesStep(),
            UnidadesStep(),
            UsuariosStep(),
        ]
