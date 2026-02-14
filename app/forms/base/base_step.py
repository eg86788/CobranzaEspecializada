# app/forms/base/base_step.py

from abc import ABC, abstractmethod

class BaseStep(ABC):

    name = None
    template = None

    @abstractmethod
    def validate(self, data):
        pass

    @abstractmethod
    def process(self, data, accumulated_data):
        pass
