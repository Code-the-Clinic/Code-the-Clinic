from django.utils import timezone
from .models import UserActivity


class UserActivityLoggingMiddleware:
    """Middleware that creates a UserActivity row for authenticated users.

    Adds a minimal footprint: logs path, IP and user agent. It only logs
    requests for authenticated users to avoid noise
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        try:
            user = getattr(request, "user", None)
            # log when user is authenticated to keep table concise
            if user and user.is_authenticated:
                ip = request.META.get("HTTP_X_FORWARDED_FOR")
                if ip:
                    ip = ip.split(",")[0].strip()
                else:
                    ip = request.META.get("REMOTE_ADDR", "")

                UserActivity.objects.create(
                    user=user,
                    action=request.path[:500],
                    ip_address=ip[:45],
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
                )
        except Exception:
            # Never let logging break the request swallow errors silently
            pass

        return response
