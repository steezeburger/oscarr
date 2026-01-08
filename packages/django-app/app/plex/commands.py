import logging
import re
from datetime import timezone

from django.conf import settings
from plexapi.myplex import MyPlexAccount

from common.commands.abstract_base_command import AbstractBaseCommand
from plex.repositories import PlexMovieRepository
from services.tmdb import TMDB

logger = logging.getLogger(__name__)


class SyncWithPlexCommand(AbstractBaseCommand):
    """
    Sync Oscarr's database with the movies on the Plex.
    Stops syncing when we get to a movie that was added
    before the latest movie in the database.

    Unfortunately the Plex API doesn't allow us to filter
    by addedAt, so we have to get a page of movies.
    """

    @staticmethod
    def extract_tmdb_id_from_guid(guid: str) -> int:
        """
        Extract TMDB ID from Plex GUID.
        Plex GUID format: com.plexapp.agents.themoviedb://278?lang=en
        Returns the TMDB ID (e.g., 278) or None if not found.
        """
        match = re.search(r'themoviedb://(\d+)', guid)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def merge_actors(plex_actors: list, tmdb_actors: list) -> list:
        """
        Merge Plex and TMDB actor lists, removing duplicates.
        Converts all to lowercase for comparison to catch case-insensitive duplicates.
        """
        seen = set()
        merged = []
        
        # Add all Plex actors first
        for actor in plex_actors:
            actor_lower = actor.lower()
            if actor_lower not in seen:
                seen.add(actor_lower)
                merged.append(actor)
        
        # Add TMDB actors that aren't already in the list
        for actor in tmdb_actors:
            actor_lower = actor.lower()
            if actor_lower not in seen:
                seen.add(actor_lower)
                merged.append(actor)
        
        return merged

    def execute(self) -> None:
        super().execute()

        account = MyPlexAccount(settings.PLEX_USERNAME,
                                settings.PLEX_PASSWORD)
        plex = account.resource(settings.PLEX_SERVER_NAME).connect()
        movies = plex.library.section('Movies')

        latest_movie = PlexMovieRepository.get_latest()

        for movie in movies.all(sort='addedAt:desc',
                                container_start=0,
                                container_size=5):
            added_at = movie.addedAt.replace(tzinfo=timezone.utc)
            if latest_movie and added_at <= latest_movie.created_at:
                # break out of loop if we start to get a movie
                # added before the latest movie in the database
                return

            try:
                # Get Plex actors
                plex_actors = [t.tag for t in movie.actors]
                
                # Try to get TMDB actors to supplement Plex actors
                tmdb_actors = []
                tmdb_id = self.extract_tmdb_id_from_guid(movie.guid)
                if tmdb_id:
                    tmdb_actors = TMDB.get_movie_cast(tmdb_id)
                
                # Merge actors from both sources
                all_actors = self.merge_actors(plex_actors, tmdb_actors)
                
                movie_details = {
                    'plex_guid': movie.guid,
                    'title': movie.title,
                    'year': movie.year,
                    'duration': movie.duration,
                    'actors': all_actors,
                    'genres': [t.tag for t in movie.genres],
                    'directors': [t.tag for t in movie.directors],
                    'producers': [t.tag for t in movie.producers],
                    'writers': [t.tag for t in movie.writers],
                }
                plex_movie = PlexMovieRepository.get_or_create(movie_details)

                plex_movie.created_at = added_at
                plex_movie.save()
                print(f'Created PlexMovie: {plex_movie}')
            except Exception as e:
                logger.exception(f"Failed to create PlexMovie: {movie}")
                logger.exception(e)
