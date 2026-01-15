from abc import ABC, abstractmethod

from common.forms.base_form import BaseForm
from django.core.exceptions import ValidationError


class AbstractBaseCommand(ABC):
    """
    The Command interface declares a method for executing a command.
    """

    form: BaseForm

    @abstractmethod
    def execute(self) -> None:
        if hasattr(self, "form") and not self.form.is_valid():
            errors_json = self.form.errors.as_json() if self.form.errors else "{}"
            raise ValidationError(errors_json)
