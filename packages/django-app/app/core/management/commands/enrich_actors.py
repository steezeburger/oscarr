import asyncio
import logging

from asgiref.sync import sync_to_async
from django.core.management import BaseCommand
from plex.commands import EnrichMovieActorsCommand
from plex.forms import EnrichMovieActorsForm
from plex.models import PlexMovie
from plex.repositories import PlexMovieRepository

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
            movies = PlexMovieRepository.get_active_movies(without_enrichment=False, limit=limit)
            self.stdout.write("Enriching all active movies...")
        else:
            movies = PlexMovieRepository.get_active_movies(without_enrichment=True, limit=limit)
            self.stdout.write("Enriching movies without actor enrichment...")

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
                continue

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
        original_actor_count = len(movie.actors) if movie.actors else 0

        # Create form and run the enrichment command
        form = EnrichMovieActorsForm({"movie": movie.id, "max_actors": 30})

        # Validate form in sync context
        is_valid = await sync_to_async(lambda: form.is_valid())()
        if not is_valid:
            raise ValueError(f"Invalid form data: {form.errors}")

        command = EnrichMovieActorsCommand(form)
        await command.execute()

        # Refresh movie from DB since command saved it via repository
        await sync_to_async(movie.refresh_from_db)()

        new_actor_count = len(movie.actors) if movie.actors else 0
        self.stdout.write(
            f"    Actors: {original_actor_count} → {new_actor_count} "
            f"(+{new_actor_count - original_actor_count})"
        )
        if movie.tmdb_id:
            self.stdout.write(f"    TMDB ID: {movie.tmdb_id}")
