from unittest import mock

import networkx as nx
from asgiref.sync import async_to_sync
from discordbot.actor_graph import (
    ACTORS,
    DIRECTORS,
    PRODUCERS,
    WRITERS,
    ActorGraphCache,
    build_actor_graph,
)
from discordbot.bacon import format_path
from django.test import SimpleTestCase, TestCase
from plex.test_helpers import PlexMovieFactory


def movie(
    title, year: int | None = 2000, actors=None, directors=None, producers=None, writers=None
):
    return {
        "title": title,
        "year": year,
        "actors": actors,
        "directors": directors,
        "producers": producers,
        "writers": writers,
    }


class TestBuildActorGraph(SimpleTestCase):
    def test_should_find_path_through_shared_movies(self):
        graph = build_actor_graph(
            [
                movie("Apollo 13", 1995, actors=["Tom Hanks", "Kevin Bacon"]),
                movie("Big", 1988, actors=["Tom Hanks", "Elizabeth Perkins"]),
            ]
        )

        path = graph.shortest_path("Elizabeth Perkins", "Kevin Bacon", {ACTORS})

        self.assertEqual(
            ["elizabeth perkins", "Big (1988)", "tom hanks", "Apollo 13 (1995)", "kevin bacon"],
            path,
        )

    def test_should_match_names_case_insensitively(self):
        graph = build_actor_graph([movie("Footloose", actors=["Kevin BACON", "Lori Singer"])])

        path = graph.shortest_path("  kEvIn bacon ", "LORI SINGER", {ACTORS})

        self.assertEqual(["kevin bacon", "Footloose (2000)", "lori singer"], path)

    def test_should_leave_year_off_when_missing(self):
        graph = build_actor_graph([movie("Untitled", year=None, actors=["a", "b"])])

        self.assertEqual(["a", "Untitled", "b"], graph.shortest_path("a", "b", {ACTORS}))

    def test_should_only_use_crew_edges_when_flag_is_on(self):
        for role in (DIRECTORS, PRODUCERS, WRITERS):
            with self.subTest(role=role):
                graph = build_actor_graph(
                    [
                        {**movie("One", actors=["Actor A"]), role: ["Crew Person"]},
                        {**movie("Two", actors=["Actor B"]), role: ["Crew Person"]},
                    ]
                )

                with self.assertRaises(nx.NodeNotFound):
                    graph.shortest_path("actor a", "crew person", {ACTORS})
                with self.assertRaises(nx.NetworkXNoPath):
                    graph.shortest_path("actor a", "actor b", {ACTORS})

                self.assertEqual(
                    ["actor a", "One (2000)", "crew person", "Two (2000)", "actor b"],
                    graph.shortest_path("actor a", "actor b", {ACTORS, role}),
                )

    def test_should_ignore_crew_credits_of_actors_when_flag_is_off(self):
        graph = build_actor_graph(
            [
                movie("Acted", actors=["Clint Eastwood", "Gene Hackman"]),
                movie("Directed", actors=["Morgan Freeman"], directors=["Clint Eastwood"]),
            ]
        )

        with self.assertRaises(nx.NetworkXNoPath):
            graph.shortest_path("gene hackman", "morgan freeman", {ACTORS})

        self.assertEqual(
            5, len(graph.shortest_path("gene hackman", "morgan freeman", {ACTORS, DIRECTORS}))
        )

    def test_should_keep_both_roles_on_one_edge(self):
        graph = build_actor_graph(
            [movie("Unforgiven", actors=["Clint Eastwood"], directors=["Clint Eastwood"])]
        )

        self.assertEqual(
            {ACTORS, DIRECTORS}, graph.graph.edges["Unforgiven (2000)", "clint eastwood"]["roles"]
        )

    def test_should_skip_null_and_blank_names(self):
        graph = build_actor_graph([movie("Empty", actors=["", "  "], directors=None)])

        self.assertEqual(["Empty (2000)"], list(graph.graph.nodes))


class TestFormatPath(SimpleTestCase):
    def test_should_describe_hops(self):
        message = format_path(
            "a",
            "c",
            ["a", "Movie One (2000)", "b", "Movie Two (2001)", "c"],
        )

        self.assertEqual(
            "a and c are connected by 2 hops.\n"
            "A worked on Movie One (2000) with B who worked on Movie Two (2001) with C.",
            message,
        )


class TestActorGraphCache(TestCase):
    def setUp(self):
        # closing the connection would drop the test transaction
        patcher = mock.patch("discordbot.actor_graph.close_old_connections")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_should_build_on_first_refresh(self):
        PlexMovieFactory(title="Footloose", year=1984, actors=["Kevin Bacon", "Lori Singer"])
        cache = ActorGraphCache()

        self.assertTrue(async_to_sync(cache.refresh)())

        assert cache.graph is not None
        self.assertEqual(
            ["kevin bacon", "Footloose (1984)", "lori singer"],
            cache.graph.shortest_path("kevin bacon", "lori singer", {ACTORS}),
        )

    def test_should_not_rebuild_when_nothing_changed(self):
        PlexMovieFactory(actors=["a"])
        cache = ActorGraphCache()
        async_to_sync(cache.refresh)()
        graph = cache.graph

        self.assertFalse(async_to_sync(cache.refresh)())
        self.assertIs(graph, cache.graph)

    def test_should_rebuild_when_a_movie_is_modified(self):
        plex_movie = PlexMovieFactory(year=2000, actors=["a"])
        cache = ActorGraphCache()
        async_to_sync(cache.refresh)()

        plex_movie.actors = ["a", "b"]
        plex_movie.save()

        self.assertTrue(async_to_sync(cache.refresh)())
        assert cache.graph is not None
        self.assertEqual(3, len(cache.graph.shortest_path("a", "b", {ACTORS})))

    def test_should_rebuild_when_a_movie_is_added(self):
        PlexMovieFactory(actors=["a"])
        cache = ActorGraphCache()
        async_to_sync(cache.refresh)()

        PlexMovieFactory(actors=["b"])

        self.assertTrue(async_to_sync(cache.refresh)())

    def test_should_rebuild_when_a_movie_is_hard_deleted(self):
        PlexMovieFactory(actors=["a"])
        older = PlexMovieFactory(actors=["b"])
        PlexMovieFactory(actors=["c"])
        cache = ActorGraphCache()
        async_to_sync(cache.refresh)()

        older.delete(force_delete=True)

        self.assertTrue(async_to_sync(cache.refresh)())
        assert cache.graph is not None
        self.assertNotIn("b", cache.graph.graph)
