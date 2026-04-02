import os

from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import AdminPortalLog


def _normalized_admin_path_prefix():
    admin_url = os.environ.get('ADMIN_URL', 'admin/').strip('/')
    return f'/{admin_url}/'


def _is_admin_url(url_value):
    if not url_value:
        return False

    admin_prefix = _normalized_admin_path_prefix()
    return admin_prefix in url_value or url_value.startswith(admin_prefix.rstrip('/'))


def _is_admin_request(request):
    if request is None:
        return False

    path = request.path or ''
    if path.startswith(_normalized_admin_path_prefix()):
        return True

    # Handle SSO/OAuth flows where auth happens at /accounts/* but next target is admin.
    next_from_get = request.GET.get('next', '')
    next_from_post = request.POST.get('next', '')
    next_from_session = request.session.get('socialaccount_next_url', '') if hasattr(request, 'session') else ''
    referrer = request.META.get('HTTP_REFERER', '')

    return any(
        _is_admin_url(candidate)
        for candidate in [next_from_get, next_from_post, next_from_session, referrer]
    )


def _get_ip_address(request):
    if request is None:
        return None

    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _build_base_log_data(request):
    return {
        'ip_address': _get_ip_address(request),
        'user_agent': request.META.get('HTTP_USER_AGENT', '') if request else '',
        'path': request.path if request else '',
    }


@receiver(user_logged_in)
def log_admin_user_login(sender, request, user, **kwargs):
    data = _build_base_log_data(request)
    request_scope = 'admin' if _is_admin_request(request) else 'general'
    AdminPortalLog.objects.create(
        user=user,
        username=user.get_username(),
        email=getattr(user, 'email', '') or '',
        event_type=AdminPortalLog.EVENT_LOGIN,
        extra_data={'source': 'django_auth_signal', 'request_scope': request_scope},
        **data,
    )


@receiver(user_logged_out)
def log_admin_user_logout(sender, request, user, **kwargs):
    data = _build_base_log_data(request)
    request_scope = 'admin' if _is_admin_request(request) else 'general'
    username = user.get_username() if user else ''
    email = getattr(user, 'email', '') if user else ''
    AdminPortalLog.objects.create(
        user=user if user and user.is_authenticated else None,
        username=username,
        email=email or '',
        event_type=AdminPortalLog.EVENT_LOGOUT,
        extra_data={'source': 'django_auth_signal', 'request_scope': request_scope},
        **data,
    )


@receiver(user_login_failed)
def log_admin_user_login_failed(sender, credentials, request, **kwargs):
    attempted_username = ''
    if isinstance(credentials, dict):
        attempted_username = (
            credentials.get('username')
            or credentials.get('email')
            or ''
        )

    data = _build_base_log_data(request)
    request_scope = 'admin' if _is_admin_request(request) else 'general'
    AdminPortalLog.objects.create(
        username=attempted_username,
        event_type=AdminPortalLog.EVENT_LOGIN_FAILED,
        extra_data={'source': 'django_auth_signal', 'request_scope': request_scope},
        **data,
    )
