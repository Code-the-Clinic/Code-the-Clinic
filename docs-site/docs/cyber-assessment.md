---
hide:
  - navigation
---

# Cyber assessment
## Security features we implemented
- Secure myBama authentication using an official UA Microsoft app registration
- Force social account login in production (SOCIALACCOUNT_ONLY = True automatically in Azure) so that no one can use the standard Django username/password login--this lowers the risk of brute-force attacks
- Set an environment variable (ALLOW_PASSWORD_ADMIN_LOGIN) to prevent users from being able to log into the Django admin portal using a username and password (they MUST log in with myBama) unless this is set to True (in production, this should only be done temporarily to create an emergency superuser in case of accidental account lockouts. During normal use, all users, including admins, should be exclusively using myBama credentials to sign in.)
- Enabled Axes, a Django add-on that logs all access attempts in the admin portal and locks out users after a set number of incorrect login attempts (this is to add an extra layer of protection against brute-force attacks if username/password login is temporarily enabled for the admin portal)
- Use CSRF tokens to prevent cross-site request forgery
- Use Python logging instead of print statements for detailed error messages to prevent stack trace exposure
- Use secure cookies by default
- Enforce HTTPS-only traffic (if anyone tries to access our website via standard HTTP, they will be automatically redirected to HTTPS)

## Issues to review periodically
- Make sure that DEBUG is set to False in the Azure App Service's environment variables--this prevents detailed error messages from being exposed to attackers.
- Make sure that ALLOW_PASSWORD_ADMIN_LOGIN is set to false
- Unless you are actively creating/editing secrets, make sure that the Key Vault is set to only accept traffic from the VNet that contains the App Service and DB (not any other IP addresses). You can check this under the Key Vault's Networking settings.
- Make sure the database (Azure DB for PostgreSQL resource in the Azure portal) is set to only accept traffic from the private endpoint that connects to the App Service's VNet. You can check this in the DB's Networking settings.
- Perform periodic audits for any instances of @csrf_exempt--you shouldn't have any instances of this in production code because all API endpoints should be protected by CSRF tokens.

