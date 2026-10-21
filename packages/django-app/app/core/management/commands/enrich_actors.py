import asyncio
import logging
from typing import cast

from aiohttp import ClientSession
from django.core.management import BaseCommand
from plex.commands import EnrichMovieActorsCommand
from plex.forms import EnrichMovieActorsForm
from plex.models import PlexMovie
from plex.repositories import PlexMovieRepository

logger = logging.getLogger(__name__)

# keep this low so TMDB doesn't rate limit us
MAX_CONCURRENT_ENRICHMENTS = 5


class Command(BaseCommand):
    """
    Management command to enrich actor data for existing movies using TMDB.

    By default only picks up movies that haven't been enriched yet, skipping
    ones TMDB couldn't find in the last 24 hours. Runs on cron after the plex sync.
    """

    help = "Enrich actor data for movies using TMDB API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Enrich all movies (default: only movies without actor enrichment)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of movies to process",
        )

    def handle(self, *args, **options):
        enrich_all = options["all"]
        limit = options["limit"]

        if enrich_all:
            movies = PlexMovieRepository.get_active_movies(without_enrichment=False, limit=limit)
            self.stdout.write("Enriching all active movies...")
        else:
            movies = PlexMovieRepository.get_movies_to_enrich(limit=limit)
            self.stdout.write("Enriching movies without actor enrichment...")

        # validate up front, the ORM can't be used synchronously inside the event loop
        forms = []
        for movie in movies:
            form = EnrichMovieActorsForm({"movie": movie.pk, "max_actors": 30})
            if form.is_valid():
                forms.append(form)
            else:
                logger.warning(f"Invalid form for enriching {movie.title}: {form.errors}")

        total_movies = len(forms)
        self.stdout.write(f"Found {total_movies} movies to enrich")

        if total_movies == 0:
            self.stdout.write(self.style.SUCCESS("No movies to enrich!"))  # type: ignore[attr-defined]
            return

        results = asyncio.run(self._enrich_all(forms))

        enriched = sum(1 for result in results if result is True)
        not_found = sum(1 for result in results if result is False)
        failed = sum(1 for result in results if isinstance(result, BaseException))

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Enrichment complete!"))  # type: ignore[attr-defined]
        self.stdout.write(f"  Total processed: {len(results)}")
        self.stdout.write(f"  Successfully enriched: {enriched}")
        self.stdout.write(f"  Not found on TMDB: {not_found}")
        self.stdout.write(f"  Failed: {failed}")

    async def _enrich_all(self, forms: list[EnrichMovieActorsForm]) -> list[bool | BaseException]:
        """
        Run all enrichments in one event loop with a shared HTTP session,
        at most MAX_CONCURRENT_ENRICHMENTS at a time.
        """
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_ENRICHMENTS)
        total = len(forms)

        async with ClientSession() as session:

            async def enrich(index: int, form: EnrichMovieActorsForm) -> bool:
                async with semaphore:
                    return await self._enrich_movie(index, total, form, session)

            return await asyncio.gather(
                *(enrich(index, form) for index, form in enumerate(forms, start=1)),
                return_exceptions=True,
            )

    async def _enrich_movie(
        self, index: int, total: int, form: EnrichMovieActorsForm, session: ClientSession
    ) -> bool:
        """
        Enrich a single movie's actor data. The command updates the form's
        movie instance in place, so its counts are current afterwards.
        """
        movie = cast(PlexMovie, form.cleaned_data["movie"])
        original_actor_count = len(cast(list[str], movie.actors)) if movie.actors else 0
        self.stdout.write(f"[{index}/{total}] Processing: {movie.title} ({movie.year})")

        try:
            enriched = await EnrichMovieActorsCommand(form).execute(session=session)
        except Exception as e:
            logger.exception(f"Failed to enrich {movie.title}: {e}")
            self.stdout.write(self.style.ERROR(f"  ✗ Failed {movie.title}: {e}"))  # type: ignore[attr-defined]
            raise

        if not enriched:
            self.stdout.write(self.style.WARNING(f"  - Not found on TMDB: {movie.title}"))  # type: ignore[attr-defined]
            return False

        new_actor_count = len(cast(list[str], movie.actors)) if movie.actors else 0
        self.stdout.write(
            self.style.SUCCESS(  # type: ignore[attr-defined]
                f"  ✓ Enriched {movie.title}: {original_actor_count} → {new_actor_count} actors "
                f"(+{new_actor_count - original_actor_count}), TMDB ID: {movie.tmdb_id}"
            )
        )
        return True
