import asyncio
import logging
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import networkx as nx
from asgiref.sync import sync_to_async
from django.db import close_old_connections
from django.db.models import Count, Max
from plex.models import PlexMovie

logger = logging.getLogger(__name__)

ACTORS = "actors"
DIRECTORS = "directors"
PRODUCERS = "producers"
WRITERS = "writers"
ROLES = (ACTORS, DIRECTORS, PRODUCERS, WRITERS)

MOVIE_FIELDS = ("title", "year", *ROLES)

# (max modified_at, row count). count catches hard deletes, which don't bump modified_at
GraphSignature = tuple[datetime | None, int]


def movie_node_name(title: str, year: int | None) -> str:
    return f"{title} ({year})" if year and year > 0 else title


@dataclass(frozen=True)
class ActorGraph:
    """
    One graph of movies and people. Every movie-person edge carries the set of roles the
    person had on that movie, so a lookup can filter down to the roles it cares about.
    People are keyed by lowercased name.
    """

    graph: nx.Graph
    people_by_role: Mapping[str, frozenset[str]]

    def view(self, roles: Collection[str]) -> nx.Graph:
        allowed = frozenset(roles)
        people = frozenset().union(*(self.people_by_role[role] for role in allowed))

        def keep_node(node: str) -> bool:
            return self.graph.nodes[node]["type"] == "movie" or node in people

        def keep_edge(u: str, v: str) -> bool:
            return not allowed.isdisjoint(self.graph.edges[u, v]["roles"])

        return nx.subgraph_view(self.graph, filter_node=keep_node, filter_edge=keep_edge)

    def shortest_path(self, source: str, target: str, roles: Collection[str]) -> list[str]:
        """
        Raises nx.NodeNotFound or nx.NetworkXNoPath like nx.shortest_path does.
        """
        path = nx.shortest_path(
            self.view(roles), source=source.strip().lower(), target=target.strip().lower()
        )
        assert isinstance(path, list)
        return path


def build_actor_graph(movies: Iterable[Mapping[str, Any]]) -> ActorGraph:
    graph = nx.Graph()
    people_by_role: dict[str, set[str]] = {role: set() for role in ROLES}
    added_people: set[str] = set()

    for movie in movies:
        movie_title = movie_node_name(movie["title"], movie["year"])
        graph.add_node(movie_title, type="movie")

        for role in ROLES:
            for name in movie[role] or ():
                person = name.strip().lower()
                if not person:
                    continue
                if person not in added_people:
                    graph.add_node(person, type="person")
                    added_people.add(person)
                people_by_role[role].add(person)

                if graph.has_edge(movie_title, person):
                    graph.edges[movie_title, person]["roles"].add(role)
                else:
                    graph.add_edge(movie_title, person, roles={role})

    return ActorGraph(
        graph=graph,
        people_by_role={role: frozenset(people) for role, people in people_by_role.items()},
    )


def get_graph_signature() -> GraphSignature:
    close_old_connections()
    result = PlexMovie.objects.aggregate(Max("modified_at"), Count("id"))
    return result["modified_at__max"], result["id__count"]


def load_movies() -> list[dict[str, Any]]:
    return list(PlexMovie.objects.values(*MOVIE_FIELDS))


class ActorGraphCache:
    """
    Holds the current ActorGraph and rebuilds it when the movies table changes. The
    graph reference is only swapped after a full build, so readers always see a
    complete graph.
    """

    def __init__(self):
        self.graph: ActorGraph | None = None
        self.signature: GraphSignature | None = None

    async def refresh(self) -> bool:
        """
        Rebuilds the graph if the movies changed since the last build. Returns whether
        it rebuilt.
        """
        signature = await sync_to_async(get_graph_signature)()
        if self.graph is not None and signature == self.signature:
            return False

        movies = await sync_to_async(load_movies)()
        graph = await asyncio.to_thread(build_actor_graph, movies)

        self.graph = graph
        self.signature = signature
        logger.info(
            "built actor graph: %s nodes, %s edges",
            graph.graph.number_of_nodes(),
            graph.graph.number_of_edges(),
        )
        return True
