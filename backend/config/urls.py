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
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection
import logging
import os

logger = logging.getLogger(__name__)

def _db_health_check(request):
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

urlpatterns = [
    path('health/', lambda request: JsonResponse({"status": "ok"}), name='health'),
    path('health/db/', _db_health_check, name='health_db'),
    path('', include('core.urls')),
    path(ADMIN_URL, admin.site.urls, name='admin'),
    path('accounts/', include('allauth.urls'), name='accounts'),
    path('clinic-reports/', include('clinic_reports.urls'), name='form'),
]
