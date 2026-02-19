from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json
from clinic_reports.models import ClinicReport, Sport

User = get_user_model() # Gets whatever Django user model we are using (the built in one or a custom one)


class ClinicReportViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Run once for the entire test class"""
        cls.football, _ = Sport.objects.get_or_create(name='Football', defaults={'active': True})
        cls.inactive, _ = Sport.objects.get_or_create(name='Inactive', active=False)

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