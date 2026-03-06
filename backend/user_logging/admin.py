from django.contrib import admin

from .models import UserActivityLog


@admin.register(UserActivityLog)
class UserActivityLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'path',
        'ip_address',
        'created_at',
        'method',
        'status_code',
        'event_type',
    )
    list_filter = ('event_type', 'method', 'status_code', 'created_at')
    search_fields = ('user__username', 'user__email', 'path', 'ip_address')
    readonly_fields = (
        'user',
        'event_type',
        'path',
        'method',
        'status_code',
        'ip_address',
        'user_agent',
        'details',
        'created_at',
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
