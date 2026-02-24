from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.http import HttpResponseBadRequest
import json
from .models import ClinicReport
from .models import Sport, HealthcareProvider

# Security note: Student form submissions require authentication because we want to protect against DDoS attacks.
# This way, only verified students and faculty can submit the form and create new traffic to the database.
@login_required
def form_view(request):
    """Render the clinic report form. Requires an authenticated user."""
    sports = Sport.objects.filter(active=True).values('id', 'name')
    healthcare_providers = HealthcareProvider.objects.filter(active=True).values('id', 'name')
    context = {'sports': sports, 'healthcare_providers': healthcare_providers}
    return render(request, 'clinic_reports/form.html', context)


@csrf_exempt # TODO: Remove this and use CSRF tokens to tighten security before launching in production!
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
        required_fields = [
            'first_name', 'last_name', 'email', 'sport',
            'immediate_emergency_care', 'musculoskeletal_exam', 'non_musculoskeletal_exam',
            'taping_bracing', 'rehabilitation_reconditioning', 'modalities',
            'pharmacology', 'injury_illness_prevention', 'non_sport_patient', 'interacted_hcps'
        ]
        missing = [f for f in required_fields if data.get(f) is None]
        if missing:
            return JsonResponse({'success': False, 'error': f'Missing required fields: {", ".join(missing)}'}, status=400)
        
        # Validate healthcare_provider if interacted_hcps is True
        interacted = data.get('interacted_hcps')
        try:
            interacted_bool = bool(int(interacted))
        except (TypeError, ValueError):
            interacted_bool = str(interacted).strip().lower() in {"1", "true", "True", "yes", "Yes", "y", "Y"}
        
        if interacted_bool and not data.get('healthcare_provider'):
            return JsonResponse({'success': False, 'error': 'Healthcare provider is required when you interacted with other healthcare professionals'}, status=400)

        # Email validation
        try:
            validate_email(data['email'])
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email address'}, status=400)

        sport_id = data.get('sport')
        try:
            sport = Sport.objects.get(id=sport_id, active=True)
        except Sport.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid sport selection'}, status=400)
        
        # Get healthcare provider if specified
        healthcare_provider = None
        if interacted_bool:
            provider_id = data.get('healthcare_provider')
            try:
                healthcare_provider = HealthcareProvider.objects.get(id=provider_id, active=True)
            except HealthcareProvider.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Invalid healthcare provider selection'}, status=400)

        report = ClinicReport.objects.create(
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
            email=data.get('email'),
            sport=sport,
            immediate_emergency_care=int(data.get('immediate_emergency_care', 0)),
            musculoskeletal_exam=int(data.get('musculoskeletal_exam', 0)),
            non_musculoskeletal_exam=int(data.get('non_musculoskeletal_exam', 0)),
            taping_bracing=int(data.get('taping_bracing', 0)),
            rehabilitation_reconditioning=int(data.get('rehabilitation_reconditioning', 0)),
            modalities=int(data.get('modalities', 0)),
            pharmacology=int(data.get('pharmacology', 0)),
            injury_illness_prevention=int(data.get('injury_illness_prevention', 0)),
            non_sport_patient=int(data.get('non_sport_patient', 0)),
            interacted_hcps=interacted_bool,
            healthcare_provider=healthcare_provider
        )
        return JsonResponse({'success': True, 'id': report.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
