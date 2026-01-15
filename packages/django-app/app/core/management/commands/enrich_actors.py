import asyncio
import logging

from aiohttp import ClientSession
from django.core.management import BaseCommand
from plex.models import PlexMovie
from services.actor_enrichment import ActorEnrichmentService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to enrich actor data for existing movies using TMDB.

    This command can be run to backfill actor data for movies that were synced
    before the actor enrichment feature was added.
    """

    help = "Enrich actor data for movies using TMDB API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Enrich all movies (default: only movies without TMDB ID)",
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

        # Get movies to enrich
        if enrich_all:
            movies = PlexMovie.objects.filter(is_active=True).order_by("-created_at")
            self.stdout.write("Enriching all active movies...")
        else:
            movies = PlexMovie.objects.filter(is_active=True, tmdb_id__isnull=True).order_by(
                "-created_at"
            )
            self.stdout.write("Enriching movies without TMDB ID...")

        if limit:
            movies = movies[:limit]

        total_movies = movies.count()
        self.stdout.write(f"Found {total_movies} movies to enrich")

        if total_movies == 0:
            self.stdout.write(self.style.SUCCESS("No movies to enrich!"))  # type: ignore[attr-defined]
            return

        # Process movies
        processed = 0
        enriched = 0
        failed = 0

        for movie in movies:
            processed += 1
            self.stdout.write(
                f"[{processed}/{total_movies}] Processing: {movie.title} ({movie.year})"
            )

            try:
                asyncio.run(self._enrich_movie(movie))
                enriched += 1
                self.stdout.write(self.style.SUCCESS(f"  ✓ Enriched {movie.title}"))  # type: ignore[attr-defined]
            except Exception as e:
                failed += 1
                logger.exception(f"Failed to enrich {movie.title}: {e}")
                self.stdout.write(self.style.ERROR(f"  ✗ Failed: {e}"))  # type: ignore[attr-defined]

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Enrichment complete!"))  # type: ignore[attr-defined]
        self.stdout.write(f"  Total processed: {processed}")
        self.stdout.write(f"  Successfully enriched: {enriched}")
        self.stdout.write(f"  Failed: {failed}")

    async def _enrich_movie(self, movie: PlexMovie):
        """
        Enrich a single movie's actor data.
        """
        async with ClientSession() as session:
            # Get current values from Django fields
            current_actors: list[str] = movie.actors or []  # type: ignore[assignment]
            current_tmdb_id: int | None = movie.tmdb_id  # type: ignore[assignment]
            current_title: str = movie.title  # type: ignore[assignment]
            current_year: int | None = movie.year  # type: ignore[assignment]

            original_actor_count = len(current_actors)

            enriched_actors, found_tmdb_id = await ActorEnrichmentService.enrich_actors(
                title=current_title,
                year=current_year,
                tmdb_id=current_tmdb_id,
                plex_actors=current_actors,
                session=session,
            )

            # Update the movie
            movie.actors = enriched_actors  # type: ignore[assignment]
            if found_tmdb_id and not current_tmdb_id:
                movie.tmdb_id = found_tmdb_id  # type: ignore[assignment]

            movie.save()

            new_actor_count = len(enriched_actors)
            self.stdout.write(
                f"    Actors: {original_actor_count} → {new_actor_count} "
                f"(+{new_actor_count - original_actor_count})"
            )
            if found_tmdb_id:
                self.stdout.write(f"    TMDB ID: {found_tmdb_id}")
