from factory import Faker  # type: ignore[attr-defined]
from factory.django import DjangoModelFactory

from plex.models import PlexMovie


class PlexMovieFactory(DjangoModelFactory):
    plex_guid = Faker("uuid4")

    title = Faker("bs")

    year = Faker("year")

    duration = Faker("unix_time")

    class Meta:
        model = PlexMovie
