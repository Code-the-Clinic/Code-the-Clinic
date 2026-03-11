import json

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import UserActivityLog

User = get_user_model()


class UserActivityLogSignalTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='signal-user',
            email='signal@university.edu',
            password='testpass123',
        )

    def test_login_and_logout_events_are_logged(self):
        self.assertTrue(self.client.login(username='signal-user', password='testpass123'))
        self.client.logout()

        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.user,
                event_type=UserActivityLog.EventType.LOGIN,
            ).exists()
        )
        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.user,
                event_type=UserActivityLog.EventType.LOGOUT,
            ).exists()
        )


class RequestLoggingMiddlewareTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.staff_user = User.objects.create_user(
            username='request-logger',
            email='request-logger@university.edu',
            password='testpass123',
            is_staff=True,
        )

    def test_anonymous_requests_are_not_logged(self):
        self.client.get('/')
        self.assertFalse(UserActivityLog.objects.filter(path='/').exists())

    def test_authenticated_get_requests_are_logged_across_admin_and_site_routes(self):
        self.client.force_login(self.staff_user)

        self.client.get('/')
        self.client.get('/dashboard/admin/')
        self.client.get('/admin/')
        self.client.get('/admin/jsi18n/')
        self.client.get('/favicon.ico')

        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.staff_user,
                path='/',
                event_type=UserActivityLog.EventType.PAGE_VIEW,
            ).exists()
        )
        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.staff_user,
                path='/dashboard/admin/',
                event_type=UserActivityLog.EventType.DASHBOARD_VIEW,
            ).exists()
        )
        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.staff_user,
                path='/admin/',
                event_type=UserActivityLog.EventType.PAGE_VIEW,
            ).exists()
        )
        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.staff_user,
                path='/admin/jsi18n/',
                event_type=UserActivityLog.EventType.PAGE_VIEW,
            ).exists()
        )
        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.staff_user,
                path='/favicon.ico',
                status_code=404,
                event_type=UserActivityLog.EventType.PAGE_VIEW,
            ).exists()
        )


class ReportSubmissionLoggingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        sport_model = apps.get_model('clinic_reports', 'Sport')
        sport, _ = sport_model.objects.get_or_create(name='Football', defaults={'active': True})
        cls.sport_id = sport.pk

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='logger',
            email='logger@university.edu',
            password='testpass123',
        )
        self.submit_url = reverse('submit_report')
        self.payload = {
            'first_name': 'Log',
            'last_name': 'Tester',
            'email': 'logger@university.edu',
            'sport': self.sport_id,
            'week': 4,
            'immediate_emergency_care': 1,
            'musculoskeletal_exam': 1,
            'non_musculoskeletal_exam': 0,
            'taping_bracing': 0,
            'rehabilitation_reconditioning': 0,
            'modalities': 0,
            'pharmacology': 0,
            'injury_illness_prevention': 0,
            'non_sport_patient': 0,
            'interacted_hcps': 0,
        }

    def test_submit_report_creates_report_submitted_log(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.submit_url,
            data=json.dumps(self.payload),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            UserActivityLog.objects.filter(
                user=self.user,
                event_type=UserActivityLog.EventType.REPORT_SUBMITTED,
                path=self.submit_url,
            ).exists()
        )
