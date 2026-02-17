from django.db import models
from django.conf import settings


class UserActivity(models.Model):
    """Simple model to record user activity with timestamp.

    It intentionally keeps a small surface: user (nullable for anonymous),
    action (path or description), ip address and user agent.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=500, blank=True)
    ip_address = models.CharField(max_length=45, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "user activity"
        verbose_name_plural = "user activities"

    def __str__(self):
        who = self.user.get_username() if self.user else "anonymous"
        return f"{who} @ {self.created_at.isoformat()} -> {self.action}"
