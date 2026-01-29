from django.contrib import admin
from .models import ClinicReport


@admin.register(ClinicReport)
class ClinicReportAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'sport', 'clinical_site', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('sport', 'clinical_site', 'created_at')
