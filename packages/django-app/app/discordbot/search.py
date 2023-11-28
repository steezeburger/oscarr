import discord
from asgiref.sync import sync_to_async
from discord import app_commands

from plex.repositories import PlexMovieRepository


@app_commands.command(name="search", description="Search for movies by title, actor, etc.")
async def search(
        interaction: discord.Interaction,
        all: str = None,
        title: str = None,
        actor: str = None,
        director: str = None,
        producer: str = None,
        writer: str = None,
):
    if all:
        movies = await sync_to_async(list)(
            PlexMovieRepository.search_all(all))
    else:
        movies = await sync_to_async(list)(
            PlexMovieRepository.search(
                title=title,
                actor=actor,
                director=director,
                producer=producer,
                writer=writer, ))

    messages = [f"{movie['title']} ({movie['year']}) \n" for movie in movies]
    message = "".join(messages)

    if len(movies) > 0:
        prepend = f"Found {len(movies)} movies.\n"
        message = prepend + message
        await interaction.response.send_message(f"```{message}```")
    else:
        await interaction.response.send_message(f"No movies found.")
