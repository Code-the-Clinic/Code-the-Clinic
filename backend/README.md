# Backend README

## IMPORTANT security tasks
- Create local .env file: We can't store secret keys in the code, so we use environment variables in a .env file. .env has been added to gitignore, so it shouldn't publish to GitHub. For local Django testing, create your own Django secret key with this command:
    - python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
- After creating the key, add it to your .env file using the template given in .env-example. Now you should be able to run the app with your local secret key.
- Do the same thing for other credentials (Azure, etc.)--always store them in your local .env, NOT in .env-example or other files that are published to Git!
- To run the app in production, set DEBUG=False in settings.py! Setting it to True is insecure for a production environment.
- [Long-term] Get rid of CSRF exempt functions (use CSRF tokens to keep everything secure)

## How to run in development
- Set up environment variables
    - Open .env-example and set the environment variables according to the guidelines (but do this in a different file, .env, and put .env in gitignore so that you don't expose any secrets.)
    - For Azure credentials, see the "How to get myBama working..." section--local Azure credentials are only needed if you want to test myBama auth locally
- To run the docs AND the django backend: docker-compose up
- To run the docs and the django backend and rebuild the docker container (for example, if you added new dependencies to requirements.txt): docker-compose up --build
- To update the local database:
    - Create migration: docker-compose exec backend python manage.py makemigrations clinic_reports
        - Use the name of the data model instead of clinic_reports if updating a different model
    - Run migration: docker-compose exec backend python manage.py migrate
- To create a superuser (required to locally test the admin page without a Microsoft account): docker-compose exec backend python manage.py createsuperuser

## How to test
- To run all backend tests: docker-compose exec backend python manage.py test
- To run all backend tests for a specific app: docker-compose exec backend python manage.py test app-name
    - For example, python manage.py test clinic_reports would run all the tests under the clinic_reports app (these check whether the form authentication and submission logic works correctly).

## Project layout notes for handoff
- Active Django apps: `core`, `clinic_reports`, and `user_logging` (plus Django/allauth/axes).
- The old scaffolded `api` app has been removed because it was never wired into INSTALLED_APPS or URLs.
- The `scripts/export_dashboard_raw_to_excel.py` helper is a standalone CLI utility and is not called by the web server.
- The `backend/src` and `frontend` folders are currently empty placeholders and can be safely deleted or repurposed in a future phase.

## How to debug
- If you are getting Django import errors after force-quitting and restarting Docker Desktop, try these steps to force re-creating all Docker containers without cache (in case the cache got corrupted during the abrupt restart). WARNING: This will delete all the records in your local database! NEVER use this method in production--only in local development!
docker-compose down -v (removes all containers and deletes all associated volumes)
docker system prune -f (removes all unused data)
docker-compose up --build (rebuilds all the containers without caching)
- If you are getting DB errors that the relation "django-session" doesn't exist, you need to run the migration command listed in the "how to run" section to recreate all the tables that Django expects to be in the database.

## How to get myBama auth working in your local environment
- Get a personal Azure tenant ID and secret by creating an Azure account
    1. Create the App Registration
        - In your personal Azure Portal (portal.azure.com), search for "App registrations" and click "New registration".
        - If you don’t have an Azure account and see something like “tenant blocked due to inactivity,” make a new Azure account, wait 5 minutes, and try again. 
        - Name: Doesn't matter, make this whatever you want 
        - Supported account types: Select the option that says: "Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant)". Do NOT select "Personal Microsoft accounts only". 
        - Redirect URI: (For local development) Select Web and enter http://localhost:8000/accounts/microsoft/login/callback/. This allows us to test myBama auth locally.
        - Click Register. 

    2. Get your Keys
        - Once created, you will land on the Overview page.
        - Copy the Application (client) ID. -> Paste this into your .env as AZURE_CLIENT_ID. 
        - Go to Certificates & secrets (sidebar) -> New client secret.
        - Description: dev-secret, Expires: 6 months 
        - Click Add -> Copy the Value (not the ID!). -> Paste this into your .env as AZURE_SECRET 
        - Put your Azure tenant ID and secret in .env (follow the instructions in .env-example)
        - Go to /accounts/microsoft/login and it should let you authenticate with myBama

    3. If you want to be automatically logged in to the admin portal with myBama, you will need to follow these steps:
        - Log in with myBama--this will create a user in the system for you
        - Log out
        - Create a superuser: docker-compose exec backend python manage.py createsuperuser
        - Log in to the admin portal as the superuser
        - Use the admin portal to give your myBama user superuser permissions
        - Delete the manually created superuser when you are done for security
        - Now when you log in with your crimson email you should automatically be able to see the admin dashboard!