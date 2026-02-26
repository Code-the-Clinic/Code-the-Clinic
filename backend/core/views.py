from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, F, Case, When, IntegerField, Value, FloatField
from django.db.models.functions import Coalesce
from django.core.exceptions import PermissionDenied
import json
from clinic_reports.models import ClinicReport, Sport

# Security note: Viewing the faculty dashboard requires authentication
@login_required
@login_required
def faculty_dashboard_view(request):
    """Faculty dashboard with heat map and pie chart"""
    if not request.user.is_staff:
        raise PermissionDenied("You don't have permission to access this page.")
    
    # Get filter values
    selected_sport = request.GET.get('sport')
    selected_semester = request.GET.get('semester')
    
    # Base queryset for pie chart (filtered by both)
    pie_reports = ClinicReport.objects.all()
    if selected_semester:
        pie_reports = pie_reports.filter(semester=selected_semester)
    if selected_sport:
        pie_reports = pie_reports.filter(sport__name=selected_sport)
    
    # Calculate pie chart totals
    pie_totals = pie_reports.aggregate(
        immediate=Sum('immediate_emergency_care') or 0,
        musculoskeletal=Sum('musculoskeletal_exam') or 0,
        non_musculoskeletal=Sum('non_musculoskeletal_exam') or 0,
        taping=Sum('taping_bracing') or 0,
        rehab=Sum('rehabilitation_reconditioning') or 0,
        modalities=Sum('modalities') or 0,
        pharmacology=Sum('pharmacology') or 0,
        prevention=Sum('injury_illness_prevention') or 0,
        non_sport=Sum('non_sport_patient') or 0,
    )
    
    # Prepare pie chart data
    pie_chart_data = []
    for label, key in [
        ('Immediate/Emergency', 'immediate'),
        ('Musculoskeletal Exam', 'musculoskeletal'),
        ('Non-Musculoskeletal', 'non_musculoskeletal'),
        ('Taping/Bracing', 'taping'),
        ('Rehabilitation', 'rehab'),
        ('Modalities', 'modalities'),
        ('Pharmacology', 'pharmacology'),
        ('Injury Prevention', 'prevention'),
        ('Non-Sport Patient', 'non_sport'),
    ]:
        value = pie_totals[key]
        if value is not None and value > 0:
            pie_chart_data.append({'label': label, 'value': value})
    
    # Heat map data (always shows ALL sports, filtered only by semester)
    heatmap_reports = ClinicReport.objects.all()
    if selected_semester:
        heatmap_reports = heatmap_reports.filter(semester=selected_semester)
    
    # Get all sports and categories
    all_sports = Sport.objects.filter(clinicreport__isnull=False).distinct().order_by('name')
    categories = [
        ('Immediate/Emergency', 'immediate_emergency_care'),
        ('Musculoskeletal Exam', 'musculoskeletal_exam'),
        ('Non-Musculoskeletal', 'non_musculoskeletal_exam'),
        ('Taping/Bracing', 'taping_bracing'),
        ('Rehabilitation', 'rehabilitation_reconditioning'),
        ('Modalities', 'modalities'),
        ('Pharmacology', 'pharmacology'),
        ('Injury Prevention', 'injury_illness_prevention'),
        ('Non-Sport Patient', 'non_sport_patient'),
    ]
    
    # Build heat map matrix: rows=categories, cols=sports
    heatmap_data = []
    max_value = 0
    for cat_label, cat_field in categories:
        row = {'category': cat_label, 'values': []}
        for sport in all_sports:
            total = heatmap_reports.filter(sport=sport).aggregate(
                val=Sum(cat_field)
            )['val'] or 0
            row['values'].append(total)
            if total > max_value:
                max_value = total
        heatmap_data.append(row)
    
    # Get filter options
    semesters = ClinicReport.objects.values_list('semester', flat=True).distinct().exclude(semester__isnull=True).order_by('-semester')
    sports = Sport.objects.filter(clinicreport__isnull=False).distinct().values_list('name', flat=True).order_by('name')
    
    context = {
        # Filters
        'selected_sport': selected_sport,
        'selected_semester': selected_semester,
        'semesters': sorted(set(semesters)),
        'sports': sorted(set(sports)),
        
        # Pie chart
        'pie_chart_data': pie_chart_data,
        'pie_total_patients': sum(item['value'] for item in pie_chart_data),
        
        # Heat map
        'heatmap_categories': [c[0] for c in categories],
        'heatmap_sports': list(all_sports.values_list('name', flat=True)),
        'heatmap_matrix': heatmap_data,
        'heatmap_max': max_value if max_value > 0 else 1,  # Avoid division by zero
    }
    
    return render(request, 'core/faculty_dashboard.html', context)
@login_required
def student_dashboard_view(request):
    """Render the student dashboard."""
    return render(request, 'core/student_dashboard.html')

def home_view(request):
    """Render the homepage."""
    from django.conf import settings
    context = {'login_url': settings.LOGIN_URL}
    return render(request, 'core/home.html', context)

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
