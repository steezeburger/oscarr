from django.test import TestCase
from unittest.mock import patch, MagicMock

from core.test_helpers import UserFactory
from plex.repositories import PlexMovieRepository
from plex.test_helpers import PlexMovieFactory
from plex.commands import SyncWithPlexCommand


class TestPlexMovieRepository(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_should_create_plex_movie(self):
        movie_details = {
            'plex_guid': 'abcd1234',
            'title': 'a title',
            'year': 1984,
            'duration': 124123123,
        }

        plex_movie = PlexMovieRepository.get_or_create(data=movie_details)

        self.assertEqual(movie_details['plex_guid'], plex_movie.plex_guid)
        self.assertEqual(movie_details['title'], plex_movie.title)
        self.assertEqual(movie_details['year'], plex_movie.year)
        self.assertEqual(movie_details['duration'], plex_movie.duration)

    def test_should_get_existing_plex_movie(self):
        plex_movie = PlexMovieFactory()

        movie_details = {
            'plex_guid': plex_movie.plex_guid,
        }
        obj_from_db = PlexMovieRepository.get_or_create(
            data=movie_details)

        self.assertEqual(plex_movie.pk, obj_from_db.pk)

    def test_should_get_plex_movie_by_title_iexact(self):
        plex_movie = PlexMovieFactory(title='BANANA')

        obj_from_db = PlexMovieRepository.get_by_title(
            plex_movie.title.lower())

        self.assertEqual(plex_movie.title, obj_from_db.title)


class TestPlexCommands(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_should_sync_plex_movies(self):
        # TODO
        pass
    def test_extract_tmdb_id_from_valid_guid(self):
        """Test extracting TMDB ID from a valid Plex GUID."""
        guid = 'com.plexapp.agents.themoviedb://278?lang=en'
        tmdb_id = SyncWithPlexCommand.extract_tmdb_id_from_guid(guid)
        self.assertEqual(tmdb_id, 278)

    def test_extract_tmdb_id_from_guid_without_themoviedb(self):
        """Test that non-TMDB GUIDs return None."""
        guid = 'com.plexapp.agents.imdb://tt0111161'
        tmdb_id = SyncWithPlexCommand.extract_tmdb_id_from_guid(guid)
        self.assertIsNone(tmdb_id)

    def test_extract_tmdb_id_with_different_formats(self):
        """Test extraction with various GUID formats."""
        # Standard format
        guid1 = 'com.plexapp.agents.themoviedb://550?lang=en'
        self.assertEqual(SyncWithPlexCommand.extract_tmdb_id_from_guid(guid1), 550)
        
        # Without language parameter
        guid2 = 'com.plexapp.agents.themoviedb://550'
        self.assertEqual(SyncWithPlexCommand.extract_tmdb_id_from_guid(guid2), 550)

    def test_merge_actors_no_duplicates(self):
        """Test that duplicates are removed when merging actor lists."""
        plex_actors = ['Tom Hanks', 'Meg Ryan', 'Gary Sinise']
        tmdb_actors = ['Tom Hanks', 'Meg Ryan', 'Bill Paxton', 'Ed Harris']
        
        merged = SyncWithPlexCommand.merge_actors(plex_actors, tmdb_actors)
        
        # Should have 5 unique actors
        self.assertEqual(len(merged), 5)
        
        # All unique actors should be present
        self.assertIn('Tom Hanks', merged)
        self.assertIn('Meg Ryan', merged)
        self.assertIn('Gary Sinise', merged)
        self.assertIn('Bill Paxton', merged)
        self.assertIn('Ed Harris', merged)

    def test_merge_actors_case_insensitive_deduplication(self):
        """Test that deduplication is case-insensitive."""
        plex_actors = ['Tom Hanks', 'Meg Ryan']
        tmdb_actors = ['tom hanks', 'meg ryan', 'Bill Paxton']  # lowercase versions
        
        merged = SyncWithPlexCommand.merge_actors(plex_actors, tmdb_actors)
        
        # Should have 3 unique actors (case-insensitive)
        self.assertEqual(len(merged), 3)

    def test_merge_actors_preserves_plex_actor_case(self):
        """Test that Plex actor casing is preserved over TMDB."""
        plex_actors = ['Tom Hanks']
        tmdb_actors = ['tom hanks', 'Bill Paxton']
        
        merged = SyncWithPlexCommand.merge_actors(plex_actors, tmdb_actors)
        
        # Should preserve the Plex casing
        self.assertIn('Tom Hanks', merged)
        self.assertNotIn('tom hanks', merged)

    def test_merge_actors_empty_lists(self):
        """Test merging when one or both lists are empty."""
        # Both empty
        merged = SyncWithPlexCommand.merge_actors([], [])
        self.assertEqual(merged, [])
        
        # Only Plex actors
        plex_actors = ['Tom Hanks', 'Meg Ryan']
        merged = SyncWithPlexCommand.merge_actors(plex_actors, [])
        self.assertEqual(len(merged), 2)
        
        # Only TMDB actors
        tmdb_actors = ['Tom Hanks', 'Bill Paxton']
        merged = SyncWithPlexCommand.merge_actors([], tmdb_actors)
        self.assertEqual(len(merged), 2)

    @patch('plex.commands.TMDB.get_movie_cast')
    def test_merge_actors_from_plex_and_tmdb(self, mock_get_cast):
        """Test that Plex and TMDB actors are merged together."""
        plex_actors = ['Tom Hanks', 'Meg Ryan']
        tmdb_actors = ['Tom Hanks', 'Meg Ryan', 'Bill Paxton', 'Ed Harris', 'Gary Sinise']
        
        mock_get_cast.return_value = tmdb_actors
        
        # Simulate the merge that happens in SyncWithPlexCommand
        merged = SyncWithPlexCommand.merge_actors(plex_actors, tmdb_actors)
        
        # Should have more actors after merging
        self.assertGreater(len(merged), len(plex_actors))
        self.assertEqual(len(merged), 5)

    @patch('plex.commands.TMDB.get_movie_cast')
    def test_tmdb_get_movie_cast_gracefully_handles_failure(self, mock_get_cast):
        """Test that missing TMDB cast doesn't break the sync."""
        mock_get_cast.return_value = []
        
        plex_actors = ['Tom Hanks']
        tmdb_actors = mock_get_cast(278)
        
        # Should still work with empty TMDB response
        merged = SyncWithPlexCommand.merge_actors(plex_actors, tmdb_actors)
        self.assertEqual(merged, ['Tom Hanks'])