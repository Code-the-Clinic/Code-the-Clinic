from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, F, Case, When, IntegerField, Value, FloatField
from django.db.models.functions import Coalesce, ExtractYear
from django.core.exceptions import PermissionDenied
from openpyxl import Workbook
from datetime import datetime
import json
import logging
import re
from clinic_reports.models import ClinicReport, Sport

logger = logging.getLogger(__name__)

# Security note: Viewing the faculty dashboard requires authentication
@login_required
def faculty_dashboard_view(request):
    """Faculty dashboard with heat map and pie chart.

    Filters are now accepted via POST as well as GET so that
    sensitive values (e.g. student names/emails) do not appear
    in the URL query string when dropdowns change.
    """
    if not request.user.is_staff:
        raise PermissionDenied("You don't have permission to access this page.")

    # Use POST for filters when available to avoid leaking them into the URL
    params = request.GET if request.method == 'GET' else request.POST

    # Get filter values
    selected_sport = params.get('sport')
    selected_student = params.get('student')
    selected_semester_raw = params.get('semester')
    selected_week = params.get('week')

    # Get filters for the 2nd pie chart
    care_category = params.get('care_category', 'immediate_emergency_care')
    selected_semester_raw2 = params.get('semester2')
    selected_week2 = params.get('week2')
    selected_student2 = params.get('student_filter2')
    
    # Parse selected semester for pie chart 1
    selected_semester_base = selected_semester_raw
    selected_year = None
    if selected_semester_raw and " '" in selected_semester_raw:
        parts = selected_semester_raw.split(" '")
        if len(parts) == 2 and parts[1].isdigit():
            selected_semester_base = parts[0]
            selected_year = 2000 + int(parts[1])
            
    # Parse selected semester for pie chart 2
    selected_semester_base2 = selected_semester_raw2
    selected_year2 = None
    if selected_semester_raw2 and " '" in selected_semester_raw2:
        parts = selected_semester_raw2.split(" '")
        if len(parts) == 2 and parts[1].isdigit():
            selected_semester_base2 = parts[0]
            selected_year2 = 2000 + int(parts[1])
            
    # Base queryset for pie chart (filtered by both)
    pie_reports = ClinicReport.objects.all()
    if selected_semester_base:
        pie_reports = pie_reports.filter(semester=selected_semester_base)
    if selected_year:
        pie_reports = pie_reports.filter(created_at__year=selected_year)
    if selected_sport:
        pie_reports = pie_reports.filter(sport__name=selected_sport)
    if selected_student and selected_student != 'All Students':
        # Extract email from "First Last (email@example.com)" format
        import re
        email_match = re.search(r'\(([^)]+)\)$', selected_student)
        email_to_filter = email_match.group(1) if email_match else selected_student
        pie_reports = pie_reports.filter(email=email_to_filter)
    if selected_week:
        pie_reports = pie_reports.filter(week=selected_week)
    
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
            
    # Base queryset for 2nd pie chart
    pie_reports2 = ClinicReport.objects.all()
    if selected_semester_base2:
        pie_reports2 = pie_reports2.filter(semester=selected_semester_base2)
    if selected_year2:
        pie_reports2 = pie_reports2.filter(created_at__year=selected_year2)
    if selected_student2 and selected_student2 != 'All Students':
        import re
        email_match2 = re.search(r'\(([^)]+)\)$', selected_student2)
        email_to_filter2 = email_match2.group(1) if email_match2 else selected_student2
        pie_reports2 = pie_reports2.filter(email=email_to_filter2)
    if selected_week2:
        pie_reports2 = pie_reports2.filter(week=selected_week2)
        
    # Calculate pie chart 2 totals grouped by sport
    # The selected care_category provides the field name, e.g., 'immediate_emergency_care'
    valid_care_categories = [
        'immediate_emergency_care', 'musculoskeletal_exam', 'non_musculoskeletal_exam', 
        'taping_bracing', 'rehabilitation_reconditioning', 'modalities', 
        'pharmacology', 'injury_illness_prevention', 'non_sport_patient'
    ]
    if care_category not in valid_care_categories:
        care_category = 'immediate_emergency_care'
        
    sport_totals = pie_reports2.values('sport__name').annotate(
        total=Sum(care_category)
    ).order_by('-total')
    
    pie_chart_data2 = []
    for sport_data in sport_totals:
        value = sport_data['total']
        if value is not None and value > 0:
            pie_chart_data2.append({
                'label': sport_data['sport__name'] or 'Unknown',
                'value': value
            })
    
    # Key Metrics (Summary Statistics)
    metric_student = params.get('metric_student')
    metric_semester_raw = params.get('metric_semester')
    
    metric_reports = ClinicReport.objects.all()
    
    if metric_semester_raw:
        if " '" in metric_semester_raw:
            parts = metric_semester_raw.split(" '")
            if len(parts) == 2 and parts[1].isdigit():
                sem_base = parts[0]
                yr_base = 2000 + int(parts[1])
                metric_reports = metric_reports.filter(semester=sem_base, created_at__year=yr_base)
        else:
            metric_reports = metric_reports.filter(semester=metric_semester_raw)
            
    if metric_student and metric_student != 'All Students':
        import re
        email_match = re.search(r'\(([^)]+)\)$', metric_student)
        email_to_filter = email_match.group(1) if email_match else metric_student
        metric_reports = metric_reports.filter(email=email_to_filter)
        
    all_care_fields = [
        'immediate_emergency_care', 'musculoskeletal_exam', 'non_musculoskeletal_exam', 
        'taping_bracing', 'rehabilitation_reconditioning', 'modalities', 
        'pharmacology', 'injury_illness_prevention', 'non_sport_patient'
    ]
    
    total_experiences = 0
    sums = metric_reports.aggregate(*[Sum(f) for f in all_care_fields])
    care_type_totals = {}
    for f in all_care_fields:
        val = sums[f'{f}__sum'] or 0
        total_experiences += val
        care_type_totals[f] = val
        
    active_students_count = metric_reports.values('email').distinct().count()
    
    avg_per_student = round(total_experiences / active_students_count, 1) if active_students_count > 0 else 0
    
    # Most Common Care Type
    most_common_care_type = "N/A"
    most_common_care_val = 0
    care_labels = {
        'immediate_emergency_care': 'Immediate / Emergency',
        'musculoskeletal_exam': 'Musculoskeletal Exam',
        'non_musculoskeletal_exam': 'Non-Musculoskeletal',
        'taping_bracing': 'Taping & Bracing',
        'rehabilitation_reconditioning': 'Rehabilitation',
        'modalities': 'Modalities',
        'pharmacology': 'Pharmacology',
        'injury_illness_prevention': 'Injury Prevention',
        'non_sport_patient': 'Non-Sport Patient'
    }
    for k, v in care_type_totals.items():
        if v > most_common_care_val:
            most_common_care_val = v
            most_common_care_type = care_labels.get(k, k)
            
    # Most Active Sport
    sport_stats = metric_reports.values('sport__name').annotate(
        total_care=sum(Sum(f) for f in all_care_fields)
    ).order_by('-total_care')
    
    most_active_sport = sport_stats.first()['sport__name'] if sport_stats and sport_stats.first()['total_care'] else "N/A"
    
    total_reports = metric_reports.count()
    
    # Get filter options
    semester_year_pairs = ClinicReport.objects.annotate(
        year=ExtractYear('created_at')
    ).values_list('semester', 'year').distinct().exclude(semester__isnull=True)
    
    formatted_semesters = []
    for sem, year in semester_year_pairs:
        if sem and year:
            short_year = str(year)[-2:]
            formatted_semesters.append(f"{sem} '{short_year}")
            
    sports = Sport.objects.filter(clinicreport__isnull=False).distinct().values_list('name', flat=True).order_by('name')
    
    # Dynamic weeks based on existing reports
    actual_weeks = ClinicReport.objects.values_list('week', flat=True).distinct().exclude(week__isnull=True).order_by('week')
    
    # Get all students for the dropdown
    students_query = ClinicReport.objects.values('first_name', 'last_name', 'email').distinct().order_by('last_name', 'first_name')
    students = [{'display': f"{s['first_name']} {s['last_name']} ({s['email']})", 'email': s['email']} for s in students_query]
    
    # Trend Chart Data
    selected_trend_sport = params.get('trend_sport')
    selected_trend_care = params.get('trend_care')
    selected_trend_student = params.get('trend_student')
    selected_trend_semester = params.get('trend_semester')
    
    trend_reports = ClinicReport.objects.all()
    if selected_trend_semester:
        if " '" in selected_trend_semester:
            parts = selected_trend_semester.split(" '")
            if len(parts) == 2 and parts[1].isdigit():
                sem_base = parts[0]
                yr_base = 2000 + int(parts[1])
                trend_reports = trend_reports.filter(semester=sem_base, created_at__year=yr_base)
        else:
            trend_reports = trend_reports.filter(semester=selected_trend_semester)
            
    if selected_trend_student and selected_trend_student != 'All Students':
        import re
        email_match = re.search(r'\(([^)]+)\)$', selected_trend_student)
        email_to_filter = email_match.group(1) if email_match else selected_trend_student
        trend_reports = trend_reports.filter(email=email_to_filter)
        
    all_care_fields = [
        'immediate_emergency_care', 'musculoskeletal_exam', 'non_musculoskeletal_exam', 
        'taping_bracing', 'rehabilitation_reconditioning', 'modalities', 
        'pharmacology', 'injury_illness_prevention', 'non_sport_patient'
    ]
    if selected_trend_care and selected_trend_care != 'all':
        care_fields = [selected_trend_care]
    else:
        care_fields = all_care_fields

    if selected_trend_sport and selected_trend_sport != 'all':
        trend_sports = [selected_trend_sport]
    else:
        trend_sports = list(Sport.objects.filter(clinicreport__isnull=False).distinct().values_list('name', flat=True))

    weeks = list(range(1, 17))
    trend_datasets = []
    
    colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#C9CBCF', '#7BC225', '#E74C3C', '#2ecc71', '#34495e']
    
    for i, sport_name in enumerate(trend_sports):
        sport_reports = trend_reports.filter(sport__name=sport_name)
        data = []
        for w in weeks:
            week_reports = sport_reports.filter(week=w)
            if week_reports.exists():
                week_sum = 0
                sums = week_reports.aggregate(*[Sum(f) for f in care_fields])
                for f in care_fields:
                    val = sums[f'{f}__sum']
                    if val:
                        week_sum += val
                data.append(week_sum)
            else:
                data.append(0)
                
        if any(data):
            trend_datasets.append({
                'label': sport_name,
                'data': data,
                'borderColor': colors[i % len(colors)],
                'tension': 0.3,
                'fill': False
            })

    # Calculate Total Interactions across all matching trend_reports
    total_data = []
    for w in weeks:
        week_reports = trend_reports.filter(sport__name__in=trend_sports, week=w)
        if week_reports.exists():
            week_sum = 0
            sums = week_reports.aggregate(*[Sum(f) for f in care_fields])
            for f in care_fields:
                val = sums[f'{f}__sum']
                if val:
                    week_sum += val
            total_data.append(week_sum)
        else:
            total_data.append(0)

    # Only add total line if there are multiple sports or we explicitly want to show it.
    # Actually, always showing it is fine, but if it covers exactly the single sport selected,
    # it might be redundant. Let's just include it if it has data.
    if any(total_data):
        trend_datasets.append({
            'label': 'Total Patient Encounters',
            'data': total_data,
            'borderColor': '#000000',
            'borderDash': [5, 5],
            'borderWidth': 3,
            'tension': 0.3,
            'fill': False
        })

    context = {
        # Filters
        'selected_sport': selected_sport,
        'selected_student': selected_student,
        'selected_semester': selected_semester_raw,
        'selected_week': selected_week,
        'semesters': sorted(set(formatted_semesters), reverse=True),
        'sports': sorted(set(sports)),
        'students': students,
        
        # Pie chart
        'pie_chart_data': pie_chart_data,
        'pie_total_patients': sum(item['value'] for item in pie_chart_data),
        
        # Pie chart 2
        'pie_chart_data2': pie_chart_data2,

        'weeks_list': list(actual_weeks),
        
        # Key Metrics
        'metric_total_experiences': total_experiences,
        'metric_active_students': active_students_count,
        'metric_avg_per_student': avg_per_student,
        'metric_most_common_care': most_common_care_type,
        'metric_most_active_sport': most_active_sport,
        'metric_total_reports': total_reports,
        'selected_metric_student': metric_student,
        'selected_metric_semester': metric_semester_raw,
        
        # Trend chart
        'trend_datasets': trend_datasets,
        'selected_trend_sport': selected_trend_sport,
        'selected_trend_care': selected_trend_care,
        'selected_trend_student': selected_trend_student,
        'selected_trend_semester': selected_trend_semester,

        # Additional selected values used to preserve filters across forms
        'care_category': care_category,
        'selected_semester2': selected_semester_raw2,
        'selected_week2': selected_week2,
        'selected_student2': selected_student2,
    }
    
    return render(request, 'core/faculty_dashboard.html', context)
@login_required
def student_dashboard_view(request):
    """Render the student dashboard."""
    # Build semester options in the same way as the faculty dashboard
    semester_year_pairs = ClinicReport.objects.annotate(
        year=ExtractYear('created_at')
    ).values_list('semester', 'year').distinct().exclude(semester__isnull=True)

    formatted_semesters = []
    for sem, year in semester_year_pairs:
        if sem and year:
            short_year = str(year)[-2:]
            formatted_semesters.append(f"{sem} '{short_year}")

    context = {
        'weeks': range(1, 17),  # Weeks 1-16
        'semesters': sorted(set(formatted_semesters), reverse=True),
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

    semester_val = filters.get('semester')
    if semester_val:
        if " '" in semester_val:
            parts = semester_val.split(" '")
            if len(parts) == 2 and parts[1].isdigit():
                semester_base = parts[0]
                year_val = 2000 + int(parts[1])
                clinic_reports = clinic_reports.filter(semester=semester_base, created_at__year=year_val)
            else:
                clinic_reports = clinic_reports.filter(semester=semester_val)
        else:
            clinic_reports = clinic_reports.filter(semester=semester_val)

    if filters.get('week'):
        clinic_reports = clinic_reports.filter(week=filters.get('week'))

    if filters.get('year') is not None:
        try:
            year_value = int(filters.get('year'))
        except (TypeError, ValueError):
            raise ValueError('Invalid year. Expected numeric year (e.g., 2026).')
        clinic_reports = clinic_reports.filter(created_at__year=year_value)

    return clinic_reports


def _extract_email_from_student_value(student_value):
    if not student_value or student_value == 'All Students':
        return None
    email_match = re.search(r'\(([^)]+)\)$', student_value)
    return email_match.group(1) if email_match else student_value


def _first_non_empty(values):
    for value in values:
        if value not in (None, ''):
            return value
    return None


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


@require_http_methods(["GET"])
@login_required
def export_dashboard_excel(request):
    """Export filtered raw dashboard ClinicReport data as an Excel file."""
    if not request.user.is_staff:
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        selected_sport = _first_non_empty([
            request.GET.get('sport'),
            request.GET.get('trend_sport') if request.GET.get('trend_sport') != 'all' else None,
        ])
        selected_semester = _first_non_empty([
            request.GET.get('semester'),
            request.GET.get('semester2'),
            request.GET.get('metric_semester'),
            request.GET.get('trend_semester'),
        ])
        selected_week = _first_non_empty([
            request.GET.get('week'),
            request.GET.get('week2'),
        ])
        selected_year = request.GET.get('year')
        selected_student = _first_non_empty([
            request.GET.get('student'),
            request.GET.get('student_filter2'),
            request.GET.get('metric_student'),
            request.GET.get('trend_student'),
        ])

        filters = {
            'sport': selected_sport,
            'semester': selected_semester,
            'week': selected_week,
            'year': selected_year,
        }

        clinic_reports = ClinicReport.objects.select_related('sport', 'healthcare_provider').all()
        clinic_reports = _apply_dashboard_filters(clinic_reports, filters)

        email_to_filter = _extract_email_from_student_value(selected_student)
        if email_to_filter:
            clinic_reports = clinic_reports.filter(email=email_to_filter)

        clinic_reports = clinic_reports.order_by('id')

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'clinic_reports_raw'

        headers = [
            'id',
            'created_at_utc',
            'first_name',
            'last_name',
            'email',
            'sport',
            'semester',
            'week',
            'immediate_emergency_care',
            'musculoskeletal_exam',
            'non_musculoskeletal_exam',
            'taping_bracing',
            'rehabilitation_reconditioning',
            'modalities',
            'pharmacology',
            'injury_illness_prevention',
            'non_sport_patient',
            'interacted_hcps',
            'healthcare_provider',
            'total_experiences',
        ]
        sheet.append(headers)

        for report in clinic_reports.iterator():
            total_experiences = (
                (report.immediate_emergency_care or 0)
                + (report.musculoskeletal_exam or 0)
                + (report.non_musculoskeletal_exam or 0)
                + (report.taping_bracing or 0)
                + (report.rehabilitation_reconditioning or 0)
                + (report.modalities or 0)
                + (report.pharmacology or 0)
                + (report.injury_illness_prevention or 0)
                + (report.non_sport_patient or 0)
            )

            sheet.append([
                report.id,
                report.created_at.isoformat() if report.created_at else '',
                report.first_name,
                report.last_name,
                report.email,
                report.sport.name if report.sport else '',
                report.semester,
                report.week,
                report.immediate_emergency_care,
                report.musculoskeletal_exam,
                report.non_musculoskeletal_exam,
                report.taping_bracing,
                report.rehabilitation_reconditioning,
                report.modalities,
                report.pharmacology,
                report.injury_illness_prevention,
                report.non_sport_patient,
                report.interacted_hcps,
                report.healthcare_provider.name if report.healthcare_provider else '',
                total_experiences,
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        response['Content-Disposition'] = f'attachment; filename="dashboard_raw_{timestamp}.xlsx"'
        workbook.save(response)
        return response
    except ValueError as e:
        logger.error(f"Dashboard export validation error: {e}")
        return JsonResponse({'success': False, 'error': 'Invalid filter parameters'}, status=400)
    except Exception as e:
        logger.error(f"Dashboard export error: {e}")
        return JsonResponse({'success': False, 'error': 'Failed to export dashboard data'}, status=500)

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
