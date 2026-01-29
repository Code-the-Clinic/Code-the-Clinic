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

        # Get the email from Microsoft data
        data = sociallogin.account.extra_data
        email = data.get('email') or data.get('userPrincipalName')

        if not email:
            raise ValidationError("No email address provided by Microsoft.")

        # 3. Check the Domain
        user_domain = email.split('@')[-1].lower()

        if user_domain not in allowed_domains:
            # The Microsoft account doesn't have a University domain
            raise ValidationError(
                f"Access Denied. Please log in with a valid University account (myBama)."
            )