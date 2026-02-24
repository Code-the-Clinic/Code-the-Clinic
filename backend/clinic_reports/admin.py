from django.contrib import admin
from .models import ClinicReport, Sport, HealthcareProvider
from django.http import HttpResponse
from django.utils import timezone
import openpyxl


def export_raw_data_to_excel(modeladmin, request, queryset):
    """
    Downloads selected rows as an Excel file from the admin portal.
    """
    # Create a virtual workbook and sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Form Contents"

    # Define columns to export
    columns = ['first_name', 'last_name', 'email', 'sport',
               'immediate_emergency_care', 'musculoskeletal_exam', 'non_musculoskeletal_exam',
               'taping_bracing', 'rehabilitation_reconditioning', 'modalities',
               'pharmacology', 'injury_illness_prevention', 'non_sport_patient',
               'interacted_hcps', 'healthcare_provider', 'created_at']

    # Write the header row (column names)
    ws.append(columns)

    # Write the data rows
    for record in queryset:
        created_date = record.created_at
        # Strip timezone info from timestamp to enable saving to excel
        created_date = timezone.localtime(created_date).replace(tzinfo=None)
        
        # Order in this list must match the columns list above
        row = [
            record.first_name,
            record.last_name,
            record.email,
            record.sport.name,
            record.immediate_emergency_care,
            record.musculoskeletal_exam,
            record.non_musculoskeletal_exam,
            record.taping_bracing,
            record.rehabilitation_reconditioning,
            record.modalities,
            record.pharmacology,
            record.injury_illness_prevention,
            record.non_sport_patient,
            'Yes' if record.interacted_hcps else 'No',
            record.healthcare_provider.name if record.healthcare_provider else '',
            created_date
        ]
        ws.append(row)

    # Download the spreadsheet
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=forms_export.xlsx'
    
    # Save the workbook to the response
    wb.save(response)
    return response

# Name for Actions dropdown
export_raw_data_to_excel.short_description = "Export selected records to Excel"

@admin.register(ClinicReport)
class ClinicReportAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'sport', 'created_at')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('sport', 'created_at')
    actions = [export_raw_data_to_excel]


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    search_fields = ('name',)
    list_filter = ('active',)


@admin.register(HealthcareProvider)
class HealthcareProviderAdmin(admin.ModelAdmin):
    list_display = ('name', 'active')
    search_fields = ('name',)
    list_filter = ('active',)
