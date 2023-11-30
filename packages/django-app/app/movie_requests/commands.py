import stringcase
from django.forms import fields

from common.commands.abstract_base_command import AbstractBaseCommand
from common.forms.base_form import BaseForm
from services.radarr import Radarr
from services.tmdb import TMDB


def get_radarr_request_from_tmdb_info(tmdb_info: dict) -> dict:
    """
    Converts a dictionary from a tmdb response into a dictionary that can
    be sent to Radarr's API
    """

    tmdb_id = tmdb_info.get('id')
    title = tmdb_info.get('title')
    title_slug = f'{stringcase.snakecase(title)}-{tmdb_id}'
    full_poster_path = TMDB.get_poster_full_path(tmdb_info.get('poster_path'))

    return {
        'tmdb_id': tmdb_id,
        'title': title,
        'title_slug': title_slug,
        'full_poster_path': full_poster_path
    }


class RequestMovieForm(BaseForm):
    tmdb_id = fields.IntegerField()


class RequestMovieCommand(AbstractBaseCommand):
    """
    Command for requesting a movie.
    """

    def __init__(self, form: 'RequestMovieForm'):
        self.form = form

    async def execute(self) -> (bool, str):
        super().execute()

        tmdb_id = self.form.cleaned_data['tmdb_id']
        existing_request = Radarr.get_movie(tmdb_id=tmdb_id)

        print(f"existing radarr movie: {existing_request}")

        if existing_request and existing_request['sizeOnDisk'] > 0:
            return False, f"This request has already been fulfilled."
        if existing_request and existing_request['sizeOnDisk'] == 0:
            message = (
                f"This movie has already been requested.\r\n"
                f"Reach out to the server administrator if you think there is an issue.")
            return False, message

        # get movie info from TMDB, so we can create a request for radarr
        movie_info = TMDB.get_movie_by_id(tmdb_id)
        if movie_info.get('belongs_to_collection'):
            message = (
                f"This movie belongs to a collection, and I don't know how to handle that yet.\r\n"
                f"Try requesting just the individual movie.")
            return False, message

        # TODO - replace with ombi
        try:
            # creates the movie in Radarr
            radarr_request = get_radarr_request_from_tmdb_info(movie_info)
            Radarr.create_movie(radarr_request)
        except Exception as e:
            return False, f"Failed to create movie on Radarr: {str(e)}"

        return True, f"Request created!"
