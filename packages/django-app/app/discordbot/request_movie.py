import logging

import discord
from discord import app_commands

from movie_requests.commands import RequestMovieCommand, RequestMovieForm

logger = logging.getLogger(__name__)


@app_commands.command(name="request", description="Request a movie from the plex with a TMDB link.")
async def request_movie(interaction: discord.Interaction, tmdb_id: str):
    print("requesting movie via discord bot")

    form = RequestMovieForm({'tmdb_id': tmdb_id})
    ok, message = await RequestMovieCommand(form).execute()

    if not ok:
        print(f"failed to request movie: {message}")
        await interaction.response.send_message(message)
        return
    else:
        await interaction.response.send_message(message)
