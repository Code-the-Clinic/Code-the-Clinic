import os
import json
from django.test import TestCase, override_settings, Client
from django.forms import ValidationError
from types import SimpleNamespace
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.adapters import CustomSocialAccountAdapter
from clinic_reports.models import ClinicReport

User = get_user_model()

class AdapterDomainTests(TestCase):
    def setUp(self):
        self.adapter = CustomSocialAccountAdapter()

    def make_sociallogin(self, email_value):
        # Creates small fake object with email in expected field
        return SimpleNamespace(account=SimpleNamespace(extra_data={'email': email_value}))

    def test_allows_allowed_domain(self):
        # Set fake values for allowed domains to avoid leaking real university email domains
        os.environ['ALLOWED_DOMAINS'] = 'university.edu,another.edu'
        sociallogin = self.make_sociallogin('user@university.edu')

        # Should authenticate successfully
        try:
            self.adapter.pre_social_login(request=None, sociallogin=sociallogin)
        except ValidationError as e:
            self.fail(f"pre_social_login unexpectedly raised a ValidationError: {e}")

    def test_blocks_disallowed_domain(self):
        os.environ['ALLOWED_DOMAINS'] = 'university.edu,another.edu'
        sociallogin = self.make_sociallogin('intruder@notallowed.com')

        with self.assertRaises(ValidationError):
            self.adapter.pre_social_login(request=None, sociallogin=sociallogin)

    def test_missing_email_raises(self):
        os.environ['ALLOWED_DOMAINS'] = 'university.edu'
        sociallogin = SimpleNamespace(account=SimpleNamespace(extra_data={}))  # no email
        # Should throw a ValidationError when email is missing
        with self.assertRaises(ValidationError):
            self.adapter.pre_social_login(request=None, sociallogin=sociallogin)

# TODO: Check that faculty dashboard view can't render without staff authentication
class FetchDataTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.fetch_url = reverse('fetch_data')

        self.student_user = User.objects.create_user(
            username='student',
            email='student@university.edu',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staff',
            email='staff@university.edu',
            password='testpass123',
            is_staff=True
        )

        # Create two reports with distinct emails and counts
        ClinicReport.objects.create(
            first_name='Alice',
            last_name='Student',
            email='student@university.edu',
            clinical_site='Clinic A',
            sport='Football',
            immediate_emergency_care=1,
            musculoskeletal_exam=2,
            non_musculoskeletal_exam=0,
            taping_bracing=1,
            rehabilitation_reconditioning=0,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=True,
        )
        ClinicReport.objects.create(
            first_name='Bob',
            last_name='Other',
            email='other@university.edu',
            clinical_site='Clinic B',
            sport='Soccer',
            immediate_emergency_care=0,
            musculoskeletal_exam=1,
            non_musculoskeletal_exam=1,
            taping_bracing=0,
            rehabilitation_reconditioning=1,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )

    def post_fetch(self, user, payload):
        self.client.force_login(user)
        response = self.client.post(
            self.fetch_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        return response

    def test_fetch_data_requires_auth(self):
        response = self.client.post(
            self.fetch_url,
            data=json.dumps({}),
            content_type='application/json'
        )
        data = json.loads(response.content)
        self.assertFalse(data.get('success'))
        self.assertIn('Authentication required', data.get('error', ''))

    def test_non_staff_forced_to_own_email(self):
        # Attempt to request another student's email
        response = self.post_fetch(self.student_user, {'email': 'other@university.edu'})
        data = json.loads(response.content)
        stats = data.get('stats')

        # The student user's weekly total = 1+2+0+1+0+0+0+0+0 = 4
        self.assertEqual(stats.get('grand_total_served'), 4)
        self.assertEqual(stats.get('total_musculoskeletal_exam'), 2)
    
    def test_non_staff_forced_to_own_email_with_empty_input(self):
        # Attempt to request another student's email
        response = self.post_fetch(self.student_user, {})
        data = json.loads(response.content)
        stats = data.get('stats')

        # The student user's weekly total = 1+2+0+1+0+0+0+0+0 = 4
        self.assertEqual(stats.get('grand_total_served'), 4)
        self.assertEqual(stats.get('total_musculoskeletal_exam'), 2)

    def test_staff_can_filter_any_email(self):
        response = self.post_fetch(self.staff_user, {'email': 'other@university.edu'})
        data = json.loads(response.content)
        stats = data.get('stats')

        # The other user's weekly total = 0+1+1+0+1+0+0+0+0 = 3
        self.assertEqual(stats.get('grand_total_served'), 3)
        self.assertEqual(stats.get('total_non_musculoskeletal_exam'), 1)

    def test_staff_filter_by_sport(self):
        response = self.post_fetch(self.staff_user, {'sport': 'Football'})
        data = json.loads(response.content)
        stats = data.get('stats')

        # Football report weekly total = 1+2+0+1+0+0+0+0+0 = 4
        self.assertEqual(stats.get('grand_total_served'), 4)
        self.assertEqual(stats.get('total_musculoskeletal_exam'), 2)
        self.assertEqual(stats.get('total_interacted_hcps'), 1)

    def test_staff_filter_by_clinical_site(self):
        response = self.post_fetch(self.staff_user, {'clinical_site': 'Clinic B'})
        data = json.loads(response.content)
        stats = data.get('stats')

        # Clinic B report weekly total = 0+1+1+0+1+0+0+0+0 = 3
        self.assertEqual(stats.get('grand_total_served'), 3)
        self.assertEqual(stats.get('total_rehabilitation_reconditioning'), 1)
        self.assertAlmostEqual(stats.get('average_patients_per_week'), 3)
        self.assertEqual(stats.get('total_interacted_hcps'), 0)

    def test_staff_filter_by_sport_and_clinical_site(self):
        response = self.post_fetch(self.staff_user, {
            'sport': 'Football',
            'clinical_site': 'Clinic B'
        })
        data = json.loads(response.content)
        stats = data.get('stats')

        # No report matches Football + Clinic B
        self.assertEqual(stats.get('grand_total_served'), 0)

    def test_staff_no_filters(self):
        response = self.post_fetch(self.staff_user, {})
        data = json.loads(response.content)
        stats = data.get('stats')

        self.assertEqual(stats.get('grand_total_served'), 7)
        self.assertEqual(stats.get('total_musculoskeletal_exam'), 3)
        self.assertAlmostEqual(stats.get('average_patients_per_week'), 3.5)
        self.assertEqual(stats.get('total_interacted_hcps'), 1)
