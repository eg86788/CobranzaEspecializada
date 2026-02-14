# app/forms/base/base_formulario.py

from app.forms.base.workflow_engine import WorkflowEngine

class BaseFormulario:

    def __init__(self):
        self.steps = self.define_steps()
        self.workflow = WorkflowEngine(self.steps)
        self.data = {}

    def define_steps(self):
        raise NotImplementedError

    def current_step(self):
        return self.workflow.current_step()

    def process_step(self, form_data):
        step = self.current_step()

        errors = step.validate(form_data)
        if errors:
            return errors

        self.data = step.process(form_data, self.data)

        if not self.workflow.is_last():
            self.workflow.next()

        return []
