# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plex", "0002_add_tmdb_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="plexmovie",
            name="actors_enriched_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp when actor data was last enriched from TMDB.",
                null=True,
            ),
        ),
    ]
