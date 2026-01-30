import os
from django.test import TestCase, override_settings
from django.forms import ValidationError
from types import SimpleNamespace
from core.adapters import CustomSocialAccountAdapter

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
