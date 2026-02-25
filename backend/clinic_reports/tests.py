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

        # Create dummy data for the form
        self.payload = {
            'first_name': 'Alice',
            'last_name': 'Example',
            'email': 'alice@university.edu',
            'sport': self.football.id,  # Form submissions use sport ID as json value
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
            'first_name': 'Bob',
            'last_name': 'Student',
            'email': 'bob@university.edu',
            'sport': self.football.id,
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
        self.client.force_login(self.user)
        self.client.post(self.submit_url, data=json.dumps(self.payload), content_type='application/json')
        report = ClinicReport.objects.first()
        self.assertIsNotNone(report)
        self.assertEqual(report.first_name, 'Alice')
        self.assertEqual(report.sport, self.football)  # Compare with Sport object

    def test_invalid_email(self):
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        bad_payload['email'] = 'not-an-email'
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_missing_required_field(self):
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        del bad_payload['first_name']
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertNotEqual(resp.status_code, 200)
        self.assertEqual(ClinicReport.objects.count(), 0)

    def test_sql_injection_attempt(self):
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        bad_payload['first_name'] = "Robert'); DROP TABLE clinic_reports_clinicreport;--"
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(ClinicReport.objects.filter(first_name__contains='Robert').exists())

    def test_xss_injection(self):
        self.client.force_login(self.user)
        bad_payload = self.payload.copy()
        bad_payload['last_name'] = '<script>alert(1)</script>'
        resp = self.client.post(self.submit_url, data=json.dumps(bad_payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        report = ClinicReport.objects.get(first_name='Alice')
        self.assertIn('<script>', report.last_name)

    @override_settings(LOGIN_URL='/accounts/microsoft/login/') # Simulate production situation (Azure credentials are available, so redirect to microsoft login) in test env
    def test_no_form_if_not_authenticated(self):
        # Use reverse to avoid hardcoding URLs
        resp = self.client.get(self.url)
        # Check that the site redirects unauthenticated users to the login page
        # if they try to access the form
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/microsoft/login/', resp['Location'])

    def test_form_view_allows_authenticated(self):
        self.client.force_login(self.user) # This simulates logging in the user
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        # Check that the submit button exists (this proves we are in the form view)
        self.assertContains(resp, "Submit Report")  

    def test_submit_requires_auth(self):
        # Unauthenticated users shouldn't be able to submit the form
        resp = self.client.post(self.submit_url, data=json.dumps(self.payload), content_type='application/json')
        self.assertEqual(resp.status_code, 401)
        body = json.loads(resp.content)
        # Check that success is false and error message is correct
        self.assertFalse(body.get('success'))
        self.assertIn("Authentication required", body.get('error', ''))
        self.assertEqual(ClinicReport.objects.count(), 0)
    
    def test_submit_creates_report_when_authenticated(self):
        self.client.force_login(self.user)
        resp = self.client.post(self.submit_url, data=json.dumps(self.payload), content_type='application/json')
        # the view returns JsonResponse with success True
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertTrue(body.get('success')) # Checks that the form sent back a "success" message
        self.assertEqual(ClinicReport.objects.count(), 1) # Checks new record added to DB

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
        
        report = ClinicReport.objects.get(email='bob@university.edu')
        self.assertIsNotNone(report)
        self.assertTrue(report.interacted_hcps)
        self.assertEqual(report.healthcare_provider, self.physician)

    def test_submit_without_healthcare_provider(self):
        """Successfully submit a report without healthcare provider interaction"""
        self.client.force_login(self.user)
        payload_no_hcp = self.payload.copy()
        payload_no_hcp['email'] = 'nohcp@university.edu'
        payload_no_hcp['interacted_hcps'] = 0
        resp = self.client.post(self.submit_url, data=json.dumps(payload_no_hcp), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.content)
        self.assertTrue(body.get('success'))
        
        report = ClinicReport.objects.get(email='nohcp@university.edu')
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
        payload['email'] = 'optional@university.edu'
        payload['healthcare_provider'] = self.physician.id
        
        resp = self.client.post(self.submit_url, data=json.dumps(payload), content_type='application/json')
        self.assertEqual(resp.status_code, 200)
        
        report = ClinicReport.objects.get(email='optional@university.edu')
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
        payload_pt['email'] = 'different@university.edu'
        payload_pt['healthcare_provider'] = self.physical_therapist.id
        resp2 = self.client.post(self.submit_url, data=json.dumps(payload_pt), content_type='application/json')
        self.assertEqual(resp2.status_code, 200)
        
        # Verify both reports were created with correct providers
        self.assertEqual(ClinicReport.objects.count(), 2)
        physician_report = ClinicReport.objects.get(email='bob@university.edu')
        pt_report = ClinicReport.objects.get(email='different@university.edu')
        self.assertEqual(physician_report.healthcare_provider, self.physician)
        self.assertEqual(pt_report.healthcare_provider, self.physical_therapist)
