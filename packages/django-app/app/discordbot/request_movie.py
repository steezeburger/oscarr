import logging
from typing import List

import discord
from discord import app_commands

from movie_requests.commands import RequestMovieForm, RequestOmbiMovieCommand
from services.tmdb import TMDB

logger = logging.getLogger(__name__)


@app_commands.command(name="request", description="Request a movie from the plex with a TMDB link.")
async def request_movie(interaction: discord.Interaction, tmdb_id: str):
    print("requesting movie via discord bot")

    username = interaction.user.name
    print(f"username: {username}")

    form = RequestMovieForm({
        'tmdb_id': tmdb_id,
        'discord_username': username,
    })
    ok, message = await RequestOmbiMovieCommand(form).execute()

    if not ok:
        print(f"failed to request movie: {message}")
        await interaction.response.send_message(message)
        return
    else:
        await interaction.response.send_message(message)


def format_for_discord(data) -> str:
    message = "🎬 **Movie/Show List** 🎬\n\n"

    for item in data['results'][0:3]:
        title = item.get('title', 'No Title')
        release_date = item.get('release_date', 'Unknown Release Date')

        message += f"**Title**: {title}\n"
        message += f"**ID**: {item['id']}\n"
        message += f"**Release Date**: {release_date}\n"
        message += "\n"
        # only include image for first result
        if item == data['results'][0]:
            message += TMDB.get_poster_full_path(item.get('poster_path'))
            message += "\n"

    # message += f"Page {data['page']} of {data['total_pages']}\n"
    # message += f"Total Results: {data['total_results']}\n"

    return message


def create_discord_embed(item):
    embed = discord.Embed(title="🎬 Top 3 Movies/Shows 🎬", color=0x1a1a1a)  # You can change the color
    title = item.get('title', 'No Title')
    release_date = item.get('release_date', 'Unknown Release Date')
    tmdb_id = item.get('id', 'Unknown ID')
    overview = item.get('overview', 'No Overview')

    embed.add_field(
        name=title,
        value=f"**Release Date**: {release_date}\n **ID**: {tmdb_id}\n **Overview**: {overview}\n",
        inline=False)

    first_poster_path = item.get('poster_path', None)
    if first_poster_path:
        first_poster_url = f"https://image.tmdb.org/t/p/original{first_poster_path}"
        embed.set_image(url=first_poster_url)

    return embed


def create_buttons(data) -> List[discord.ui.Button]:
    buttons = []
    for item in data['results'][:3]:
        tmdb_id = item.get('id', None)
        if tmdb_id:
            button = discord.ui.Button(
                label=f"Request {item['title']}",
                style=discord.ButtonStyle.primary,
                custom_id=f"tmdb_{tmdb_id}")
            buttons.append(button)
    return buttons


@app_commands.command(name="search_tmdb", description="Search TMDB for a movie.")
async def search_tmdb(interaction: discord.Interaction, title: str):
    print("searching tmdb via discord bot")
    results = TMDB.search_by_title(title)

    embeds = [create_discord_embed(item) for item in results['results'][:3]]
    buttons = create_buttons(results)

    view = discord.ui.View()
    for button in buttons:
        view.add_item(button)

    try:
        await interaction.response.send_message(
            embeds=embeds,
            view=view)
    except Exception as e:
        print(e)

    return
