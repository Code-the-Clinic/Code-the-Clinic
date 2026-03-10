from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, F, Case, When, IntegerField, Value, FloatField
from django.db.models.functions import Coalesce
from django.core.exceptions import PermissionDenied
import json
import logging
from clinic_reports.models import ClinicReport, Sport

logger = logging.getLogger(__name__)

# Security note: Viewing the faculty dashboard requires authentication
@login_required
def faculty_dashboard_view(request):
    """Faculty dashboard with heat map and pie chart"""
    if not request.user.is_staff:
        raise PermissionDenied("You don't have permission to access this page.")
    
    # Get filter values
    selected_sport = request.GET.get('sport')
    selected_semester = request.GET.get('semester')
    selected_time_filter = request.GET.get('time_filter')  # ADD THIS
    selected_week = request.GET.get('week')
    
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

        'weeks_list': range(1, 17),  # Weeks 1-16
        
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
    context = {
        'weeks': range(1, 17)  # Weeks 1-16
    }
    return render(request, 'core/student_dashboard.html', context)

def home_view(request):
    """Render the homepage."""
    from django.conf import settings
    context = {'login_url': settings.LOGIN_URL}
    return render(request, 'core/home.html', context)


def _apply_dashboard_filters(clinic_reports, filters):
    """Apply common dashboard filters to a ClinicReport queryset."""
    if filters.get('sport'):
        clinic_reports = clinic_reports.filter(sport__name=filters.get('sport'))

    if filters.get('semester'):
        clinic_reports = clinic_reports.filter(semester=filters.get('semester'))

    if filters.get('week'):
        clinic_reports = clinic_reports.filter(week=filters.get('week'))

    if filters.get('year') is not None:
        try:
            year_value = int(filters.get('year'))
        except (TypeError, ValueError):
            raise ValueError('Invalid year. Expected numeric year (e.g., 2026).')
        clinic_reports = clinic_reports.filter(created_at__year=year_value)

    return clinic_reports


def _build_dashboard_payload(clinic_reports):
    """Build shared dashboard response payload for pie charts and summary metrics."""
    # Calculate average patient load per report (submission/week)
    average_patients_per_week = clinic_reports.annotate(
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
        average=Coalesce(
            Avg('weekly_total_patients'),
            Value(0.0),
            output_field=FloatField()
        )
    )['average']

    # Calculate pie chart totals
    pie_totals = clinic_reports.aggregate(
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

    return {
        'success': True,
        'pie_chart_data': pie_chart_data,
        'total_patients': sum(item['value'] for item in pie_chart_data),
        'average_patients_per_week': average_patients_per_week,
    }

@require_http_methods(["POST"])
@login_required
def fetch_data(request):
    """API endpoint to fetch pie chart data for faculty dashboard
    
    Accepts JSON payload with filters:
    - sport: filter by sport name (optional)
    - semester: filter by semester (optional)
    - week: filter by week number (optional)
    - year: filter by year (optional)
    
    Authorization:
    - Non-staff users cannot use this endpoint
    - Staff users can filter by any combination of parameters
    """
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    try:
        filters = json.loads(request.body)
        clinic_reports = ClinicReport.objects.all()
        clinic_reports = _apply_dashboard_filters(clinic_reports, filters)
        return JsonResponse(_build_dashboard_payload(clinic_reports))
    
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        logger.error(f"Dashboard data fetch validation error: {e}")
        return JsonResponse({'success': False, 'error': 'Invalid filter parameters'}, status=400)
    except Exception as e:
        logger.error(f"Dashboard data fetch error: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to fetch dashboard data'}, status=500)


@require_http_methods(["POST"])
@login_required
def fetch_student_data(request):
    """API endpoint for student dashboard data (self-only)."""
    if request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Use the faculty endpoint for staff requests.'}, status=403)

    try:
        filters = json.loads(request.body)
        clinic_reports = ClinicReport.objects.filter(email=request.user.email)
        clinic_reports = _apply_dashboard_filters(clinic_reports, filters)
        return JsonResponse(_build_dashboard_payload(clinic_reports))

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except ValueError as e:
        logger.warning(f"Student data fetch validation error: {e}")
        return JsonResponse({'success': False, 'error': 'Invalid filter parameters'}, status=400)
    except Exception as e:
        logger.error(f"Student data fetch error: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to fetch student data'}, status=500)
