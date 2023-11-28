import os

import discord
from asgiref.sync import sync_to_async
from discord import app_commands, File
from django.db.models import Count, Func, F
from matplotlib import pyplot

from plex.models import PlexMovie


@app_commands.command(name="genre_pie", description="Generate a pie chart of the movie genres.")
async def genre_pie(interaction: discord.Interaction):
    """
    Generate a pie chart of the movie genres
    """

    # TODO - cache this and only recreate if a movie has been added since cached image

    try:
        q = PlexMovie.objects.annotate(
            genre=Func(F('genres'), function='unnest')
        ).values('genre').order_by('genre').annotate(
            count=Count('title')
        ).values_list('genre', 'count')

        genre_counts = await sync_to_async(list)(q)

        # Prepare data for pie chart
        labels = [f"{g[0]} ({g[1]})" for g in genre_counts]
        sizes = [g[1] for g in genre_counts]

        # Create and save the pie chart
        pyplot.clf()
        fig, ax = pyplot.subplots()
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', shadow=True, startangle=90)
        ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        fig.savefig('genre_pie_chart.png')

        # Send the pie chart image
        await interaction.response.send_message(file=File('genre_pie_chart.png'))

        # Remove the image file
        os.remove('genre_pie_chart.png')
    except Exception as e:
        print(e)
        await interaction.response.send_message(f"Error: {e}")
