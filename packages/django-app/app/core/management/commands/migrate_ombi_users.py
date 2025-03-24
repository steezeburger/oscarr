import logging
from django.conf import settings
from django.core.management.base import BaseCommand

from core.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Migrates Discord username to Ombi UID mappings from environment variables to the database'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            'Starting migration of Discord to Ombi UID mappings'))

        # Get the uid_map from settings
        uid_map = settings.OMBI_UID_MAP
        admin_uid = settings.OMBI_ADMIN_UID
        migrated_count = 0
        skipped_count = 0

        # First, ensure the admin user exists with correct Ombi UID
        if admin_uid:
            try:
                # Look for user with nickname="admin"
                try:
                    admin_user = User.objects.get(nickname="admin")

                    # Update admin fields
                    if not admin_user.discord_username:
                        admin_user.discord_username = "admin"

                    if not admin_user.ombi_uid:
                        admin_user.ombi_uid = admin_uid
                        admin_user.save()
                        self.stdout.write(
                            f'Updated admin user with discord username and Ombi UID {admin_uid}')
                        migrated_count += 1
                    else:
                        self.stdout.write(
                            f'Admin user already has Ombi UID {admin_user.ombi_uid}')
                        skipped_count += 1

                except User.DoesNotExist:
                    # Try finding a superuser to use
                    superuser = User.objects.filter(is_superuser=True).first()
                    if superuser:
                        if not superuser.discord_username:
                            superuser.discord_username = "admin"
                        if not superuser.ombi_uid:
                            superuser.ombi_uid = admin_uid
                            superuser.save()
                            self.stdout.write(
                                f'Updated superuser {superuser.nickname} with admin discord username and Ombi UID {admin_uid}')
                            migrated_count += 1
                        else:
                            self.stdout.write(
                                f'Superuser {superuser.nickname} already has Ombi UID')
                            skipped_count += 1
                    else:
                        # Create a new admin user
                        admin_user = User.objects.create(
                            nickname="admin",
                            discord_username="admin",
                            ombi_uid=admin_uid,
                            is_staff=True
                        )
                        self.stdout.write(
                            f'Created admin user with Ombi UID {admin_uid}')
                        migrated_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error handling admin user: {str(e)}'))

        # Process all users from uid_map
        for discord_username, ombi_uid in uid_map.items():
            # Check if a user with this discord_username already exists
            try:
                user = User.objects.get(discord_username=discord_username)

                # Update the ombi_uid if not already set
                if not user.ombi_uid:
                    user.ombi_uid = ombi_uid
                    user.save()
                    self.stdout.write(
                        f'Updated existing user {discord_username} with Ombi UID {ombi_uid}')
                    migrated_count += 1
                else:
                    self.stdout.write(
                        f'User {discord_username} already has Ombi UID {user.ombi_uid}')
                    skipped_count += 1

            except User.DoesNotExist:
                # Create a new user with this discord_username and ombi_uid
                user = User.objects.create(
                    nickname=discord_username,  # Use discord username as nickname
                    discord_username=discord_username,
                    ombi_uid=ombi_uid
                )
                self.stdout.write(
                    f'Created new user with discord_username {discord_username} and Ombi UID {ombi_uid}')
                migrated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Migration complete! Migrated {migrated_count} users, skipped {skipped_count} users'))
