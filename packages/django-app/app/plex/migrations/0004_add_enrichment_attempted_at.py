from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plex", "0003_add_actors_enriched_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="plexmovie",
            name="enrichment_attempted_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp of the last attempt to enrich actor data from TMDB.",
                null=True,
            ),
        ),
    ]
