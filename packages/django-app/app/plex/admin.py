from django.contrib import admin, messages

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
    search_fields = (
        'title',
        'actors',
        'directors',
        'producers',
        'writers',
    )

    actions = ['force_delete_plex_movie']

    @admin.action(description='!!! FORCE DELETE PLEX MOVIE !!!')
    def force_delete_plex_movie(self, request, queryset):
        queryset.delete(force_delete=True)
        self.message_user(
            request,
            "Force Deleted Plex Movies!",
            messages.SUCCESS)
