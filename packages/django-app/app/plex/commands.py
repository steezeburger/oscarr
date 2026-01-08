import logging
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
                # Get actors from Plex
                plex_actors = [t.tag for t in movie.actors]

                # Augment with TMDB actors
                actors = self._get_augmented_actors(
                    movie.title, movie.year, plex_actors)

                movie_details = {
                    'plex_guid': movie.guid,
                    'title': movie.title,
                    'year': movie.year,
                    'duration': movie.duration,
                    'actors': actors,
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

    def _get_augmented_actors(self, title: str, year: int,
                               plex_actors: list) -> list:
        """
        Fetch actors from TMDB and merge with Plex actors.
        Returns a deduplicated list preserving order.
        """
        try:
            tmdb_movie = TMDB.search_by_title_and_year(title, year)
            if tmdb_movie:
                tmdb_id = tmdb_movie['id']
                tmdb_actors = TMDB.get_movie_credits(tmdb_id, cast_limit=20)

                # Merge: TMDB actors first (more complete), then Plex actors
                seen = set()
                merged = []
                for actor in tmdb_actors + plex_actors:
                    actor_lower = actor.lower()
                    if actor_lower not in seen:
                        seen.add(actor_lower)
                        merged.append(actor)
                return merged
        except Exception as e:
            logger.warning(f"Failed to fetch TMDB actors for {title}: {e}")

        return plex_actors


class BackfillActorsCommand(AbstractBaseCommand):
    """
    Backfill TMDB actors for existing PlexMovie records.
    Fetches top 20 actors from TMDB and merges with existing actors.
    """

    def execute(self) -> None:
        super().execute()

        movies = PlexMovieRepository.model.objects.all()
        total = movies.count()
        updated = 0
        failed = 0

        for i, movie in enumerate(movies, 1):
            try:
                tmdb_movie = TMDB.search_by_title_and_year(movie.title,
                                                           movie.year)
                if tmdb_movie:
                    tmdb_id = tmdb_movie['id']
                    tmdb_actors = TMDB.get_movie_credits(tmdb_id, cast_limit=20)

                    # Merge actors (TMDB first, then existing)
                    existing_actors = movie.actors or []
                    seen = set()
                    merged = []
                    for actor in tmdb_actors + existing_actors:
                        actor_lower = actor.lower()
                        if actor_lower not in seen:
                            seen.add(actor_lower)
                            merged.append(actor)

                    if len(merged) > len(existing_actors):
                        movie.actors = merged
                        movie.save()
                        updated += 1
                        print(f'[{i}/{total}] Updated: {movie.title} '
                              f'({len(existing_actors)} -> {len(merged)} actors)')
                    else:
                        print(f'[{i}/{total}] Skipped: {movie.title} '
                              f'(no new actors)')
                else:
                    print(f'[{i}/{total}] Not found on TMDB: {movie.title}')
                    failed += 1

            except Exception as e:
                logger.exception(f"Failed to backfill actors for: {movie}")
                failed += 1

        print(f'\nBackfill complete: {updated} updated, {failed} failed, '
              f'{total - updated - failed} unchanged')
