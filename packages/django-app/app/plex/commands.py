import asyncio
import logging
from dataclasses import dataclass

from aiohttp import ClientSession
from common.commands.abstract_base_command import AbstractBaseCommand
from services.plex import Plex
from services.tmdb import TMDB

from plex.forms import EnrichMovieActorsForm
from plex.repositories import PlexMovieRepository

logger = logging.getLogger(__name__)

# keep this low so TMDB doesn't rate limit us
MAX_CONCURRENT_ENRICHMENTS = 5


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
            except Exception:
                logger.exception(f"Failed to create PlexMovie: {movie}")


class EnrichMovieActorsCommand(AbstractBaseCommand):
    """
    Enrich a movie's actor list with data from TMDB.
    """

    def __init__(self, form: EnrichMovieActorsForm):
        self.form = form

    async def execute(self, session: ClientSession | None = None) -> bool:
        """
        Returns True if the movie was enriched, False if TMDB couldn't find it.
        """
        super().execute()

        movie = self.form.cleaned_data["movie"]
        max_actors = self.form.cleaned_data["max_actors"]

        await PlexMovieRepository.mark_enrichment_attempted_async(movie)

        if session is None:
            async with ClientSession() as new_session:
                return await self._do_enrich(movie, max_actors, new_session)
        return await self._do_enrich(movie, max_actors, session)

    async def _do_enrich(self, movie, max_actors: int, session: ClientSession) -> bool:
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
                return False

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
            return True
        except Exception as e:
            logger.exception(f"Error enriching actors for {movie.title}: {e}")
            raise


@dataclass
class EnrichActorsResult:
    enriched: int = 0
    not_found: int = 0
    failed: int = 0

    @property
    def total(self) -> int:
        return self.enriched + self.not_found + self.failed


class EnrichActorsCommand(AbstractBaseCommand):
    """
    Enrich actor data from TMDB for a batch of movies.

    By default only picks up movies that haven't been enriched yet, skipping
    ones attempted in the last 24 hours. Runs them all in one event loop with
    a shared HTTP session, at most MAX_CONCURRENT_ENRICHMENTS at a time.
    """

    def __init__(self, enrich_all: bool = False, limit: int | None = None):
        self.enrich_all = enrich_all
        self.limit = limit

    def execute(self) -> EnrichActorsResult:
        super().execute()

        if self.enrich_all:
            movies = PlexMovieRepository.get_active_movies(limit=self.limit)
        else:
            movies = PlexMovieRepository.get_movies_to_enrich(limit=self.limit)

        # validate up front, the ORM can't be used synchronously inside the event loop
        forms = []
        for movie in movies:
            form = EnrichMovieActorsForm({"movie": movie.pk, "max_actors": 30})
            if form.is_valid():
                forms.append(form)
            else:
                logger.warning(f"Invalid form for enriching {movie.title}: {form.errors}")

        logger.info(f"Found {len(forms)} movies to enrich")

        result = EnrichActorsResult()
        if not forms:
            return result

        outcomes = asyncio.run(self._enrich_all(forms))
        for form, outcome in zip(forms, outcomes, strict=True):
            title = form.cleaned_data["movie"].title
            if isinstance(outcome, BaseException):
                result.failed += 1
                logger.warning(f"Failed to enrich actors for {title}: {outcome}")
            elif outcome:
                result.enriched += 1
            else:
                result.not_found += 1

        return result

    async def _enrich_all(self, forms: list[EnrichMovieActorsForm]) -> list[bool | BaseException]:
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_ENRICHMENTS)

        async with ClientSession() as session:

            async def enrich(form: EnrichMovieActorsForm) -> bool:
                async with semaphore:
                    return await EnrichMovieActorsCommand(form).execute(session=session)

            return await asyncio.gather(*(enrich(form) for form in forms), return_exceptions=True)
