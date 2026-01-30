from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json
from clinic_reports.models import ClinicReport

User = get_user_model() # Gets whatever Django user model we are using (the built in one or a custom one)

class ClinicReportViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse('form')
        self.submit_url = reverse('submit_report')
        self.user = User.objects.create_user(username='tester', email='tester@university.edu', password='pass')

        # Create dummy data for the form
        self.payload = {
            'first_name': 'Alice',
            'last_name': 'Example',
            'email': 'alice@university.edu',
            'clinical_site': 'Sports Med',
            'sport': 'Football',
            'immediate_emergency_care': 1,
            'musculoskeletal_exam': 2,
            'non_musculoskeletal_exam': 0,
            'taping_bracing': 0,
            'rehabilitation_reconditioning': 0,
            'modalities': 0,
            'pharmacology': 0,
            'injury_illness_prevention': 0,
            'non_sport_patient': 0,
        }

    def test_no_form_if_not_authenticated(self):
        # Use reverse to avoid hardcoding URLs
        resp = self.client.get(self.url)
        # Check that the site redirects unauthenticated users to the login page
        # if they try to access the form
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])

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