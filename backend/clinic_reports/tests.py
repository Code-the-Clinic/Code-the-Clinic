from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.urls import reverse
import json
from clinic_reports.models import ClinicReport, Sport, HealthcareProvider

User = get_user_model() # Gets whatever Django user model we are using (the built in one or a custom one)


class ClinicReportViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Run once for the entire test class"""
        cls.football, _ = Sport.objects.get_or_create(name='Football', defaults={'active': True})
        cls.inactive, _ = Sport.objects.get_or_create(name='Inactive', active=False)
        cls.physician, _ = HealthcareProvider.objects.get_or_create(name='Physician (MD/DO)', defaults={'active': True})
        cls.physical_therapist, _ = HealthcareProvider.objects.get_or_create(name='Physical Therapist (PT)', defaults={'active': True})
        cls.inactive_provider, _ = HealthcareProvider.objects.get_or_create(name='Inactive Provider', active=False)

    def setUp(self):
        """Run before each test method"""
        self.client = Client()
        self.url = reverse('form')
        self.submit_url = reverse('submit_report')
        self.user = User.objects.create_user(username='tester', email='tester@university.edu', password='pass')
        self.user.first_name = 'Alice'
        self.user.last_name = 'Example'
        self.user.save()

        # Create dummy data for the form
        self.payload = {
            'first_name': 'Alice',  # Ignored by view; kept for backward-compat payload shape
            'last_name': 'Example', # Ignored by view
            'sport': self.football.id,  # Form submissions use sport ID as json value
            'week': 5,
            'immediate_emergency_care': 1,
            'musculoskeletal_exam': 2,
            'non_musculoskeletal_exam': 0,
            'taping_bracing': 0,
            'rehabilitation_reconditioning': 0,
            'modalities': 0,
            'pharmacology': 0,
            'injury_illness_prevention': 0,
            'non_sport_patient': 0,
            'interacted_hcps': 0,
        }

        # Payload with healthcare provider interaction
        self.payload_with_hcp = {
            'first_name': 'Bob',    # Ignored by view
            'last_name': 'Student', # Ignored by view
            'sport': self.football.id,
            'week': 3,
            'immediate_emergency_care': 0,
            'musculoskeletal_exam': 1,
            'non_musculoskeletal_exam': 0,
            'taping_bracing': 0,
            'rehabilitation_reconditioning': 1,
            'modalities': 0,
            'pharmacology': 0,
            'injury_illness_prevention': 0,
            'non_sport_patient': 0,
            'interacted_hcps': 1,
            'healthcare_provider': self.physician.id,
        }

    def test_data_retrieval(self):
        """Persist a submitted report and read it back correctly."""
        self.client.force_login(self.user)
        self.client.post(self.submit_url, data=json.dumps(self.payload), content_type='application/json')
        report = ClinicReport.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.first_name, self.user.first_name)
        self.assertEqual(report.sport, self.football)  # Compare with Sport object

    def test_invalid_email(self):
        """Reject submissions when the authenticated user's email is invalid."""
        self.client.force_login(self.user)
        # Invalid email on the authenticated user account should cause failure
        self.user.email = 'not-an-email'
        self.user.save()
        bad_payload = self.payload.copy()
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_payload_email_is_ignored(self):
        """Email in the JSON payload should be ignored and the user's email used instead."""
        self.client.force_login(self.user)
        payload = self.payload.copy()
        payload['email'] = 'someoneelse@university.edu'

        resp = self.client.post(self.submit_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ClinicReport.objects.count(), 1)

        report = ClinicReport.objects.first()
        self.assertEqual(report.email, self.user.email)
        self.assertNotEqual(report.email, 'someoneelse@university.edu')

    def test_payload_name_is_ignored(self):
        """First and last name in the payload should be ignored in favor of the user's name."""
        self.client.force_login(self.user)
        payload = self.payload.copy()
        payload['first_name'] = "Robert'); DROP TABLE clinic_reports_clinicreport;--"
        payload['last_name'] = "EvilTester'); DROP TABLE clinic_reports_clinicreport;--"

        resp = self.client.post(self.submit_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ClinicReport.objects.count(), 1)

        report = ClinicReport.objects.first()
        self.assertEqual(report.first_name, self.user.first_name)
        self.assertEqual(report.last_name, self.user.last_name)
        self.assertNotIn('DROP TABLE', report.first_name)
        self.assertNotIn('DROP TABLE', report.last_name)

    def test_missing_required_field(self):
        """Fail validation when a required field (such as sport) is missing."""
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        del bad_payload['sport']
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_sql_injection_attempt(self):
        """Attempt SQL injection through a numeric, user-editable field.

        This simulates a student typing a malicious string into a count field.
        The view should reject the input and not create any records, and
        Django's ORM should prevent any SQL being executed beyond the
        parameterized query.
        """
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        bad_payload['immediate_emergency_care'] = "1; DROP TABLE clinic_reports_clinicreport;--"

        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        # The view should fail validation when casting to int
        self.assertNotEqual(resp.status_code, 200)
        # No reports should be created and the table should still be intact
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_xss_injection(self):
        """Ensure payload HTML in name fields is ignored to avoid XSS."""
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        bad_payload['last_name'] = '<script>alert(1)</script>'
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        report = ClinicReport.objects.get(first_name='Alice')
        # Last name should come from user object, not payload, so script tag is ignored
        self.assertEqual(report.last_name, self.user.last_name)

    @override_settings(LOGIN_URL='/accounts/microsoft/login/') # Simulate production situation (Azure credentials are available, so redirect to microsoft login) in test env
    def test_no_form_if_not_authenticated(self):
        """Redirect unauthenticated users to the configured login URL."""
        # Use reverse to avoid hardcoding URLs
        resp = self.client.get(self.url)
        # Check that the site redirects unauthenticated users to the login page
        # if they try to access the form
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/microsoft/login/', resp['Location'])

    def test_form_view_allows_authenticated(self):
        """Allow authenticated users to access and render the clinic report form."""
        self.client.force_login(self.user) # This simulates logging in the user
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # Check that the submit button exists (this proves we are in the form view)
        self.assertContains(resp, "Submit Report")  

    def test_submit_requires_auth(self):
        """Return a 401 JSON response when an unauthenticated user submits the form."""
        # Unauthenticated users shouldn't be able to submit the form
        resp = self.client.post(self.submit_url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(resp.status_code, 401)
        body = json.loads(resp.content)
        # Check that success is false and error message is correct
        self.assertFalse(body.get('success'))
        self.assertIn("Authentication required", body.get('error', ''))
        self.assertEqual(ClinicReport.objects.count(), 0)
    
    def test_submit_creates_report_when_authenticated(self):
        """Create a ClinicReport record when an authenticated user submits valid data."""
        self.client.force_login(self.user)
        resp = self.client.post(self.submit_url, data=json.dumps(self.payload), content_type='application/json')
        # the view returns JsonResponse with success True
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertTrue(body.get('success')) # Checks that the form sent back a "success" message
        self.assertEqual(ClinicReport.objects.count(), 1) # Checks new record added to DB

    def test_multiple_payload_emails_use_user_email(self):
        """Even with different payload emails, stored email is always the user's email."""
        self.client.force_login(self.user)

        payload1 = self.payload.copy()
        payload1['email'] = 'first@university.edu'
        payload2 = self.payload.copy()
        payload2['email'] = 'second@university.edu'

        resp1 = self.client.post(self.submit_url, data=json.dumps(payload1), content_type='application/json')
        resp2 = self.client.post(self.submit_url, data=json.dumps(payload2), content_type='application/json')
        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)

        self.assertEqual(ClinicReport.objects.count(), 2)
        for report in ClinicReport.objects.all():
            self.assertEqual(report.email, self.user.email)

    def test_form_shows_only_active_sports(self):
        """Form should only display sports with active=True"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        # Football and Inactive objects were created at the beginning
        # but only Football should show up in the response
        self.assertContains(response, 'Football')
        self.assertNotContains(response, 'Inactive')

    def test_submit_with_invalid_sport_id(self):
        """Submitting with non-existent sport ID should fail"""
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        bad_payload['sport'] = 99999  # Non-existent ID
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_submit_with_inactive_sport(self):
        """Submitting with inactive sport ID should fail"""
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        bad_payload['sport'] = self.inactive.id
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_healthcare_provider_str(self):
        """Test string representation of HealthcareProvider"""
        self.assertEqual(str(self.physician), 'Physician (MD/DO)')

    def test_submit_with_healthcare_provider(self):
        """Successfully submit a report with healthcare provider interaction"""
        self.client.force_login(self.user)
        resp = self.client.post(self.submit_url, data=json.dumps(self.payload_with_hcp), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertTrue(body.get('success'))
        
        report = ClinicReport.objects.get(email=self.user.email)
        self.assertIsNotNone(report)
        self.assertTrue(report.interacted_hcps)
        self.assertEqual(report.healthcare_provider, self.physician)

    def test_submit_without_healthcare_provider(self):
        """Successfully submit a report without healthcare provider interaction"""
        self.client.force_login(self.user)
        payload_no_hcp = self.payload.copy()
        payload_no_hcp['interacted_hcps'] = 0
        resp = self.client.post(self.submit_url, data=json.dumps(payload_no_hcp), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertTrue(body.get('success'))
        
        report = ClinicReport.objects.get(email=self.user.email)
        self.assertIsNotNone(report)
        self.assertFalse(report.interacted_hcps)
        self.assertIsNone(report.healthcare_provider)

    def test_interacted_hcps_true_requires_provider(self):
        """When interacted_hcps is True, healthcare_provider is required"""
        self.client.force_login(self.user)
        bad_payload = self.payload_with_hcp.copy()
        del bad_payload['healthcare_provider']  # Remove healthcare_provider
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertFalse(body.get('success'))
        self.assertIn('Healthcare provider is required', body.get('error', ''))
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_submit_with_invalid_provider_id(self):
        """Submitting with non-existent healthcare provider ID should fail"""
        self.client.force_login(self.user)
        bad_payload = self.payload_with_hcp.copy()
        bad_payload['healthcare_provider'] = 99999  # Non-existent ID
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertFalse(body.get('success'))
        self.assertIn('Invalid healthcare provider', body.get('error', ''))
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_submit_with_inactive_provider(self):
        """Submitting with inactive healthcare provider ID should fail"""
        self.client.force_login(self.user)
        bad_payload = self.payload_with_hcp.copy()
        bad_payload['healthcare_provider'] = self.inactive_provider.id
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.content)
        self.assertFalse(body.get('success'))
        self.assertIn('Invalid healthcare provider', body.get('error', ''))
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_form_shows_only_active_providers(self):
        """Form should only display healthcare providers with active=True"""
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        # Check active providers are shown
        self.assertContains(response, 'Physician (MD/DO)')
        self.assertContains(response, 'Physical Therapist (PT)')
        # Check inactive provider is not shown
        self.assertNotContains(response, 'Inactive Provider')

    def test_healthcare_provider_optional_when_no_interaction(self):
        """Healthcare provider can be omitted when interacted_hcps is False"""
        self.client.force_login(self.user)
        # Payload with interacted_hcps=0 and healthcare_provider specified (should be ignored)
        payload = self.payload.copy()
        payload['healthcare_provider'] = self.physician.id
        
        resp = self.client.post(self.submit_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        
        report = ClinicReport.objects.get(email=self.user.email)
        self.assertIsNotNone(report)
        self.assertFalse(report.interacted_hcps)

    def test_multiple_provider_types(self):
        """Test submitting reports with different healthcare provider types"""
        self.client.force_login(self.user)
        
        # Submit with physician
        resp1 = self.client.post(self.submit_url, data=json.dumps(self.payload_with_hcp), content_type='application/json')
        self.assertEqual(resp1.status_code, 200)
        
        # Submit with physical therapist
        payload_pt = self.payload_with_hcp.copy()
        payload_pt['healthcare_provider'] = self.physical_therapist.id
        resp2 = self.client.post(self.submit_url, data=json.dumps(payload_pt), content_type='application/json')
        self.assertEqual(resp2.status_code, 200)
        
        # Verify both reports were created with correct providers
        self.assertEqual(ClinicReport.objects.count(), 2)
        physician_report = ClinicReport.objects.get(healthcare_provider=self.physician)
        pt_report = ClinicReport.objects.get(healthcare_provider=self.physical_therapist)
        self.assertEqual(physician_report.healthcare_provider, self.physician)
        self.assertEqual(pt_report.healthcare_provider, self.physical_therapist)
