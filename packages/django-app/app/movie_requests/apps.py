from django.apps import AppConfig


class MovieRequestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"  # type: ignore[assignment]
    name = "movie_requests"
