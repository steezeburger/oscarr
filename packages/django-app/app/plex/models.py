from common.models.crud_timestamps_mixin import CRUDTimestampsMixin
from common.models.soft_delete_timestamp_mixin import SoftDeleteTimestampMixin
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.utils.translation import gettext_lazy as _


class PlexMovie(SoftDeleteTimestampMixin, CRUDTimestampsMixin):
    """
    Model representing a movie that exists on the Plex server.
    """

    plex_guid = models.CharField(max_length=512, help_text=_("Plex GUID."))

    tmdb_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text=_("TMDB ID for enriching movie data."),  # type: ignore[arg-type]
    )

    title = models.CharField(max_length=255, help_text=_("The title of the movie."))

    year = models.SmallIntegerField(
        db_index=True,
        null=True,
        blank=True,
        help_text=_("The year the movie was released."),  # type: ignore[arg-type]
    )

    duration = models.BigIntegerField(
        help_text=_("The duration of the movie in milliseconds.")  # type: ignore[arg-type]
    )

    actors = ArrayField(models.CharField(max_length=255, blank=True), null=True, blank=True)

    actors_enriched_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Timestamp when actor data was last enriched from TMDB."),  # type: ignore[arg-type]
    )

    genres = ArrayField(models.CharField(max_length=255, blank=True), null=True, blank=True)

    directors = ArrayField(models.CharField(max_length=255, blank=True), null=True, blank=True)

    producers = ArrayField(models.CharField(max_length=255, blank=True), null=True, blank=True)

    writers = ArrayField(models.CharField(max_length=255, blank=True), null=True, blank=True)

    class Meta:
        db_table = "plex_movies"
        default_permissions = ()
        ordering = ("id",)

    def __str__(self):
        return f"{self.title} ({self.year})"


class CachedGraph(models.Model):
    """
    Model for storing pickled NetworkX graphs in the database.
    Generic storage for any graph type (actor, producer, director, etc.).
    """

    key = models.CharField(
        max_length=255,
        unique=True,
        primary_key=True,
        help_text=_("Unique identifier for the cached graph (e.g., 'actor_graph')"),  # type: ignore[arg-type]
    )

    data = models.BinaryField(
        help_text=_("Pickled graph data stored as binary")  # type: ignore[arg-type]
    )

    updated_at = models.DateTimeField(
        auto_now=True, help_text=_("Timestamp of last cache update")  # type: ignore[arg-type]
    )

    class Meta:
        db_table = "cached_graphs"
        default_permissions = ()

    def __str__(self):
        return f"CachedGraph: {self.key}"
