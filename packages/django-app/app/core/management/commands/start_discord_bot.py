from django.conf import settings
from django.core.management import BaseCommand

from discordbot.bot import bot


class Command(BaseCommand):
    """
    Start the Discord bot server.
    """

    def handle(self, *args, **options):
        bot.run(settings.DISCORD_TOKEN)
