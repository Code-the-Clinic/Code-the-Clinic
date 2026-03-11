from django.apps import AppConfig


class UserLoggingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'user_logging'
    verbose_name = 'User Activity Logging'

    def ready(self):
        import user_logging.signals 
