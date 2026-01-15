import asyncio
import logging

from aiohttp import ClientSession
from common.commands.abstract_base_command import AbstractBaseCommand
from services.plex import Plex
from services.tmdb import TMDB

from plex.forms import EnrichMovieActorsForm
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
                    form = EnrichMovieActorsForm({"movie": plex_movie.id, "max_actors": 30})
                    if form.is_valid():
                        command = EnrichMovieActorsCommand(form)
                        asyncio.run(command.execute())
                    else:
                        logger.warning(
                            f"Invalid form for enriching {plex_movie.title}: {form.errors}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to enrich actors for {plex_movie.title}: {e}")

                plex_movie.save()
                print(f"Created PlexMovie: {plex_movie}")
            except Exception as e:
                logger.exception(f"Failed to create PlexMovie: {movie}")
                logger.exception(e)


class EnrichMovieActorsCommand(AbstractBaseCommand):
    """
    Command to enrich a movie's actor list with data from TMDB.
    """

    def __init__(self, form: EnrichMovieActorsForm):
        self.form = form

    async def execute(self):
        """
        Execute the enrichment asynchronously.
        Updates the movie instance with enriched actors and TMDB ID.
        """
        super().execute()

        movie = self.form.cleaned_data["movie"]
        max_actors = self.form.cleaned_data["max_actors"]

        async with ClientSession() as session:
            plex_actors = list(movie.actors) if movie.actors else []
            tmdb_id = movie.tmdb_id

            # If we don't have a TMDB ID, search by title and year
            if not tmdb_id:
                logger.info(f"Searching TMDB for {movie.title} ({movie.year})...")
                tmdb_id = await TMDB.find_movie_id(
                    str(movie.title),
                    movie.year,
                    session,  # type: ignore[arg-type]
                )
                if not tmdb_id:
                    logger.warning(f"Could not find TMDB ID for {movie.title}")
                    return

            # Fetch credits from TMDB
            try:
                credits = await TMDB.get_movie_credits(tmdb_id, session)
                tmdb_actors = [actor["name"] for actor in credits.get("cast", [])]

                # Merge actors: Plex actors first, then TMDB actors not in the list
                enriched_actors = plex_actors.copy()
                plex_actors_lower = {actor.lower() for actor in enriched_actors}

                for tmdb_actor in tmdb_actors:
                    if tmdb_actor.lower() not in plex_actors_lower:
                        enriched_actors.append(tmdb_actor)

                # Limit to max_actors
                enriched_actors = enriched_actors[:max_actors]

                # Update the movie
                movie.actors = enriched_actors  # type: ignore[assignment]
                if not movie.tmdb_id:
                    movie.tmdb_id = tmdb_id  # type: ignore[assignment]

                logger.info(
                    f"Enriched {movie.title}: {len(plex_actors)} Plex + "
                    f"{len(tmdb_actors)} TMDB = {len(enriched_actors)} total"
                )

            except Exception as e:
                logger.exception(f"Error enriching actors for {movie.title}: {e}")
                raise
