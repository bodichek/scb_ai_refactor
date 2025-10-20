from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import OnboardingProgress


User = get_user_model()


@receiver(post_save, sender=User)
def create_onboarding_progress(sender, instance, created, **kwargs):
    if not created:
        return

    progress, _ = OnboardingProgress.objects.get_or_create(user=instance)

    if instance.is_staff or instance.is_superuser:
        progress.is_completed = True
        progress.current_step = OnboardingProgress.Steps.DONE
        progress.save(update_fields=["is_completed", "current_step", "updated_at"])
