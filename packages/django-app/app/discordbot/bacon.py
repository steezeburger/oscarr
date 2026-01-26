import discord
import networkx as nx
from asgiref.sync import sync_to_async
from discord import app_commands
from plex.models import PlexMovie
from plex.repositories import CachedGraphRepository


async def build_actor_graph():
    """
    Build a NetworkX graph of all movies and their associated people.
    Includes actors, directors, producers, and writers.

    Returns:
        nx.Graph: Complete graph of all movie-person relationships
    """
    movies = await sync_to_async(list)(PlexMovie.objects.all().values())

    graph = nx.Graph()
    added_people = set()

    for movie_dict in movies:
        # Add movie node
        year = movie_dict.get("year")
        year = int(year) if year and year > 0 else None
        year_string = f" ({year})" if year else ""
        movie_title = f"{movie_dict['title']}{year_string}"
        graph.add_node(movie_title, type="movie")

        # Add all people (actors, directors, producers, writers)
        for person_type in ["actors", "directors", "producers", "writers"]:
            people = movie_dict.get(person_type) or []
            for person in people:
                person_lower = person.lower()
                if person_lower not in added_people:
                    graph.add_node(person_lower, type="person")
                    added_people.add(person_lower)
                graph.add_edge(movie_title, person_lower)

    return graph


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
    """Find the shortest path between two people through movies."""
    # Normalize input
    from_actor = from_actor.strip().lower()
    to_actor = to_actor.strip().lower()

    # Defer response since this might take a moment
    await interaction.response.defer()

    # Try to load cached graph
    graph = await CachedGraphRepository.load_actor_graph_async()

    if graph is None:
        # Build graph if not cached
        graph = await build_actor_graph()
        # Cache it for next time
        await sync_to_async(CachedGraphRepository.save_actor_graph)(graph)

    try:
        path = nx.shortest_path(graph, source=from_actor, target=to_actor)

        # Build message
        words_list = []
        hops = 0

        for idx, entry in enumerate(path):
            if idx == 0:
                # from person
                words_list.append(entry.title())
                words_list.append("worked on")
            elif idx % 2 != 0:
                # a movie
                hops += 1
                words_list.append(entry)
                words_list.append("with")
            elif idx % 2 == 0 and idx != len(path) - 1:
                # an intermediary person
                words_list.append(entry.title())
                words_list.append("who worked on")
            elif idx == len(path) - 1:
                # target person
                words_list.append(f"{entry.title()}.")

        message = f"{from_actor} and {to_actor} are connected by {hops} hops.\n" + " ".join(
            words_list
        )
        await interaction.followup.send(message)
    except nx.NetworkXNoPath:
        await interaction.followup.send(f"No path found between {from_actor} and {to_actor}.")
    except nx.NodeNotFound as e:
        await interaction.followup.send(f"Person not found: {str(e)}")
