from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from .models import ClinicReport

# Security note: Student form submissions require authentication because we want to protect against DDoS attacks.
# This way, only verified students and faculty can submit the form and create new traffic to the database.
@login_required
def form_view(request):
    """Render the clinic report form. Requires an authenticated user."""
    return render(request, 'clinic_reports/form.html')


@csrf_exempt # TODO: Update this to tighten security before launching in production!
@require_http_methods(["POST"])
def submit_report(request):
    """API endpoint to submit clinic report.

    This endpoint requires the user to be authenticated. For Ajax POSTs from
    the form we return a JSON 401 when unauthenticated instead of a redirect
    so the frontend can handle it cleanly.
    """
    if not request.user.is_authenticated:
        # Throw a 401 Forbidden error if user is not logged in
        return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)

    try:
        data = json.loads(request.body)
        report = ClinicReport.objects.create(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            clinical_site=data.get('clinical_site'),
            sport=data.get('sport'),
            immediate_emergency_care=int(data.get('immediate_emergency_care', 0)),
            musculoskeletal_exam=int(data.get('musculoskeletal_exam', 0)),
            non_musculoskeletal_exam=int(data.get('non_musculoskeletal_exam', 0)),
            taping_bracing=int(data.get('taping_bracing', 0)),
            rehabilitation_reconditioning=int(data.get('rehabilitation_reconditioning', 0)),
            modalities=int(data.get('modalities', 0)),
            pharmacology=int(data.get('pharmacology', 0)),
            injury_illness_prevention=int(data.get('injury_illness_prevention', 0)),
            non_sport_patient=int(data.get('non_sport_patient', 0)),
        )
        return JsonResponse({'success': True, 'id': report.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
