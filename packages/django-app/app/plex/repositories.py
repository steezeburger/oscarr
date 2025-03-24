from asgiref.sync import sync_to_async
from django.db.models import Q

from common.repositories.base_repository import BaseRepository
from plex.models import PlexMovie


class PlexMovieRepository(BaseRepository):
    model = PlexMovie

    @classmethod
    def get_by_title(cls, title):
        plex_movie = cls.model.objects.filter(title__iexact=title).first()
        return plex_movie

    @classmethod
    def get_random(cls):
        plex_movie = cls.model.objects.order_by('?').first()
        return plex_movie

    @classmethod
    def get_latest(cls):
        plex_movie = cls.model.objects.order_by('-created_at').first()
        return plex_movie

    @classmethod
    @sync_to_async
    def get_by_title_async(cls, title):
        return cls.get_by_title(title)

    @classmethod
    def get_or_create(cls, data: dict):
        plex_movie = None

        if 'plex_guid' in data:
            qs = cls.model.objects.filter(
                plex_guid=data['plex_guid'])
            if qs:
                plex_movie = qs.first()

        if plex_movie is None:
            plex_movie = cls.model.objects.create(**data)

        return plex_movie

    @classmethod
    def search(
            cls,
            *,
            title=None,
            actor=None,
            director=None,
            producer=None,
            writer=None):
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
            Q(title__icontains=keyword) |
            Q(actors__icontains=keyword) |
            Q(directors__icontains=keyword) |
            Q(producers__icontains=keyword) |
            Q(writers__icontains=keyword))

        values = movies.values()

        return values
