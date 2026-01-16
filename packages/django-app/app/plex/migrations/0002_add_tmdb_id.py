# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plex", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="plexmovie",
            name="tmdb_id",
            field=models.IntegerField(
                blank=True,
                db_index=True,
                help_text="TMDB ID for enriching movie data.",
                null=True,
            ),
        ),
    ]
