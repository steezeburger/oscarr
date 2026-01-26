import discord
import networkx as nx
from discord import app_commands
from plex.commands import GetActorGraphCommand


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

    # Get actor graph (from cache or build if needed)
    command = GetActorGraphCommand()
    graph = await command.execute()

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
