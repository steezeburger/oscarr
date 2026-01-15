import asyncio
import logging

from aiohttp import ClientSession
from common.commands.abstract_base_command import AbstractBaseCommand
from services.actor_enrichment import ActorEnrichmentService
from services.plex import Plex

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

    async def _enrich_movie_actors(self, plex_movie):
        """
        Enrich a movie's actor list with data from TMDB.

        Args:
            plex_movie: PlexMovie instance to enrich
        """
        async with ClientSession() as session:
            # Get current values from Django fields
            current_actors: list[str] = plex_movie.actors or []  # type: ignore[assignment]
            current_tmdb_id: int | None = plex_movie.tmdb_id  # type: ignore[assignment]
            current_title: str = plex_movie.title  # type: ignore[assignment]
            current_year: int | None = plex_movie.year  # type: ignore[assignment]

            enriched_actors, found_tmdb_id = await ActorEnrichmentService.enrich_actors(
                title=current_title,
                year=current_year,
                tmdb_id=current_tmdb_id,
                plex_actors=current_actors,
                session=session,
            )

            # Update the movie with enriched data
            plex_movie.actors = enriched_actors  # type: ignore[assignment]
            if found_tmdb_id and not current_tmdb_id:
                plex_movie.tmdb_id = found_tmdb_id  # type: ignore[assignment]

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
                    asyncio.run(self._enrich_movie_actors(plex_movie))
                except Exception as e:
                    logger.warning(f"Failed to enrich actors for {plex_movie.title}: {e}")

                plex_movie.save()
                print(f"Created PlexMovie: {plex_movie}")
            except Exception as e:
                logger.exception(f"Failed to create PlexMovie: {movie}")
                logger.exception(e)
