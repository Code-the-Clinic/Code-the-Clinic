"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.db import connection
import logging
import os

logger = logging.getLogger(__name__)

def _db_health_check(request):
    """Perform a simple database connectivity check for health endpoints."""
    try:
        connection.ensure_connection()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return JsonResponse({"status": "ok", "db": "ok"})
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        return JsonResponse({"status": "error", "db": "Database connection failed"}, status=500)

# Configurable admin URL - set ADMIN_URL in env to keep it secret from public repo
# Defaults to 'admin/' for local development
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')


def _admin_login(request):
    """
    In production, force admin auth through Microsoft SSO unless break-glass
    password login is explicitly enabled.
    """
    if settings.ALLOW_PASSWORD_ADMIN_LOGIN:
        return admin.site.login(request)

    next_url = request.GET.get('next', f'/{ADMIN_URL}')
    if not url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = f'/{ADMIN_URL}'

    query = urlencode({'next': next_url})
    return redirect(f'/accounts/microsoft/login/?{query}')

urlpatterns = [
    path('health/', lambda request: JsonResponse({"status": "ok"}), name='health'),
    path('health/db/', _db_health_check, name='health_db'),
    path('', include('core.urls')),
    path(f'{ADMIN_URL}login/', _admin_login, name='admin_login'),
    path(ADMIN_URL, admin.site.urls, name='admin'),
    path('accounts/', include('allauth.urls'), name='accounts'),
    path('clinic-reports/', include('clinic_reports.urls'), name='form'),
]
