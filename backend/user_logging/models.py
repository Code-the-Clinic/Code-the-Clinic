from django.conf import settings
from django.db import models


class AdminPortalLog(models.Model):
    EVENT_ACTIVITY = 'activity'
    EVENT_LOGIN = 'login'
    EVENT_LOGOUT = 'logout'
    EVENT_LOGIN_FAILED = 'login_failed'

    EVENT_CHOICES = [
        (EVENT_ACTIVITY, 'Activity'),
        (EVENT_LOGIN, 'Login'),
        (EVENT_LOGOUT, 'Logout'),
        (EVENT_LOGIN_FAILED, 'Login Failed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_portal_logs',
    )
    username = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    path = models.CharField(max_length=512, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['event_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        identity = self.email or self.username or 'unknown-user'
        return f"{self.event_type} - {identity} @ {self.created_at:%Y-%m-%d %H:%M:%S}"
