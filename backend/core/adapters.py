import os
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.forms import ValidationError

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Executed immediately after Microsoft verifies the user,
        but BEFORE the user is created or logged into Django.
        """
        # Load allowed domains from .env
        allowed_list = os.environ.get('ALLOWED_DOMAINS', '').split(',')
        allowed_domains = [d.strip().lower() for d in allowed_list if d.strip()]

        # Get user email from Microsoft data
        data = sociallogin.account.extra_data
        email = data.get('email') or data.get('userPrincipalName')

        if not email:
            raise ValidationError("No email address provided by Microsoft.")

        # 3. Check email domain (should be a university email)
        user_domain = email.split('@')[-1].lower()

        if user_domain not in allowed_domains:
            # Not a university domain--do not authenticate
            raise ValidationError(
                f"Access Denied. Please log in with a valid University account (myBama)."
            )