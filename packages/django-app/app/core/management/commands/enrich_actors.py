from django.core.management import BaseCommand
from plex.commands import EnrichActorsCommand


class Command(BaseCommand):
    """
    Management command wrapper for EnrichActorsCommand so we can easily call on schedule.
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
        if options["all"]:
            self.stdout.write("Enriching all active movies...")
        else:
            self.stdout.write("Enriching movies without actor enrichment...")

        result = EnrichActorsCommand(enrich_all=options["all"], limit=options["limit"]).execute()

        if result.total == 0:
            self.stdout.write(self.style.SUCCESS("No movies to enrich!"))  # type: ignore[attr-defined]
            return

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Enrichment complete!"))  # type: ignore[attr-defined]
        self.stdout.write(f"  Total processed: {result.total}")
        self.stdout.write(f"  Successfully enriched: {result.enriched}")
        self.stdout.write(f"  Not found on TMDB: {result.not_found}")
        self.stdout.write(f"  Failed: {result.failed}")
