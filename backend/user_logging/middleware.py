"""Middleware for lightweight, privacy-aware admin portal activity logging.

This module is intentionally minimal and only records high-level navigation
metadata needed for security/audit insights (no request bodies or sensitive
query params are stored). See AdminPortalLog in user_logging.models for the
data schema.
"""

from urllib.parse import parse_qsl

from django.conf import settings

from .models import AdminPortalLog


SENSITIVE_QUERY_KEYS = {
    'password',
    'token',
    'access_token',
    'refresh_token',
    'code',
    'state',
    'secret',
    'authorization',
}


def _get_ip_address(request):
    """Extract a best-effort client IP address from the incoming request."""
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        candidate = forwarded.split(',')[0].strip()
    else:
        candidate = request.META.get('REMOTE_ADDR')

    if not candidate:
        return candidate

    # Some hosting environments include the port (e.g. "1.2.3.4:56789").
    # Strip the port for IPv4-style addresses so it fits GenericIPAddressField.
    if ':' in candidate and candidate.count('.') == 3:
        candidate = candidate.split(':', 1)[0]

    return candidate


def _sanitize_query_string(raw_query):
    """Redact sensitive keys and truncate query strings before logging."""
    if not raw_query:
        return ''

    safe_pairs = []
    for key, value in parse_qsl(raw_query, keep_blank_values=True):
        if key.lower() in SENSITIVE_QUERY_KEYS:
            safe_pairs.append((key, '[REDACTED]'))
        else:
            safe_pairs.append((key, value[:200]))

    return '&'.join(f'{k}={v}' for k, v in safe_pairs)[:1000]


class UserActivityLoggingMiddleware:
    """Capture high-level navigation activity while avoiding sensitive request data."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not getattr(settings, 'USER_LOGGING_ENABLED', True):
            return response

        try:
            path = request.path or ''
            excluded_prefixes = getattr(
                settings,
                'USER_LOGGING_EXCLUDED_PREFIXES',
                [
                    '/static/',
                    '/media/',
                    '/health/',
                    '/favicon.ico',
                    '/admin/jsi18n/',
                    '/admin/user_logging/adminportallog/',
                ],
            )

            if any(path.startswith(prefix) for prefix in excluded_prefixes):
                return response

            include_anonymous = getattr(settings, 'USER_LOGGING_INCLUDE_ANONYMOUS', False)
            if not include_anonymous and not request.user.is_authenticated:
                return response

            user = request.user if request.user.is_authenticated else None
            raw_query = request.META.get('QUERY_STRING', '')

            AdminPortalLog.objects.create(
                user=user,
                username=user.get_username() if user else '',
                email=getattr(user, 'email', '') if user else '',
                event_type=AdminPortalLog.EVENT_ACTIVITY,
                ip_address=_get_ip_address(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
                path=path[:512],
                extra_data={
                    'source': 'request_middleware',
                    'method': request.method,
                    'status_code': response.status_code,
                    'query': _sanitize_query_string(raw_query),
                    'is_authenticated': bool(user),
                },
            )
        except Exception:
            # Never break user requests because logging fails.
            pass

        return response
