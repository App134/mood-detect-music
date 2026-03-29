import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile, UserPreferences

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_or_update_profile(sender, instance, created, **kwargs):
    if created:
        try:
            UserProfile.objects.get_or_create(user=instance)
            UserPreferences.objects.get_or_create(user=instance)
            logger.info(f"Successfully created Profile and Preferences for user: {instance.username}")
        except Exception as e:
            logger.error(f"Error creating profile for {instance.username}: {str(e)}")
