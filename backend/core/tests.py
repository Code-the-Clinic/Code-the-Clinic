import os
import json
from django.utils import timezone
from django.test import TestCase, override_settings, Client
from django.forms import ValidationError
from types import SimpleNamespace
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.adapters import CustomSocialAccountAdapter
from clinic_reports.models import ClinicReport, Sport
from unittest.mock import patch

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
    @classmethod
    def setUpTestData(cls):
        """Run once for the entire test class"""
        cls.football, _ = Sport.objects.get_or_create(name='Football', defaults={'active': True})
        cls.soccer, _ = Sport.objects.get_or_create(name='Soccer', defaults={'active': True})

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

        # Create reports with predictable category totals.
        # Two reports share an email so their computed weeks are 1 and 2.
        ClinicReport.objects.create(
            first_name='Alice',
            last_name='One',
            email='alice@university.edu',
            sport=self.football,
            week=1,
            immediate_emergency_care=1,
            musculoskeletal_exam=2,
            non_musculoskeletal_exam=0,
            taping_bracing=0,
            rehabilitation_reconditioning=0,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )
        ClinicReport.objects.create(
            first_name='Alice',
            last_name='Two',
            email='alice@university.edu',
            sport=self.football,
            week=2,
            immediate_emergency_care=2,
            musculoskeletal_exam=0,
            non_musculoskeletal_exam=0,
            taping_bracing=0,
            rehabilitation_reconditioning=1,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )
        ClinicReport.objects.create(
            first_name='Bob',
            last_name='Three',
            email='bob@university.edu',
            sport=self.soccer,
            week=1,
            immediate_emergency_care=0,
            musculoskeletal_exam=0,
            non_musculoskeletal_exam=1,
            taping_bracing=1,
            rehabilitation_reconditioning=0,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )

    def post_fetch(self, user, payload):
        self.client.force_login(user)
        response = self.client.post(
            self.fetch_url, # URL for fetch_data endpoint
            data=json.dumps(payload),
            content_type='application/json'
        )
        return response

    def test_fetch_data_requires_authentication(self):
        response = self.client.post(
            self.fetch_url,
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)

    def test_fetch_data_denies_non_staff_users(self):
        response = self.post_fetch(self.student_user, {})
        data = json.loads(response.content)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(data.get('success'))
        self.assertIn('Permission denied', data.get('error', ''))

    def test_staff_fetch_without_filters_returns_expected_totals(self):
        response = self.post_fetch(self.staff_user, {})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('total_patients'), 8)
        self.assertAlmostEqual(data.get('average_patients_per_week'), 8 / 3, places=5)

        labels = {item['label']: item['value'] for item in data.get('pie_chart_data', [])}
        self.assertEqual(labels.get('Immediate/Emergency'), 3)
        self.assertEqual(labels.get('Musculoskeletal Exam'), 2)
        self.assertEqual(labels.get('Non-Musculoskeletal'), 1)
        self.assertEqual(labels.get('Taping/Bracing'), 1)
        self.assertEqual(labels.get('Rehabilitation'), 1)

    def test_staff_filter_by_sport(self):
        response = self.post_fetch(self.staff_user, {'sport': 'Football'})
        data = json.loads(response.content)
        labels = {item['label']: item['value'] for item in data.get('pie_chart_data', [])}

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('total_patients'), 6)
        self.assertAlmostEqual(data.get('average_patients_per_week'), 3.0, places=5)
        self.assertEqual(labels.get('Immediate/Emergency'), 3)
        self.assertEqual(labels.get('Musculoskeletal Exam'), 2)
        self.assertEqual(labels.get('Rehabilitation'), 1)
        self.assertNotIn('Non-Musculoskeletal', labels)

    def test_staff_filter_by_semester(self):
        response = self.post_fetch(self.staff_user, {'semester': 'Spring'})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('total_patients'), 8)

    def test_staff_filter_by_week(self):
        response = self.post_fetch(self.staff_user, {'week': 2})
        data = json.loads(response.content)
        labels = {item['label']: item['value'] for item in data.get('pie_chart_data', [])}

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('total_patients'), 3)
        self.assertEqual(labels.get('Immediate/Emergency'), 2)
        self.assertEqual(labels.get('Rehabilitation'), 1)
        self.assertNotIn('Musculoskeletal Exam', labels)

    def test_staff_filter_by_year(self):
        response = self.post_fetch(self.staff_user, {'year': timezone.now().year})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('total_patients'), 8)

    def test_staff_filter_by_year_rejects_non_numeric_value(self):
        response = self.post_fetch(self.staff_user, {'year': 'Spr'})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data.get('success'))
        self.assertIn('Invalid year', data.get('error', ''))

    def test_fetch_data_rejects_invalid_json(self):
        self.client.force_login(self.staff_user)
        response = self.client.post(
            self.fetch_url,
            data='not-json',
            content_type='application/json'
        )
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data.get('success'))
        self.assertIn('Invalid JSON', data.get('error', ''))

    def test_staff_fetch_with_no_matching_results_returns_zero_average(self):
        response = self.post_fetch(
            self.staff_user,
            {
                'sport': 'Football',
                'week': 16,
                'year': timezone.now().year,
            }
        )
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('total_patients'), 0)
        self.assertEqual(data.get('pie_chart_data'), [])
        self.assertEqual(data.get('average_patients_per_week'), 0.0)


class FetchStudentDataTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.football, _ = Sport.objects.get_or_create(name='Football', defaults={'active': True})
        cls.soccer, _ = Sport.objects.get_or_create(name='Soccer', defaults={'active': True})

    def setUp(self):
        self.client = Client()
        self.fetch_student_url = reverse('fetch_student_data')

        self.student_user = User.objects.create_user(
            username='student-self',
            email='student-self@university.edu',
            password='testpass123'
        )
        self.other_student = User.objects.create_user(
            username='student-other',
            email='student-other@university.edu',
            password='testpass123'
        )
        self.staff_user = User.objects.create_user(
            username='staff-for-student-endpoint',
            email='staff-only@university.edu',
            password='testpass123',
            is_staff=True
        )

        ClinicReport.objects.create(
            first_name='Self',
            last_name='One',
            email='student-self@university.edu',
            sport=self.football,
            immediate_emergency_care=1,
            musculoskeletal_exam=1,
            non_musculoskeletal_exam=0,
            taping_bracing=0,
            rehabilitation_reconditioning=0,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )
        ClinicReport.objects.create(
            first_name='Self',
            last_name='Two',
            email='student-self@university.edu',
            sport=self.football,
            immediate_emergency_care=0,
            musculoskeletal_exam=0,
            non_musculoskeletal_exam=0,
            taping_bracing=1,
            rehabilitation_reconditioning=1,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )
        ClinicReport.objects.create(
            first_name='Other',
            last_name='User',
            email='student-other@university.edu',
            sport=self.soccer,
            immediate_emergency_care=5,
            musculoskeletal_exam=0,
            non_musculoskeletal_exam=0,
            taping_bracing=0,
            rehabilitation_reconditioning=0,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )

    def post_fetch_student(self, user, payload):
        self.client.force_login(user)
        return self.client.post(
            self.fetch_student_url,
            data=json.dumps(payload),
            content_type='application/json'
        )

    def test_fetch_student_data_requires_authentication(self):
        response = self.client.post(
            self.fetch_student_url,
            data=json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 302)

    def test_fetch_student_data_denies_staff_user(self):
        response = self.post_fetch_student(self.staff_user, {})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 403)
        self.assertFalse(data.get('success'))
        self.assertIn('faculty endpoint', data.get('error', ''))

    def test_fetch_student_data_returns_only_current_user_data(self):
        response = self.post_fetch_student(self.student_user, {'email': 'student-other@university.edu'})
        data = json.loads(response.content)
        labels = {item['label']: item['value'] for item in data.get('pie_chart_data', [])}

        self.assertEqual(response.status_code, 200)
        self.assertTrue(data.get('success'))
        # Only the current student totals should count: (1+1) + (1+1) = 4
        self.assertEqual(data.get('total_patients'), 4)
        self.assertAlmostEqual(data.get('average_patients_per_week'), 2.0, places=5)
        self.assertEqual(labels.get('Immediate/Emergency'), 1)
        self.assertEqual(labels.get('Musculoskeletal Exam'), 1)
        self.assertEqual(labels.get('Taping/Bracing'), 1)
        self.assertEqual(labels.get('Rehabilitation'), 1)
        self.assertNotIn('Non-Musculoskeletal', labels)

    def test_fetch_student_data_rejects_invalid_year(self):
        response = self.post_fetch_student(self.student_user, {'year': 'Spring'})
        data = json.loads(response.content)

        self.assertEqual(response.status_code, 400)
        self.assertFalse(data.get('success'))
        self.assertIn('Invalid year', data.get('error', ''))


class HomeViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.home_url = reverse('home')

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

    def test_home_view_anonymous_user(self):
        """Anonymous users should see the home page with login button"""
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Code the Clinic')
        self.assertContains(response, 'Login with myBama')
        # Anonymous users should NOT see admin or student dashboard links in navbar
        self.assertNotContains(response, '/dashboard/admin/')
        self.assertNotContains(response, '/dashboard/student/')
        # Anonymous users should NOT see admin portal button
        self.assertNotContains(response, 'Admin Portal')
    
    def test_home_view_authenticated_student(self):
        """Authenticated non-staff users should see student options"""
        self.client.force_login(self.student_user)
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Code the Clinic')
        # Student should see student dashboard link in nav
        self.assertContains(response, '/dashboard/student/')
        # Student should NOT see admin dashboard link in navbar
        self.assertNotContains(response, '/dashboard/admin/')
        # Student should NOT see admin portal button
        self.assertNotContains(response, 'Admin Portal')

    def test_home_view_authenticated_staff(self):
        """Authenticated staff users should see faculty options"""
        self.client.force_login(self.staff_user)
        response = self.client.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Welcome to Code the Clinic')
        # Staff should see admin dashboard link in navbar
        self.assertContains(response, '/dashboard/admin/')
        # Staff should see admin portal button
        self.assertContains(response, 'Admin Portal')
        self.assertContains(response, '/admin/')

    def test_home_view_context(self):
        """Home view should pass user context to template"""
        self.client.force_login(self.student_user)
        response = self.client.get(self.home_url)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertFalse(response.context['user'].is_staff)

        self.client.force_login(self.staff_user)
        response = self.client.get(self.home_url)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertTrue(response.context['user'].is_staff)

class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()
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

    @override_settings(LOGIN_URL='/accounts/microsoft/login/')
    def test_faculty_dashboard_requires_login(self):
        """Faculty dashboard should redirect anonymous users to login"""
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/microsoft/login/', response.url)

    @override_settings(LOGIN_URL='/accounts/microsoft/login/')
    def test_student_dashboard_requires_login(self):
        """Student dashboard should redirect anonymous users to login"""
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/microsoft/login', response.url)

    def test_faculty_dashboard_authenticated(self):
        """Authenticated users can access faculty dashboard"""
        self.client.force_login(self.staff_user)
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_dashboard_authenticated(self):
        """Authenticated users can access student dashboard"""
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('student_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_student_cannot_access_faculty_dashboard(self):
        """Students get redirected to login when trying to access faculty dashboard"""
        self.client.force_login(self.student_user)
        response = self.client.get(reverse('faculty_dashboard'))
        self.assertEqual(response.status_code, 403) # Permission denied error


class LoginUrlSettingsTests(TestCase):
    """Test that LOGIN_URL is configured correctly based on Azure credentials"""
    
    @patch.dict(os.environ, {'MICROSOFT_LOGIN_CLIENT_ID': 'test-client-id'})
    def test_login_url_with_azure_credentials(self):
        """When Azure credentials are present, LOGIN_URL should go to Microsoft login"""
        from config.settings import get_login_url
        self.assertEqual(get_login_url(), '/accounts/microsoft/login/')
    
    @patch.dict(os.environ, {}, clear=False)
    def test_login_url_without_azure_credentials(self):
        """When Azure credentials are absent, LOGIN_URL should go to provider chooser"""
        from config.settings import get_login_url
        # Remove MICROSOFT_LOGIN_CLIENT_ID if it exists
        os.environ.pop('MICROSOFT_LOGIN_CLIENT_ID', None)
        self.assertEqual(get_login_url(), '/accounts/login/')

