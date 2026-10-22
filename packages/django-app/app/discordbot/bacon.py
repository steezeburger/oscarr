import asyncio
from typing import TYPE_CHECKING

import discord
import networkx as nx
from discord import app_commands
from discordbot.actor_graph import ACTORS, DIRECTORS, PRODUCERS, WRITERS

if TYPE_CHECKING:
    from discordbot.bot import OscarrBot


def format_path(from_actor: str, to_actor: str, path: list[str]) -> str:
    words_list = []
    hops = 0

    for idx, entry in enumerate(path):
        if idx == 0:
            # from actor
            words_list.append(entry.title())
            words_list.append("worked on")
        elif idx % 2 != 0:
            # a movie
            hops += 1
            words_list.append(entry)
            words_list.append("with")
        elif idx % 2 == 0 and idx != len(path) - 1:
            # an actor
            words_list.append(entry.title())
            words_list.append("who worked on")
        elif idx == len(path) - 1:
            # last actor
            words_list.append(f"{entry.title()}.")

    return f"{from_actor} and {to_actor} are connected by {hops} hops.\n" + " ".join(words_list)


@app_commands.command(name="bacon", description="Shows hops between actors.")
@app_commands.rename(from_actor="from", to_actor="to")
async def bacon(
    interaction: discord.Interaction["OscarrBot"],
    from_actor: str,
    to_actor: str,
    with_directors: bool = False,
    with_producers: bool = False,
    with_writers: bool = False,
):
    await interaction.response.defer()

    actor_graph = interaction.client.actor_graphs.graph
    if actor_graph is None:
        await interaction.followup.send(
            "Still building the actor graph, try again in a minute or two."
        )
        return

    from_actor = from_actor.strip().lower()
    to_actor = to_actor.strip().lower()

    roles = {ACTORS}
    if with_directors:
        roles.add(DIRECTORS)
    if with_producers:
        roles.add(PRODUCERS)
    if with_writers:
        roles.add(WRITERS)

    try:
        path = await asyncio.to_thread(actor_graph.shortest_path, from_actor, to_actor, roles)
    except (nx.NetworkXNoPath, nx.NodeNotFound) as exception:
        await interaction.followup.send(str(exception))
        return

    await interaction.followup.send(format_path(from_actor, to_actor, path))
