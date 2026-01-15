from common.forms.base_form import BaseForm
from django import forms


class EnrichMovieActorsForm(BaseForm):
    """
    Form for validating EnrichMovieActorsCommand input.
    """

    movie = forms.ModelChoiceField(
        queryset=None,  # Set in __init__
        required=True,
        help_text="The movie to enrich with TMDB actor data",
    )
    max_actors = forms.IntegerField(
        required=False,
        initial=30,
        min_value=1,
        max_value=100,
        help_text="Maximum number of actors to store",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Import here to avoid circular imports
        from plex.models import PlexMovie

        self.fields["movie"].queryset = PlexMovie.objects.all()

    def clean_max_actors(self):
        max_actors = self.cleaned_data.get("max_actors")
        return max_actors or 30
