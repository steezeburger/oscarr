import factory

from factory.django import DjangoModelFactory

from plex.models import PlexMovie


class PlexMovieFactory(DjangoModelFactory):
    plex_guid = factory.Faker('uuid4')

    title = factory.Faker('bs')

    year = factory.Faker('year')

    duration = factory.Faker('unix_time')

    class Meta:
        model = PlexMovie
