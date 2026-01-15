import logging

from aiohttp import ClientSession
from common.commands.abstract_base_command import AbstractBaseCommand
from services.tmdb import TMDB

logger = logging.getLogger(__name__)


class EnrichMovieActorsCommand(AbstractBaseCommand):
    """
    Command to enrich a movie's actor list with data from TMDB.
    """

    def __init__(self, movie, session: ClientSession, max_actors: int = 30):
        super().__init__()
        self.movie = movie
        self.session = session
        self.max_actors = max_actors

    async def execute_async(self):
        """
        Execute the enrichment asynchronously.
        Updates the movie instance with enriched actors and TMDB ID.
        """
        plex_actors = list(self.movie.actors) if self.movie.actors else []
        tmdb_id = self.movie.tmdb_id

        # If we don't have a TMDB ID, search by title and year
        if not tmdb_id:
            logger.info(f"Searching TMDB for {self.movie.title} ({self.movie.year})...")
            tmdb_id = await TMDB.find_movie_id(
                str(self.movie.title),
                self.movie.year,
                self.session,  # type: ignore[arg-type]
            )
            if not tmdb_id:
                logger.warning(f"Could not find TMDB ID for {self.movie.title}")
                return

        # Fetch credits from TMDB
        try:
            credits = await TMDB.get_movie_credits(tmdb_id, self.session)
            tmdb_actors = [actor["name"] for actor in credits.get("cast", [])]

            # Merge actors: Plex actors first, then TMDB actors not in the list
            enriched_actors = plex_actors.copy()
            plex_actors_lower = {actor.lower() for actor in enriched_actors}

            for tmdb_actor in tmdb_actors:
                if tmdb_actor.lower() not in plex_actors_lower:
                    enriched_actors.append(tmdb_actor)

            # Limit to max_actors
            enriched_actors = enriched_actors[: self.max_actors]

            # Update the movie
            self.movie.actors = enriched_actors  # type: ignore[assignment]
            if not self.movie.tmdb_id:
                self.movie.tmdb_id = tmdb_id  # type: ignore[assignment]

            logger.info(
                f"Enriched {self.movie.title}: {len(plex_actors)} Plex + "
                f"{len(tmdb_actors)} TMDB = {len(enriched_actors)} total"
            )

        except Exception as e:
            logger.exception(f"Error enriching actors for {self.movie.title}: {e}")
            raise
