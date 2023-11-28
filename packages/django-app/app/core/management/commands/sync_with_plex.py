import logging
from datetime import timezone

from django.conf import settings
from django.core.management import BaseCommand
from plexapi.myplex import MyPlexAccount

from plex.repositories import PlexMovieRepository

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Sync Leo's database with the movies on the Plex.
    """

    def handle(self, *args, **options):
        account = MyPlexAccount(settings.PLEX_USERNAME,
                                settings.PLEX_PASSWORD)
        plex = account.resource(settings.PLEX_SERVER_NAME).connect()

        movies = plex.library.section('Movies')

        # TODO - schedule this job to run every night
        # FIXME - had to pick a relatively high number for container_size
        #  as filtering with `addedAt__gt=` or `addedAt__startswith=` did not work
        for movie in movies.all(sort='addedAt:desc',
                                container_start=0,
                                container_size=100):

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

                plex_movie.created_at = movie.addedAt.replace(tzinfo=timezone.utc)
                plex_movie.save()
                print(f'Created PlexMovie: {plex_movie}')
            except Exception as e:
                logger.exception(f"Failed to create PlexMovie: {movie}")
                logger.exception(e)
