from django.apps import AppConfig


class UserLoggingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_logging'
    verbose_name = 'User Logging'

    def ready(self):
        """Import auth signal handlers so they are registered at startup."""
        # Register signal handlers for auth events
        import user_logging.signals  # noqa: F401
