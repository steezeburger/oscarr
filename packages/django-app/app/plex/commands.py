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
    Sync Oscarr's database with the movies on Plex. Stops syncing when we
    reach a movie that was added before the latest movie in the database.

    Plex API doesn't allow filtering by addedAt, so we page through movies
    sorted addedAt:desc and bail when we hit one we've already seen.
    """

    def execute(self) -> None:
        super().execute()

        latest_movie = PlexMovieRepository.get_latest()
        forms_to_enrich: list[EnrichMovieActorsForm] = []

        for movie in Plex.fetch_movies(sort="addedAt:desc", container_start=0, container_size=5):
            added_at = Plex.normalize_added_at(movie.addedAt)
            if latest_movie and added_at <= latest_movie.created_at:
                break

            try:
                movie_details = Plex.extract_movie_details(movie)
                plex_movie = PlexMovieRepository.get_or_create(movie_details)
                plex_movie.created_at = added_at
                plex_movie.save()
                print(f"Created PlexMovie: {plex_movie}")

                form = EnrichMovieActorsForm({"movie": plex_movie.id, "max_actors": 30})
                if form.is_valid():
                    forms_to_enrich.append(form)
                else:
                    logger.warning(f"Invalid form for enriching {plex_movie.title}: {form.errors}")
            except Exception:
                logger.exception(f"Failed to create PlexMovie: {movie}")

        if forms_to_enrich:
            asyncio.run(_enrich_all(forms_to_enrich))


async def _enrich_all(forms: list[EnrichMovieActorsForm]) -> None:
    """
    Run all enrichments inside one event loop with a shared HTTP session,
    instead of one event loop + one ClientSession per movie.
    """
    async with ClientSession() as session:
        results = await asyncio.gather(
            *(EnrichMovieActorsCommand(form).execute(session=session) for form in forms),
            return_exceptions=True,
        )
        for form, result in zip(forms, results, strict=True):
            if isinstance(result, Exception):
                movie = form.cleaned_data.get("movie")
                title = getattr(movie, "title", "<unknown>")
                logger.warning(f"Failed to enrich actors for {title}: {result}")


class EnrichMovieActorsCommand(AbstractBaseCommand):
    """
    Enrich a movie's actor list with data from TMDB.
    """

    def __init__(self, form: EnrichMovieActorsForm):
        self.form = form

    async def execute(self, session: ClientSession | None = None):
        super().execute()

        movie = self.form.cleaned_data["movie"]
        max_actors = self.form.cleaned_data["max_actors"]

        if session is None:
            async with ClientSession() as new_session:
                await self._do_enrich(movie, max_actors, new_session)
        else:
            await self._do_enrich(movie, max_actors, session)

    async def _do_enrich(self, movie, max_actors: int, session: ClientSession) -> None:
        plex_actors = list(movie.actors) if movie.actors else []
        tmdb_id = movie.tmdb_id

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

        try:
            credits = await TMDB.get_movie_credits(tmdb_id, session)
            tmdb_actors = [actor["name"] for actor in credits.get("cast", [])]

            enriched_actors = plex_actors.copy()
            plex_actors_lower = {actor.lower() for actor in enriched_actors}

            for tmdb_actor in tmdb_actors:
                if tmdb_actor.lower() not in plex_actors_lower:
                    enriched_actors.append(tmdb_actor)

            enriched_actors = enriched_actors[:max_actors]

            await PlexMovieRepository.update_movie_actors_async(
                movie=movie, actors=enriched_actors, tmdb_id=tmdb_id
            )

            logger.info(
                f"Enriched {movie.title}: {len(plex_actors)} Plex + "
                f"{len(tmdb_actors)} TMDB = {len(enriched_actors)} total"
            )
        except Exception as e:
            logger.exception(f"Error enriching actors for {movie.title}: {e}")
            raise
