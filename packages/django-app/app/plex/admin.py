from django.contrib import admin

from .models import PlexMovie


@admin.register(PlexMovie)
class PlexMovieAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'created_at',
        'modified_at',
        'deleted_at',
        'is_active',
        'plex_guid',
        'title',
        'year',
        'duration',
        'actors',
        'genres',
        'directors',
        'producers',
        'writers',
    )
    list_filter = ('created_at', 'modified_at', 'deleted_at', 'is_active')
    date_hierarchy = 'created_at'
