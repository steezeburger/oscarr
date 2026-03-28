import asyncio

import aiohttp
from aiohttp import ClientSession
from discord.ext import commands
from discordbot.bot import OscarrBot
from django.conf import settings
from django.core.management import BaseCommand


async def run():
    connector = aiohttp.TCPConnector(force_close=True)
    async with ClientSession(connector=connector) as web_client:
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
