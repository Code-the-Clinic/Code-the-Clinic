from django.apps import AppConfig


class UserLoggingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_logging'
    verbose_name = 'User Logging'

    def ready(self):
        # Register signal handlers for auth events
        import user_logging.signals  # noqa: F401
