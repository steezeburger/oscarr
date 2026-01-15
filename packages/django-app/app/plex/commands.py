import asyncio
import logging

from common.commands.abstract_base_command import AbstractBaseCommand
from services.plex import Plex

from plex.enrich_movie_actors_command import EnrichMovieActorsCommand
from plex.repositories import PlexMovieRepository

logger = logging.getLogger(__name__)


class SyncWithPlexCommand(AbstractBaseCommand):
    """
    Sync Oscarr's database with the movies on the Plex.
    Stops syncing when we get to a movie that was added
    before the latest movie in the database.

    Unfortunately the Plex API doesn't allow us to filter
    by addedAt, so we have to get a page of movies.
    """

    def execute(self) -> None:
        super().execute()

        latest_movie = PlexMovieRepository.get_latest()

        for movie in Plex.fetch_movies(sort="addedAt:desc", container_start=0, container_size=5):
            added_at = Plex.normalize_added_at(movie.addedAt)
            if latest_movie and added_at <= latest_movie.created_at:
                # break out of loop if we start to get a movie
                # added before the latest movie in the database
                return

            try:
                movie_details = Plex.extract_movie_details(movie)
                plex_movie = PlexMovieRepository.get_or_create(movie_details)

                plex_movie.created_at = added_at

                # Enrich actors with TMDB data
                try:
                    command = EnrichMovieActorsCommand(plex_movie)
                    asyncio.run(command.execute())
                except Exception as e:
                    logger.warning(f"Failed to enrich actors for {plex_movie.title}: {e}")

                plex_movie.save()
                print(f"Created PlexMovie: {plex_movie}")
            except Exception as e:
                logger.exception(f"Failed to create PlexMovie: {movie}")
                logger.exception(e)
