from django.apps import AppConfig


class IntercomConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "intercom"

    def ready(self):
        from . import signals  # noqa: F401

