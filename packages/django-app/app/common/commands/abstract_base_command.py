from abc import ABC, abstractmethod

from django.core.exceptions import ValidationError

from common.forms.base_form import BaseForm


class AbstractBaseCommand(ABC):
    """
    The Command interface declares a method for executing a command.
    """

    form: BaseForm

    @abstractmethod
    def execute(self) -> None:
        if hasattr(self, "form") and not self.form.is_valid():
            raise ValidationError(self.form.errors.as_json())
