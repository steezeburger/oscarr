from datetime import datetime, timedelta
from io import StringIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from core.test_helpers import UserFactory
from django.core.management import call_command
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from services.plex import Plex
from services.tmdb import TMDB

from plex.commands import SyncWithPlexCommand
from plex.repositories import PlexMovieRepository
from plex.test_helpers import PlexMovieFactory


class TestPlexMovieRepository(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_should_create_plex_movie(self):
        movie_details = {
            "plex_guid": "abcd1234",
            "title": "a title",
            "year": 1984,
            "duration": 124123123,
        }

        plex_movie = PlexMovieRepository.get_or_create(data=movie_details)

        self.assertEqual(movie_details["plex_guid"], plex_movie.plex_guid)
        self.assertEqual(movie_details["title"], plex_movie.title)
        self.assertEqual(movie_details["year"], plex_movie.year)
        self.assertEqual(movie_details["duration"], plex_movie.duration)

    def test_should_get_existing_plex_movie(self):
        plex_movie = PlexMovieFactory()

        movie_details = {
            "plex_guid": plex_movie.plex_guid,
        }
        obj_from_db = PlexMovieRepository.get_or_create(data=movie_details)

        self.assertEqual(plex_movie.pk, obj_from_db.pk)

    def test_should_get_plex_movie_by_title_iexact(self):
        plex_movie = PlexMovieFactory(title="BANANA")

        obj_from_db = PlexMovieRepository.get_by_title(plex_movie.title.lower())

        self.assertEqual(plex_movie.title, obj_from_db.title)


class TestPlexCommands(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_sync_should_save_movies_without_calling_tmdb(self):
        plex_movie = SimpleNamespace(
            guid="plex://movie/1",
            title="Heat",
            year=1995,
            duration=10_200_000,
            addedAt=datetime(2026, 10, 21, 12, 0),
            actors=[SimpleNamespace(tag="Al Pacino")],
            genres=[],
            directors=[],
            producers=[],
            writers=[],
        )

        with (
            patch.object(Plex, "fetch_movies", return_value=[plex_movie]),
            patch.object(TMDB, "find_movie_id", new_callable=AsyncMock) as find_movie_id,
            patch.object(TMDB, "get_movie_credits", new_callable=AsyncMock) as get_movie_credits,
        ):
            SyncWithPlexCommand().execute()

        movie = PlexMovieRepository.get_by_title("Heat")
        self.assertIsNotNone(movie)
        self.assertEqual(["Al Pacino"], movie.actors)
        self.assertIsNone(movie.actors_enriched_at)
        self.assertIsNone(movie.enrichment_attempted_at)
        find_movie_id.assert_not_called()
        get_movie_credits.assert_not_called()


class TestGetMoviesToEnrich(TestCase):
    def test_should_include_unenriched_movies(self):
        movie = PlexMovieFactory()

        self.assertEqual([movie], list(PlexMovieRepository.get_movies_to_enrich()))

    def test_should_skip_enriched_movies(self):
        PlexMovieFactory(actors_enriched_at=timezone.now())

        self.assertEqual([], list(PlexMovieRepository.get_movies_to_enrich()))

    def test_should_skip_movies_attempted_in_the_last_day(self):
        PlexMovieFactory(enrichment_attempted_at=timezone.now() - timedelta(hours=1))

        self.assertEqual([], list(PlexMovieRepository.get_movies_to_enrich()))

    def test_should_retry_movies_attempted_over_a_day_ago(self):
        movie = PlexMovieFactory(enrichment_attempted_at=timezone.now() - timedelta(hours=25))

        self.assertEqual([movie], list(PlexMovieRepository.get_movies_to_enrich()))

    def test_should_skip_inactive_movies(self):
        PlexMovieFactory(is_active=False)

        self.assertEqual([], list(PlexMovieRepository.get_movies_to_enrich()))

    def test_should_respect_limit(self):
        PlexMovieFactory.create_batch(3)

        self.assertEqual(2, len(PlexMovieRepository.get_movies_to_enrich(limit=2)))


class TestEnrichActorsCommand(TransactionTestCase):
    """
    TransactionTestCase because the async ORM calls run on another thread,
    which can't see data inside a TestCase transaction.
    """

    def setUp(self):
        now = timezone.now()
        self.unenriched = PlexMovieFactory(title="Unenriched", actors=["Plex Actor"])
        self.enriched = PlexMovieFactory(title="Enriched", actors_enriched_at=now)
        self.recently_attempted = PlexMovieFactory(
            title="Recently Attempted", enrichment_attempted_at=now - timedelta(hours=1)
        )

    def _run(self, *args, find_movie_id: int | None = 123):
        with (
            patch.object(
                TMDB, "find_movie_id", new_callable=AsyncMock, return_value=find_movie_id
            ) as mock_find,
            patch.object(
                TMDB,
                "get_movie_credits",
                new_callable=AsyncMock,
                return_value={"cast": [{"name": "TMDB Actor"}]},
            ),
        ):
            out = StringIO()
            call_command("enrich_actors", *args, stdout=out)
        searched = {call.args[0] for call in mock_find.await_args_list}
        return searched, out.getvalue()

    def test_default_should_only_enrich_unenriched_movies_not_recently_attempted(self):
        searched, out = self._run()

        self.assertEqual({"Unenriched"}, searched)
        self.unenriched.refresh_from_db()
        self.assertEqual(["Plex Actor", "TMDB Actor"], self.unenriched.actors)
        self.assertEqual(123, self.unenriched.tmdb_id)
        self.assertIsNotNone(self.unenriched.actors_enriched_at)
        self.assertIsNotNone(self.unenriched.enrichment_attempted_at)
        self.assertIn("Successfully enriched: 1", out)

    def test_all_should_enrich_every_active_movie(self):
        searched, _ = self._run("--all")

        self.assertEqual({"Unenriched", "Enriched", "Recently Attempted"}, searched)

    def test_not_found_should_record_attempt_and_skip_next_run(self):
        searched, out = self._run(find_movie_id=None)

        self.assertEqual({"Unenriched"}, searched)
        self.assertIn("Not found on TMDB: 1", out)
        self.unenriched.refresh_from_db()
        self.assertIsNone(self.unenriched.actors_enriched_at)
        self.assertIsNotNone(self.unenriched.enrichment_attempted_at)

        searched, out = self._run(find_movie_id=None)

        self.assertEqual(set(), searched)
        self.assertIn("No movies to enrich!", out)
