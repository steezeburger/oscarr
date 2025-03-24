import logging
from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrates Discord username to Ombi UID mappings from environment variables to the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting migration of Discord to Ombi UID mappings'))
        
        # Get the uid_map from settings
        uid_map = settings.OMBI_UID_MAP
        migrated_count = 0
        skipped_count = 0
        
        for discord_username, ombi_uid in uid_map.items():
            if discord_username == 'admin':
                # Skip the admin special case
                continue
                
            # Check if a user with this discord_username already exists
            try:
                user = User.objects.get(discord_username=discord_username)
                
                # Update the ombi_uid if not already set
                if not user.ombi_uid:
                    user.ombi_uid = ombi_uid
                    user.save()
                    self.stdout.write(f'Updated existing user {discord_username} with Ombi UID {ombi_uid}')
                    migrated_count += 1
                else:
                    self.stdout.write(f'User {discord_username} already has Ombi UID {user.ombi_uid}')
                    skipped_count += 1
                    
            except User.DoesNotExist:
                # Create a new user with this discord_username and ombi_uid
                user = User.objects.create(
                    nickname=discord_username,  # Use discord username as nickname
                    discord_username=discord_username,
                    ombi_uid=ombi_uid
                )
                self.stdout.write(f'Created new user with discord_username {discord_username} and Ombi UID {ombi_uid}')
                migrated_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Migration complete! Migrated {migrated_count} users, skipped {skipped_count} users'))