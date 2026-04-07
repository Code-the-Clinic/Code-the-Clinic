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
        self.assertIn('Invalid filter parameters', data.get('error', ''))

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
        self.assertIn('Invalid filter parameters', data.get('error', ''))


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
    """Test that LOGIN_URL is configured correctly based on runtime environment."""
    
    @patch('config.settings.IS_IN_AZURE', True)
    def test_login_url_in_azure_environment(self):
        """When running in Azure App Service, LOGIN_URL should go to Microsoft login."""
        from config.settings import get_login_url
        self.assertEqual(get_login_url(), '/accounts/microsoft/login/')
    
    @patch('config.settings.IS_IN_AZURE', False)
    def test_login_url_in_local_environment_uses_provider_chooser(self):
        """Outside Azure, LOGIN_URL should use provider chooser even if MS creds exist."""
        from config.settings import get_login_url
        self.assertEqual(get_login_url(), '/accounts/login/')


class FacultyDashboardMetricsTests(TestCase):
    """Tests for faculty_dashboard_view filters and aggregate math."""

    @classmethod
    def setUpTestData(cls):
        cls.football, _ = Sport.objects.get_or_create(name='Football', defaults={'active': True})
        cls.soccer, _ = Sport.objects.get_or_create(name='Soccer', defaults={'active': True})

    def setUp(self):
        self.client = Client()
        self.url = reverse('faculty_dashboard')

        self.staff_user = User.objects.create_user(
            username='staff-metrics',
            email='staff-metrics@university.edu',
            password='testpass123',
            is_staff=True,
        )
        self.client.force_login(self.staff_user)

        # Two reports with known totals
        ClinicReport.objects.create(
            first_name='Alice',
            last_name='Liddell',
            email='alice@university.edu',
            sport=self.football,
            week=1,
            immediate_emergency_care=2,
            musculoskeletal_exam=0,
            non_musculoskeletal_exam=0,
            taping_bracing=0,
            rehabilitation_reconditioning=0,
            modalities=1,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )
        ClinicReport.objects.create(
            first_name='Bob',
            last_name='Smith',
            email='bob@university.edu',
            sport=self.soccer,
            week=1,
            immediate_emergency_care=1,
            musculoskeletal_exam=5,
            non_musculoskeletal_exam=0,
            taping_bracing=0,
            rehabilitation_reconditioning=5,
            modalities=0,
            pharmacology=0,
            injury_illness_prevention=0,
            non_sport_patient=0,
            interacted_hcps=False,
        )

    def test_post_filters_override_get(self):
        """On POST, filters are taken from POST, not GET query params."""
        response = self.client.post(
            self.url + '?student=Eve%20(ignored@university.edu)',
            {
                'student': 'First Last (alice@university.edu)',
                'care_category': 'modalities',
                "semester2": "Fall '24",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Selected values come from POST
        self.assertEqual(
            response.context['selected_student'],
            'First Last (alice@university.edu)',
        )
        self.assertEqual(response.context['care_category'], 'modalities')
        self.assertEqual(response.context['selected_semester2'], "Fall '24")

    def test_key_metrics_math(self):
        """Key metrics totals, averages, and most-active sport are correct."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        # Totals across all care fields
        # Alice: 2 immediate + 1 modalities = 3
        # Bob:   1 immediate + 5 musculoskeletal + 5 rehab = 11
        # Total experiences = 14
        self.assertEqual(response.context['metric_total_experiences'], 14)

        # Two distinct student emails
        self.assertEqual(response.context['metric_active_students'], 2)
        # 14 / 2 = 7.0
        self.assertEqual(response.context['metric_avg_per_student'], 7.0)

        # Two reports total
        self.assertEqual(response.context['metric_total_reports'], 2)

        # Most common care type should be Musculoskeletal Exam (5)
        self.assertEqual(response.context['metric_most_common_care'], 'Musculoskeletal Exam')

        # Most active sport is Soccer (11 experiences) vs Football (3)
        self.assertEqual(response.context['metric_most_active_sport'], 'Soccer')

    def test_pie_charts_math(self):
        """Pie charts correctly reflect category and per-sport totals."""
        response = self.client.post(self.url, {'care_category': 'immediate_emergency_care'})
        self.assertEqual(response.status_code, 200)

        pie1 = response.context['pie_chart_data']
        labels1 = {item['label']: item['value'] for item in pie1}
        # Immediate/Emergency total across both reports: 2 + 1 = 3
        self.assertEqual(labels1.get('Immediate/Emergency'), 3)

        pie2 = response.context['pie_chart_data2']
        labels2 = {item['label']: item['value'] for item in pie2}
        # Per-sport totals for Immediate/Emergency
        self.assertEqual(labels2.get('Football'), 2)
        self.assertEqual(labels2.get('Soccer'), 1)

    def test_trend_chart_math(self):
        """Trend chart datasets sum experiences per sport per week."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        datasets = response.context['trend_datasets']
        data_by_label = {ds['label']: ds['data'] for ds in datasets}

        football_data = data_by_label['Football']
        soccer_data = data_by_label['Soccer']

        # Week 1 index is 0
        self.assertEqual(football_data[0], 3)  # 2 immediate + 1 modalities
        self.assertEqual(soccer_data[0], 11)   # 1 immediate + 5 musculoskeletal + 5 rehab

    def test_metric_filters_by_student_and_semester(self):
        """Metric filters (metric_student, metric_semester) correctly restrict aggregates."""
        # Derive the semester/year string from the actual report so the test
        # is stable regardless of current date (Spring vs Fall).
        alice_report = ClinicReport.objects.get(email='alice@university.edu')
        year = alice_report.created_at.year
        short_year = str(year)[-2:]
        formatted_semester = f"{alice_report.semester} '{short_year}"

        # Filter to Alice only in this semester
        response = self.client.post(self.url, {
            'metric_student': 'Alice Liddell (alice@university.edu)',
            'metric_semester': formatted_semester,
        })
        self.assertEqual(response.status_code, 200)

        # Only Alice's 3 experiences should be counted
        self.assertEqual(response.context['metric_total_experiences'], 3)
        self.assertEqual(response.context['metric_active_students'], 1)
        self.assertEqual(response.context['metric_avg_per_student'], 3.0)
        self.assertEqual(response.context['metric_total_reports'], 1)

    def test_trend_filters_by_sport_and_care_type(self):
        """Trend filters limit datasets to the requested sport and care type."""
        # Immediate/emergency care only, and only Football
        response = self.client.post(self.url, {
            'trend_sport': 'Football',
            'trend_care': 'immediate_emergency_care',
        })
        self.assertEqual(response.status_code, 200)

        datasets = response.context['trend_datasets']
        original_datasets = [ds for ds in datasets if ds['label'] != 'Total Patient Encounters']
        # Only Football should be present
        self.assertEqual(len(original_datasets), 1)
        self.assertEqual(original_datasets[0]['label'], 'Football')

        # For Football and care type immediate_emergency_care, week 1 total is 2
        football_data = original_datasets[0]['data']
        self.assertEqual(football_data[0], 2)

    def test_trend_filters_by_student(self):
        """Trend filters for trend_student restrict data to that student only.""" 
        response = self.client.post(self.url, {
            'trend_student': 'Alice Liddell (alice@university.edu)',
        })
        self.assertEqual(response.status_code, 200)

        datasets = response.context['trend_datasets']
        original_datasets = [ds for ds in datasets if ds['label'] != 'Total Patient Encounters']
        labels = {ds['label'] for ds in original_datasets}

        # With a student filter, only sports where that student has data appear
        self.assertEqual(labels, {'Football'})

        data_by_label = {ds['label']: ds['data'] for ds in original_datasets}
        football_data = data_by_label['Football']

        # Alice only has Football experiences: 3 at week 1, and no weeks for Soccer
        self.assertEqual(football_data[0], 3)

