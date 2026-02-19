from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, F, Case, When, IntegerField, Value, FloatField
from django.db.models.functions import Coalesce
from django.core.exceptions import PermissionDenied
import json
from clinic_reports.models import ClinicReport

# Security note: Viewing the faculty dashboard requires authentication
@login_required
def faculty_dashboard_view(request):
    """Render the faculty/admin dashboard. Requires staff permission."""
    if not request.user.is_staff:
        raise PermissionDenied("You don't have permission to access this page.")
    return render(request, 'core/faculty_dashboard.html')

@login_required
def student_dashboard_view(request):
    """Render the student dashboard."""
    return render(request, 'core/student_dashboard.html')

def home_view(request):
    """Render the homepage."""
    return render(request, 'core/home.html')

@require_http_methods(["POST"])
def fetch_data(request):
    """API endpoint to load data for dashboards (need to differentiate between students and faculty)
    
    Authorization:
    - Non-staff users can only view their own email's data
    - Staff users can filter by any email or sport
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
            # Filter by sport name, not ID, because this will make the API more intuitive to use
            clinic_reports = clinic_reports.filter(sport__name=filters.get('sport'))

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
            average_patients_per_week=Coalesce(
                Avg('weekly_total_patients'),
                Value(0.0),
                output_field=FloatField()
            ),
            
            # Calculate total patients served by category
            total_immediate_emergency_care=Coalesce(Sum('immediate_emergency_care'), Value(0)),
            total_musculoskeletal_exam=Coalesce(Sum('musculoskeletal_exam'), Value(0)),
            total_non_musculoskeletal_exam=Coalesce(Sum('non_musculoskeletal_exam'), Value(0)),
            total_taping_bracing=Coalesce(Sum('taping_bracing'), Value(0)),
            total_rehabilitation_reconditioning=Coalesce(Sum('rehabilitation_reconditioning'), Value(0)),
            total_modalities=Coalesce(Sum('modalities'), Value(0)),
            total_pharmacology=Coalesce(Sum('pharmacology'), Value(0)),
            total_injury_illness_prevention=Coalesce(Sum('injury_illness_prevention'), Value(0)),
            total_non_sport_patient=Coalesce(Sum('non_sport_patient'), Value(0)),
            total_interacted_hcps=Coalesce(
                Sum(
                    Case(
                        When(interacted_hcps=True, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                ),
                Value(0)
            ),

            # Total patients served across all students and categories
            grand_total_served=Coalesce(Sum('weekly_total_patients'), Value(0))
        )

        return JsonResponse({
            'success': True,
            'stats': stats,
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
