import discord
import networkx as nx
import pandas as pd
from asgiref.sync import sync_to_async
from discord import app_commands

from plex.models import PlexMovie


@app_commands.command(name="bacon", description="Shows hops between actors.")
@app_commands.rename(from_actor="from", to_actor="to")
async def bacon(
        interaction: discord.Interaction,
        from_actor: str,
        to_actor: str,
        with_directors: bool = False,
        with_producers: bool = False,
        with_writers: bool = False,
):
    # munge input
    from_actor = from_actor.strip().lower()
    to_actor = to_actor.strip().lower()

    movies = await sync_to_async(list)(PlexMovie.objects.all().values())
    df = pd.DataFrame(movies)

    graph = nx.Graph()
    added_actors = []
    added_directors = []
    added_producers = []
    added_writers = []

    def add_movie_and_actors_to_graph(movie):
        year = int(movie.year) if movie.year > 0 else None
        year_string = f" ({year})" if year else None
        movie_title = f"{movie.title}{year_string}"
        graph.add_node(movie_title,
                       type='movie',
                       color='red')

        for actor in movie.actors:
            if actor not in added_actors:
                actor = actor.lower()
                graph.add_node(actor,
                               type='actor',
                               color='blue' if actor == from_actor else 'green')
                added_actors.append(actor)
            graph.add_edge(movie_title, actor)

        if with_directors:
            for director in movie.directors:
                if director not in added_directors:
                    director = director.lower()
                    graph.add_node(director,
                                   type='directors',
                                   color='yellow' if director == from_actor else 'green')
                    added_directors.append(director)
                graph.add_edge(movie_title, director)

        if with_producers:
            for producer in movie.producers:
                if producer not in added_producers:
                    producer = producer.lower()
                    graph.add_node(producer,
                                   type='producers',
                                   color='purple' if producer == from_actor else 'green')
                    added_producers.append(producer)
                graph.add_edge(movie_title, producer)

        if with_writers:
            for writer in movie.writers:
                if writer not in added_writers:
                    writer = writer.lower()
                    graph.add_node(writer,
                                   type='writers',
                                   color='red' if writer == from_actor else 'green')
                    added_writers.append(writer)
                graph.add_edge(movie_title, writer)

    _ = df.apply(lambda m: add_movie_and_actors_to_graph(m), axis=1)

    try:
        path = nx.shortest_path(graph,
                                source=from_actor,
                                target=to_actor)

        # build message
        words_list = []
        hops = 0

        for idx, entry in enumerate(path):
            if idx == 0:
                # from actor
                words_list.append(entry.title())
                words_list.append('worked on')
            elif idx % 2 != 0:
                # a movie
                hops += 1
                words_list.append(entry)
                words_list.append('with')
            elif idx % 2 == 0 and idx != len(path) - 1:
                # an actor
                words_list.append(entry.title())
                words_list.append('who worked on')
            elif idx == len(path) - 1:
                # last actor
                words_list.append(f'{entry.title()}.')

        message = f'{from_actor} and {to_actor} are connected by {hops} hops.\n' + \
                  ' '.join(words_list)
        await interaction.response.send_message(message)
    except nx.NetworkXNoPath as exception:
        await interaction.response.send_message(exception)
    except nx.NodeNotFound as exception:
        await interaction.response.send_message(exception)

    await interaction.response.send_message('gonna queue up something good!')
