from django.contrib import admin

from .models import AdminPortalLog


@admin.register(AdminPortalLog)
class AdminPortalLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'event_type', 'username', 'email', 'ip_address', 'path')
    list_filter = ('event_type', 'created_at')
    search_fields = ('username', 'email', 'ip_address', 'path')
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at',
        'event_type',
        'user',
        'username',
        'email',
        'ip_address',
        'user_agent',
        'path',
        'extra_data',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
