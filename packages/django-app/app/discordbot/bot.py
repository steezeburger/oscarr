from typing import Optional

import discord
from aiohttp import ClientSession
from discord import app_commands

from discordbot.bacon import bacon
from discordbot.get_random import get_random
from discordbot.request_movie import request_movie, search_tmdb
from discordbot.search import search
from discordbot.stats import genre_pie


class OscarrBot(discord.Client):
    def __init__(
            self,
            *args,
            web_client: ClientSession,
            intents: Optional[discord.Intents] = None,
    ):
        """Client initialization."""
        if intents is None:
            intents = discord.Intents.default()
        intents.members = True

        super().__init__(intents=intents)
        self.web_client = web_client
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        await self.wait_until_ready()
        print(f'Logged on as {self.user}!')

    async def on_guild_join(self, guild: discord.Guild):
        """On guild join."""
        pass

    async def on_guild_remove(self, guild: discord.Guild):
        """On guild remove."""
        pass

    async def setup_hook(self) -> None:
        print('setup hook')
        self.tree.add_command(bacon)
        self.tree.add_command(genre_pie)
        self.tree.add_command(get_random)
        self.tree.add_command(request_movie)
        self.tree.add_command(search_tmdb)
        self.tree.add_command(search)
        await self.tree.sync()
