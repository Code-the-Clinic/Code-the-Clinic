from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, F, Case, When, IntegerField
from django.db.models.functions import Coalesce
import json
from clinic_reports.models import ClinicReport


# Security note: Viewing the faculty dashboard requires authentication
# TODO: Specify staff/superuser designation to access this page
@login_required
def faculty_dashboard_view(request):
    """Render the faculty/admin dashboard. Requires an authenticated user."""
    return render(request, 'core/faculty_dashboard.html')

@login_required
def student_dashboard_view(request):
    """Render the faculty/admin dashboard form. Requires an authenticated user."""
    return render(request, 'core/student_dashboard.html')

@require_http_methods(["POST"])
def fetch_data(request):
    """API endpoint to load data for dashboards (need to differentiate between students and faculty)
    
    Authorization:
    - Non-staff users can only view their own email's data
    - Staff users can filter by any email, sport, or clinical_site
    """
    if not request.user.is_authenticated:
        # Throw a 403 Forbidden error if user is not logged in
        return JsonResponse({'success': False, 'error': 'Authentication required'})
    try:
        filters = json.loads(request.body)
        clinic_reports = ClinicReport.objects.all()

        # Authorization: non-staff users can only view their own data
        if not request.user.is_staff:
            # Force non-staff users to view only their own email
            filters['email'] = request.user.email
        
        if filters.get('email'):
            clinic_reports = clinic_reports.filter(email=filters.get('email'))

        if filters.get('sport'):
            clinic_reports = clinic_reports.filter(sport=filters.get('sport'))
            
        if filters.get('clinical_site'):
            clinic_reports = clinic_reports.filter(clinical_site=filters.get('clinical_site'))

        # Get summary stats
        stats = clinic_reports.annotate(
            # Calculate the total patients served per row (1 row = 1 submitted form)
            weekly_total_patients=Coalesce(F('immediate_emergency_care'), 0) + 
            Coalesce(F('musculoskeletal_exam'), 0) +
            Coalesce(F('non_musculoskeletal_exam'), 0) +
            Coalesce(F('taping_bracing'), 0) +
            Coalesce(F('rehabilitation_reconditioning'), 0) +
            Coalesce(F('modalities'), 0) +
            Coalesce(F('pharmacology'), 0) +
            Coalesce(F('injury_illness_prevention'), 0) +
            Coalesce(F('non_sport_patient'), 0)
        ).aggregate(
            # Calculate average patient load
            average_patients_per_week=Avg('weekly_total_patients'),
            
            # Calculate total patients served by category
            total_immediate_emergency_care=Sum('immediate_emergency_care'),
            total_musculoskeletal_exam=Sum('musculoskeletal_exam'),
            total_non_musculoskeletal_exam=Sum('non_musculoskeletal_exam'),
            total_taping_bracing=Sum('taping_bracing'),
            total_rehabilitation_reconditioning=Sum('rehabilitation_reconditioning'),
            total_modalities=Sum('modalities'),
            total_pharmacology=Sum('pharmacology'),
            total_injury_illness_prevention=Sum('injury_illness_prevention'),
            total_non_sport_patient=Sum('non_sport_patient'),
            total_interacted_hcps=Sum(
                Case(
                    When(interacted_hcps=True, then=1),
                    default=0,
                    output_field=IntegerField()
                )
            ),

            # Total patients served across all students and categories
            grand_total_served=Sum('weekly_total_patients')
        )

        return JsonResponse({
            'success': True,
            'stats': stats,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
