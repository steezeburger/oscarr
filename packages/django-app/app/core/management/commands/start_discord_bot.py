import asyncio

from aiohttp import ClientSession
from discord.ext import commands
from django.conf import settings
from django.core.management import BaseCommand

from discordbot.bot import OscarrBot


async def run():
    async with ClientSession() as web_client:
        async with OscarrBot(
                commands.when_mentioned,
                web_client=web_client,
        ) as client:
            await client.start(settings.DISCORD_TOKEN)


class Command(BaseCommand):
    """
    Start the Discord bot server.
    """

    def handle(self, *args, **options):
        asyncio.run(run())
