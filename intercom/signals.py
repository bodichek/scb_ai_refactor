from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Message, Notification


@receiver(post_save, sender=Message)
def on_message_created(sender, instance: Message, created, **kwargs):
    if not created:
        return

    # aktualizace času poslední zprávy ve vlákně
    thread = instance.thread
    thread.last_message_at = timezone.now()
    thread.save(update_fields=["last_message_at"])

    # notifikace pro protistranu
    recipient = thread.coach if instance.sender_id == thread.client_id else thread.client
    Notification.objects.create(user=recipient, message=instance)

