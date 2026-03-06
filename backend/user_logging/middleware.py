from .models import UserActivityLog
from .services import log_user_activity


class UserActivityMiddleware:
    """Log authenticated user page visits for selected routes."""

    SKIPPED_PREFIXES = (
        '/health/',
        '/static/',
        '/media/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if self._should_log(request):
            event_type = UserActivityLog.EventType.PAGE_VIEW
            if request.path.startswith('/dashboard/'):
                event_type = UserActivityLog.EventType.DASHBOARD_VIEW

            log_user_activity(
                request=request,
                event_type=event_type,
                status_code=response.status_code,
                details={'route': request.path},
            )

        return response

    def _should_log(self, request):
        request_user = getattr(request, 'user', None)
        if not request_user or not request_user.is_authenticated:
            return False

        if request.method != 'GET':
            return False

        if any(request.path.startswith(prefix) for prefix in self.SKIPPED_PREFIXES):
            return False

        return True
