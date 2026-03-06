from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import UserActivityLog
from .services import log_user_activity


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    log_user_activity(
        request=request,
        user=user,
        event_type=UserActivityLog.EventType.LOGIN,
        details={'email': user.email},
    )


@receiver(user_logged_out)
def log_successful_logout(sender, request, user, **kwargs):
    log_user_activity(
        request=request,
        user=user,
        event_type=UserActivityLog.EventType.LOGOUT,
        details={'email': getattr(user, 'email', '') if user else ''},
    )


@receiver(user_login_failed)
def log_failed_login(sender, credentials, request, **kwargs):
    attempted_identifier = ''
    if isinstance(credentials, dict):
        attempted_identifier = (
            credentials.get('email')
            or credentials.get('username')
            or credentials.get('login')
            or ''
        )

    log_user_activity(
        request=request,
        event_type=UserActivityLog.EventType.LOGIN_FAILED,
        details={'attempted_identifier': attempted_identifier},
    )
