from django import forms

from common.commands.abstract_base_command import AbstractBaseCommand
from common.forms.base_form import BaseForm


class PlayMovieForm(BaseForm):
    """
    Form for playing a movie.
    """
    movie_id = forms.IntegerField()


class PlayMovieCommand(AbstractBaseCommand):
    """
    Command for playing a movie.
    """

    def __init__(self, form: 'PlayMovieForm'):
        self.form = form

    def execute(self) -> None:
        super().execute()

        print("playing a movie!")
