import discord
from asgiref.sync import sync_to_async
from discord import app_commands

from plex.repositories import PlexMovieRepository


@app_commands.command(name="get_random", description="Get a random movie.")
async def get_random(interaction: discord.Interaction):
    plex_movie = await sync_to_async(PlexMovieRepository.get_random)()

    await interaction.response.send_message(f"{plex_movie.title} ({plex_movie.year})")
