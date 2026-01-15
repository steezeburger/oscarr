import logging
from datetime import UTC

from django.conf import settings
from plexapi.myplex import MyPlexAccount
from plexapi.server import PlexServer

logger = logging.getLogger(__name__)


class Plex:
    """
    Service facade for Plex API interactions.
    """

    @classmethod
    def get_account(cls) -> MyPlexAccount:
        """
        Authenticate and return a MyPlexAccount instance.
        """
        return MyPlexAccount(settings.PLEX_USERNAME, settings.PLEX_PASSWORD)

    @classmethod
    def get_server(cls) -> PlexServer:
        """
        Connect to and return the configured Plex server.
        """
        account = cls.get_account()
        return account.resource(settings.PLEX_SERVER_NAME).connect()

    @classmethod
    def get_movies_section(cls):
        """
        Get the Movies library section from the Plex server.
        """
        server = cls.get_server()
        return server.library.section("Movies")

    @classmethod
    def fetch_movies(cls, sort="addedAt:desc", container_start=0, container_size=5):
        """
        Fetch movies from the Plex library with pagination and sorting.

        Args:
            sort: Sort order (default: 'addedAt:desc')
            container_start: Starting index for pagination
            container_size: Number of movies to fetch

        Returns:
            Generator of movie objects from Plex
        """
        movies_section = cls.get_movies_section()
        return movies_section.all(
            sort=sort, container_start=container_start, container_size=container_size
        )

    @classmethod
    def extract_tmdb_id(cls, movie) -> int | None:
        """
        Extract TMDB ID from Plex movie guids.

        Args:
            movie: Plex movie object

        Returns:
            TMDB ID as integer, or None if not found
        """
        try:
            for guid in movie.guids:
                guid_id = guid.id
                if guid_id.startswith("tmdb://"):
                    return int(guid_id.replace("tmdb://", ""))
        except (AttributeError, ValueError) as e:
            logger.warning(f"Failed to extract TMDB ID from {movie.title}: {e}")
        return None

    @classmethod
    def extract_movie_details(cls, movie) -> dict:
        """
        Extract relevant movie details from a Plex movie object.

        Args:
            movie: Plex movie object

        Returns:
            Dictionary containing movie details
        """
        return {
            "plex_guid": movie.guid,
            "tmdb_id": cls.extract_tmdb_id(movie),
            "title": movie.title,
            "year": movie.year,
            "duration": movie.duration,
            "actors": [t.tag for t in movie.actors],
            "genres": [t.tag for t in movie.genres],
            "directors": [t.tag for t in movie.directors],
            "producers": [t.tag for t in movie.producers],
            "writers": [t.tag for t in movie.writers],
        }

    @staticmethod
    def normalize_added_at(added_at):
        """
        Normalize the addedAt datetime to UTC timezone.

        Args:
            added_at: datetime object from Plex

        Returns:
            datetime with UTC timezone
        """
        return added_at.replace(tzinfo=UTC)
