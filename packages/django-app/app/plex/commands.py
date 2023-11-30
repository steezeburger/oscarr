import logging
from datetime import timezone

from django.conf import settings
from plexapi.myplex import MyPlexAccount

from common.commands.abstract_base_command import AbstractBaseCommand
from plex.repositories import PlexMovieRepository

logger = logging.getLogger()


class SyncWithPlexCommand(AbstractBaseCommand):
    """
    Sync Oscarr's database with the movies on the Plex.
    """

    def execute(self) -> None:
        super().execute()

        account = MyPlexAccount(settings.PLEX_USERNAME,
                                settings.PLEX_PASSWORD)
        plex = account.resource(settings.PLEX_SERVER_NAME).connect()
        movies = plex.library.section('Movies')

        latest_movie = PlexMovieRepository.get_latest()

        for movie in movies.all(sort='addedAt:desc',
                                container_start=0,
                                container_size=100):
            added_at = movie.addedAt.replace(tzinfo=timezone.utc)
            if latest_movie and added_at <= latest_movie.created_at:
                # break out of loop if we start to get a movie
                # added before the latest movie in the database
                return

            try:
                movie_details = {
                    'plex_guid': movie.guid,
                    'title': movie.title,
                    'year': movie.year,
                    'duration': movie.duration,
                    'actors': [t.tag for t in movie.actors],
                    'genres': [t.tag for t in movie.genres],
                    'directors': [t.tag for t in movie.directors],
                    'producers': [t.tag for t in movie.producers],
                    'writers': [t.tag for t in movie.writers],
                }
                plex_movie = PlexMovieRepository.get_or_create(movie_details)

                plex_movie.created_at = added_at
                plex_movie.save()
                print(f'Created PlexMovie: {plex_movie}')
            except Exception as e:
                logger.exception(f"Failed to create PlexMovie: {movie}")
                logger.exception(e)
