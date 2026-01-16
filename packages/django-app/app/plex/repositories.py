from asgiref.sync import sync_to_async
from common.repositories.base_repository import BaseRepository
from django.db.models import Q
from django.utils import timezone

from plex.models import PlexMovie


class PlexMovieRepository(BaseRepository):
    model = PlexMovie

    @classmethod
    def get_by_title(cls, title):
        plex_movie = cls.model.objects.filter(title__iexact=title).first()
        return plex_movie

    @classmethod
    def get_random(cls):
        plex_movie = cls.model.objects.order_by("?").first()
        return plex_movie

    @classmethod
    def get_latest(cls):
        plex_movie = cls.model.objects.order_by("-created_at").first()
        return plex_movie

    @classmethod
    @sync_to_async
    def get_by_title_async(cls, title):
        return cls.get_by_title(title)

    @classmethod
    def get_or_create(cls, data: dict):
        plex_movie = None

        if "plex_guid" in data:
            qs = cls.model.objects.filter(plex_guid=data["plex_guid"])
            if qs:
                plex_movie = qs.first()

        if plex_movie is None:
            plex_movie = cls.model.objects.create(**data)

        return plex_movie

    @classmethod
    def search(cls, *, title=None, actor=None, director=None, producer=None, writer=None):
        movies = cls.model.objects.all()

        if title:
            movies = movies.filter(title__icontains=title)

        if actor:
            movies = movies.filter(actors__icontains=actor)

        if director:
            movies = movies.filter(directors__icontains=director)

        if producer:
            movies = movies.filter(producers__icontains=producer)

        if writer:
            movies = movies.filter(writers__icontains=writer)

        values = movies.values()

        return values

    @classmethod
    def search_all(cls, keyword):
        movies = cls.model.objects.filter(
            Q(title__icontains=keyword)
            | Q(actors__icontains=keyword)  # type: ignore[operator]
            | Q(directors__icontains=keyword)
            | Q(producers__icontains=keyword)
            | Q(writers__icontains=keyword)
        )

        values = movies.values()

        return values

    @classmethod
    def get_active_movies(cls, without_enrichment=False, limit=None):
        """
        Get active movies, optionally filtering by actor enrichment status.

        Args:
            without_enrichment: If True, only return movies that haven't been enriched
            limit: Maximum number of movies to return

        Returns:
            QuerySet of PlexMovie instances ordered by created_at descending
        """
        movies = cls.model.objects.filter(is_active=True)

        if without_enrichment:
            movies = movies.filter(actors_enriched_at__isnull=True)

        movies = movies.order_by("-created_at")

        if limit:
            movies = movies[:limit]

        return movies

    @classmethod
    def update_movie_actors(cls, movie, actors, tmdb_id=None):
        """
        Update a movie's actors list and mark as enriched.

        Args:
            movie: PlexMovie instance to update
            actors: List of actor names
            tmdb_id: Optional TMDB ID to set if not already present

        Returns:
            Updated PlexMovie instance
        """
        movie.actors = actors
        movie.actors_enriched_at = timezone.now()

        if tmdb_id and not movie.tmdb_id:
            movie.tmdb_id = tmdb_id

        movie.save()
        return movie

    @classmethod
    async def update_movie_actors_async(cls, movie, actors, tmdb_id=None):
        """
        Async version of update_movie_actors.

        Args:
            movie: PlexMovie instance to update
            actors: List of actor names
            tmdb_id: Optional TMDB ID to set if not already present

        Returns:
            Updated PlexMovie instance
        """
        movie.actors = actors
        movie.actors_enriched_at = timezone.now()

        if tmdb_id and not movie.tmdb_id:
            movie.tmdb_id = tmdb_id

        await sync_to_async(movie.save)()
        return movie
