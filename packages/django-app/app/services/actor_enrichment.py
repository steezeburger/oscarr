import logging

from aiohttp import ClientSession
from services.tmdb import TMDB

logger = logging.getLogger(__name__)


class ActorEnrichmentService:
    """
    Service for enriching actor data using TMDB API.
    """

    @classmethod
    async def enrich_actors(
        cls,
        title: str,
        year: int | None,
        tmdb_id: int | None,
        plex_actors: list[str],
        session: ClientSession,
        max_actors: int = 30,
    ) -> tuple[list[str], int | None]:
        """
        Enrich actor list by fetching full cast from TMDB and merging with Plex actors.

        Args:
            title: Movie title
            year: Release year
            tmdb_id: TMDB ID (if available)
            plex_actors: List of actor names from Plex
            session: aiohttp ClientSession
            max_actors: Maximum number of actors to return (default: 30)

        Returns:
            Tuple of (enriched actor list, tmdb_id used)
        """
        try:
            # If we don't have a TMDB ID, try to find it by searching
            if not tmdb_id:
                logger.info(f"No TMDB ID for {title} ({year}), searching TMDB...")
                tmdb_id = await TMDB.find_movie_id_by_title_and_year(title, year, session)
                if not tmdb_id:
                    logger.warning(f"Could not find TMDB ID for {title} ({year})")
                    return plex_actors, None
                logger.info(f"Found TMDB ID {tmdb_id} for {title} ({year})")

            # Fetch credits from TMDB
            credits = await TMDB.get_movie_credits(tmdb_id, session)
            tmdb_actors = [actor["name"] for actor in credits.get("cast", [])]

            # Merge actors: keep Plex actors first, then add TMDB actors not already in the list
            # This preserves any Plex-specific ordering while adding missing actors
            enriched_actors = plex_actors.copy() if plex_actors else []
            plex_actors_lower = {actor.lower() for actor in enriched_actors}

            for tmdb_actor in tmdb_actors:
                if tmdb_actor.lower() not in plex_actors_lower:
                    enriched_actors.append(tmdb_actor)

            # Limit to max_actors
            enriched_actors = enriched_actors[:max_actors]

            logger.info(
                f"Enriched {title}: {len(plex_actors or [])} Plex actors + "
                f"{len(tmdb_actors)} TMDB actors = {len(enriched_actors)} total"
            )

            return enriched_actors, tmdb_id

        except Exception as e:
            logger.exception(f"Error enriching actors for {title} ({year}): {e}")
            return plex_actors, tmdb_id
