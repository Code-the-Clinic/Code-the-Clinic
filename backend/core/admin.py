from django.contrib import admin
from .models import UserActivity


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "ip_address", "created_at")
    list_filter = ("user",)
    search_fields = ("action", "user__username", "ip_address")

# Register your models here.
