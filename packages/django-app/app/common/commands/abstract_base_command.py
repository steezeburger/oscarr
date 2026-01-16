from abc import ABC

from common.forms.base_form import BaseForm
from django.core.exceptions import ValidationError


class AbstractBaseCommand(ABC):
    """
    Base class for commands. Supports both sync and async execution.

    Subclasses should implement execute() - either as a sync or async method.
    Form validation is performed automatically if a form is present.
    """

    form: BaseForm

    def execute(self):
        """
        Execute the command. Override this in subclasses.
        Can be either sync or async depending on the command needs.
        """
        if hasattr(self, "form") and not self.form.is_valid():
            errors_json = self.form.errors.as_json() if self.form.errors else "{}"
            raise ValidationError(errors_json)
