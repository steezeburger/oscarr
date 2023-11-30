import logging

from django.core.management import BaseCommand

from plex.commands import SyncWithPlexCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Management command wrapper for SyncWithPlexCommand so we can easily call on schedule.
    """

    def handle(self, *args, **options):
        SyncWithPlexCommand().execute()
