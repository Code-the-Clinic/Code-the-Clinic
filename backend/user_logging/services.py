import logging

from django.db import OperationalError, ProgrammingError

from .models import UserActivityLog


logger = logging.getLogger(__name__)


def _safe_text(value):
    """Return a database-safe string for Char/Text fields."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    return str(value)


def get_client_ip(request):
    """Get best-effort client IP (supports X-Forwarded-For)."""
    if request is None:
        return None

    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_user_activity(
    *,
    event_type,
    request=None,
    user=None,
    path='',
    method='',
    status_code=None,
    details=None,
):
    """Create a user activity log entry."""
    if details is None:
        details = {}
    elif not isinstance(details, dict):
        details = {'value': str(details)}

    request_user = getattr(request, 'user', None)
    if user is None and request_user and request_user.is_authenticated:
        user = request_user

    raw_path = path if path not in (None, '') else (getattr(request, 'path', '') if request else '')
    raw_method = method if method not in (None, '') else (getattr(request, 'method', '') if request else '')
    raw_user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''

    final_path = _safe_text(raw_path)
    final_method = _safe_text(raw_method)
    user_agent = _safe_text(raw_user_agent)

    try:
        return UserActivityLog.objects.create(
            user=user,
            event_type=event_type,
            path=final_path,
            method=final_method,
            status_code=status_code,
            ip_address=get_client_ip(request),
            user_agent=user_agent,
            details=details,
        )
    except (OperationalError, ProgrammingError):
        logger.debug('Skipping user activity log because the table is not ready yet.')
        return None
    except Exception:
        logger.exception('Unexpected error while writing user activity log.')
        return None
