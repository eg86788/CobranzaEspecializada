# app/forms/base/workflow_engine.py

class WorkflowEngine:

    def __init__(self, steps):
        self.steps = steps
        self.current_index = 0

    def current_step(self):
        return self.steps[self.current_index]

    def next(self):
        if self.current_index + 1 < len(self.steps):
            self.current_index += 1
        return self.current_step()

    def is_last(self):
        return self.current_index == len(self.steps) - 1
