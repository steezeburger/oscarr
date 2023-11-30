from typing import Optional

import discord
from aiohttp import ClientSession
from discord import app_commands

from discordbot.bacon import bacon
from discordbot.get_random import get_random
from discordbot.request_movie import request_movie, search_tmdb
from discordbot.search import search
from discordbot.stats import genre_pie
from movie_requests.commands import RequestMovieForm, RequestOmbiMovieCommand


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

    async def on_interaction(self, interaction: discord.Interaction):
        try:
            print(f"interaction: {interaction.data}")
            print(f"interaction type: {interaction.type}")
            if interaction.type == discord.InteractionType.component:
                custom_id = interaction.data['custom_id']
                if custom_id.startswith("tmdb_"):
                    tmdb_id = custom_id.split("_")[1]
                    form = RequestMovieForm({
                        'tmdb_id': tmdb_id,
                        'discord_username': interaction.user.name,
                    })
                    ok, message = await RequestOmbiMovieCommand(form).execute()
                    if not ok:
                        print(f"failed to request movie: {message}")
                        await interaction.response.send_message(message)
                        return
                    else:
                        await interaction.response.send_message(message)
        except Exception as e:
            print(f"error: {e}")

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
