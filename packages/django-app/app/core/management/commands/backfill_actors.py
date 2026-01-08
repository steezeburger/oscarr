import logging

from django.core.management import BaseCommand

from plex.commands import BackfillActorsCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command to backfill TMDB actors for existing PlexMovie records.
    Usage: python manage.py backfill_actors
    """
    help = 'Backfill TMDB actors for all existing PlexMovie records'

    def handle(self, *args, **options):
        self.stdout.write('Starting actor backfill from TMDB...')
        BackfillActorsCommand().execute()
        self.stdout.write(self.style.SUCCESS('Actor backfill complete!'))
