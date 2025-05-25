import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.models import User
from services.ombi import Ombi

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_ombi_user(sender, instance, created, **kwargs):
    """
    Signal handler to create an Ombi user when a Django user is created,
    and set the ombi_uid field on the Django user.
    """
    if created and not instance.ombi_uid:
        try:
            logger.info(f"Creating Ombi user for Django user {instance.nickname}")
            
            # Create user in Ombi
            response = Ombi.create_user(username=instance.nickname)
            
            # Extract user ID from response and update Django user
            if response and 'id' in response:
                ombi_uid = response['id']
                logger.info(f"Updating Django user {instance.nickname} with Ombi UID {ombi_uid}")
                
                # Update the user without triggering the signal again
                User.objects.filter(id=instance.id).update(ombi_uid=ombi_uid)
            else:
                logger.error(f"Failed to get Ombi UID from response: {response}")
                
        except Exception as e:
            logger.error(f"Error creating Ombi user for {instance.nickname}: {str(e)}")
