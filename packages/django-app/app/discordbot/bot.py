import logging

import discord
from aiohttp import ClientSession
from discord import app_commands
from discord.ext import tasks
from discordbot.actor_graph import ActorGraphCache
from discordbot.bacon import bacon
from discordbot.get_random import get_random
from discordbot.request_movie import request_movie, search_tmdb
from discordbot.search import search
from discordbot.stats import genre_pie
from movie_requests.commands import RequestMovieForm, RequestOmbiMovieCommand

logger = logging.getLogger(__name__)


class OscarrBot(discord.Client):
    web_client: ClientSession
    actor_graphs: ActorGraphCache

    def __init__(
        self,
        *args,
        web_client: ClientSession,
        intents: discord.Intents | None = None,
    ):
        """Client initialization."""
        if intents is None:
            intents = discord.Intents.default()
        intents.members = True

        super().__init__(intents=intents)
        self.web_client = web_client
        self.tree = app_commands.CommandTree(self)
        self.tree.on_error = self.on_app_command_error
        self.actor_graphs = ActorGraphCache()

    async def on_ready(self):
        await self.wait_until_ready()
        print(f"Logged on as {self.user}!")

    async def on_interaction(self, interaction: discord.Interaction):
        try:
            print(f"interaction: {interaction.data}")
            print(f"interaction type: {interaction.type}")
            # FIXME - put this logic in its own function
            if interaction.type == discord.InteractionType.component:
                if not interaction.data:
                    return
                custom_id = interaction.data.get("custom_id")
                if not custom_id:
                    return
                if custom_id.startswith("tmdb_"):
                    await interaction.response.send_message("Working on it...")
                    tmdb_id = custom_id.split("_")[1]
                    form = RequestMovieForm(
                        {
                            "tmdb_id": tmdb_id,
                            "discord_username": interaction.user.name,
                        }
                    )
                    ok, message = await RequestOmbiMovieCommand(form, self.web_client).execute()
                    if not ok:
                        print(f"failed to request movie: {message}")
                        await interaction.edit_original_response(content=message)
                        return
                    else:
                        await interaction.edit_original_response(content=message)
        except Exception as e:
            print(f"error: {e}")

    async def on_guild_join(self, guild: discord.Guild):
        """On guild join."""
        pass

    async def on_guild_remove(self, guild: discord.Guild):
        """On guild remove."""
        pass

    async def on_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        command_name = interaction.command.name if interaction.command else None
        logger.error("error in /%s", command_name, exc_info=error)
        message = "Something went wrong, check the bot logs."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message)
            else:
                await interaction.response.send_message(message)
        except discord.HTTPException:
            logger.exception("failed to report error for /%s", command_name)

    @tasks.loop(seconds=60)
    async def refresh_actor_graph(self):
        try:
            await self.actor_graphs.refresh()
        except Exception:
            logger.exception("failed to refresh actor graph")

    async def setup_hook(self) -> None:
        print("setup hook")
        self.refresh_actor_graph.start()
        self.tree.add_command(bacon)
        self.tree.add_command(genre_pie)
        self.tree.add_command(get_random)
        self.tree.add_command(request_movie)
        self.tree.add_command(search_tmdb)
        self.tree.add_command(search)
        await self.tree.sync()
