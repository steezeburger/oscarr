import stringcase
from aiohttp import ClientSession
from asgiref.sync import sync_to_async
from common.commands.abstract_base_command import AbstractBaseCommand
from common.forms.base_form import BaseForm
from core.models import User
from django.conf import settings
from django.forms import fields
from services.ombi import Ombi
from services.radarr import Radarr
from services.tmdb import TMDB


def get_radarr_request_from_tmdb_info(tmdb_info: dict) -> dict:
    """
    Converts a dictionary from a tmdb response into a dictionary that can
    be sent to Radarr's API
    """

    tmdb_id = tmdb_info.get("id")
    title = tmdb_info.get("title")
    title_slug = f"{stringcase.snakecase(title)}-{tmdb_id}"
    full_poster_path = TMDB.get_poster_full_path(tmdb_info.get("poster_path"))

    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "title_slug": title_slug,
        "full_poster_path": full_poster_path,
    }


class RequestMovieForm(BaseForm):
    tmdb_id = fields.IntegerField()
    discord_username = fields.CharField(required=False)


class RequestRadarrMovieCommand(AbstractBaseCommand):
    """
    Command for requesting a movie on Radarr.
    """

    def __init__(self, form: "RequestMovieForm", session: ClientSession):
        self.form = form
        self.session = session

    async def execute(self) -> tuple[bool, str]:
        super().execute()

        tmdb_id = self.form.cleaned_data["tmdb_id"]
        existing_request = await Radarr.get_movie(tmdb_id=tmdb_id, session=self.session)

        print(f"existing radarr movie: {existing_request}")

        if existing_request and existing_request["sizeOnDisk"] > 0:
            return False, "This request has already been fulfilled."
        if existing_request and existing_request["sizeOnDisk"] == 0:
            message = (
                "This movie has already been requested.\r\n"
                "Reach out to the server administrator if you think there is an issue."
            )
            return False, message

        # get movie info from TMDB, so we can create a request for radarr
        movie_info = await TMDB.get_movie_by_id(tmdb_id, session=self.session)
        if movie_info.get("belongs_to_collection"):
            message = (
                "This movie belongs to a collection, and I don't know how to handle that yet.\r\n"
                "Try requesting just the individual movie."
            )
            return False, message

        try:
            # creates the movie in Radarr
            radarr_request = get_radarr_request_from_tmdb_info(movie_info)
            await Radarr.create_movie(radarr_request, session=self.session)
        except Exception as e:
            return False, f"Failed to create movie on Radarr: {str(e)}"

        return True, "Request created!"


async def get_ombi_request_from_tmdb_info(tmdb_info: dict, username: str) -> dict:
    # Default to admin UID
    uid = settings.OMBI_UID_MAP.get("admin")

    # Define a synchronous function to get the user's Ombi UID
    def get_user_ombi_uid(username):
        try:
            user = User.objects.get(discord_username=username)
            if user.ombi_uid:
                return user.ombi_uid
            return None
        except User.DoesNotExist:  # type: ignore[attr-defined]
            return None

    # Wrap the synchronous function with sync_to_async
    get_user_ombi_uid_async = sync_to_async(get_user_ombi_uid)

    # Call the async function
    user_uid = await get_user_ombi_uid_async(username)

    # Use the user's UID if found, otherwise default to admin
    if user_uid:
        uid = user_uid

    return {
        "theMovieDbId": tmdb_info.get("id"),
        "languageCode": "en",
        "is4kRequest": False,
        "requestOnBehalf": uid,
        "rootFolderOverride": None,
        "qualityPathOverride": None,
    }


class RequestOmbiMovieCommand(AbstractBaseCommand):
    """
    Command for requesting a movie on Ombi.
    """

    def __init__(self, form: "RequestMovieForm", session: ClientSession):
        self.form = form
        self.session = session

    async def execute(self) -> tuple[bool, str]:
        super().execute()

        tmdb_id = self.form.cleaned_data["tmdb_id"]
        existing_request = await Radarr.get_movie(tmdb_id=tmdb_id, session=self.session)

        print(f"existing radarr movie: {existing_request}")

        if existing_request and existing_request["sizeOnDisk"] > 0:
            return (
                False,
                f"This request has already been fulfilled. {existing_request['title']} is on the server!",
            )
        if existing_request and existing_request["sizeOnDisk"] == 0:
            message = (
                f"{existing_request['title']} has already been requested.\r\n"
                f"Reach out to the server administrator if you think there is an issue."
            )
            return False, message

        movie_info = await TMDB.get_movie_by_id(tmdb_id, session=self.session)
        print(f"movie info: {movie_info}")

        try:
            # creates the movie request in ombi
            ombi_request = await get_ombi_request_from_tmdb_info(
                movie_info, self.form.cleaned_data["discord_username"]
            )
            await Ombi.create_request(ombi_request, session=self.session)
            return (
                True,
                f"Request created! \n https://www.themoviedb.org/movie/{movie_info.get('id')}",
            )
        except Exception as e:
            return False, f"Failed to create movie on Ombi: {str(e)}"
