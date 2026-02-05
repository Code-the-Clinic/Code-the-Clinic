# Backend README

## IMPORTANT security tasks
- Create local .env file: We can't store secret keys in the code, so we use environment variables in a .env file. .env has been added to gitignore, so it shouldn't publish to GitHub. For local Django testing, create your own Django secret key with this command:
    - python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
- After creating the key, add it to your .env file using the template given in .env-example. Now you should be able to run the app with your local secret key.
- Do the same thing for other credentials (Azure, etc.)--always store them in your local .env, NOT in .env-example or other files that are published to Git!
- To run the app in production, set DEBUG=False in settings.py! Setting it to True is insecure for a production environment.
- [Long-term] Get rid of CSRF exempt functions (use CSRF tokens to keep everything secure)

## How to run in development
- To run the docs AND the django backend: docker-compose up
- To run the docs and the django backend and rebuild the docker container (for example, if you added new dependencies to requirements.txt): docker-compose up --build
- To update the local database:
    - Create migration: docker-compose exec backend python manage.py makemigrations clinic_reports
        - Use the name of the data model instead of clinic_reports if updating a different model
    - Run migration: docker-compose exec backend python manage.py migrate
- To create a superuser (required to locally test the admin page without a Microsoft account): docker-compose exec backend python manage.py createsuperuser

## How to test in a production-like environment
- Run `docker-compose -f docker-compose.prod.yml up --build` — no bind mount, staticfiles from image.
- When deploying in production: Remove bind mounts, ensure collectstatic runs during build, and serve statics via Whitenoise or Nginx.

## How to test
- To run all backend tests: docker-compose exec backend python manage.py test
- To run all backend tests for a specific app: docker-compose exec backend python manage.py test app-name
    - For example, python manage.py test clinic_reports would run all the tests under the clinic_reports app (these check whether the form authentication and submission logic works correctly).

## How to debug
- If you are getting Django import errors after force-quitting and restarting Docker Desktop, try these steps to force re-creating all Docker containers without cache (in case the cache got corrupted during the abrupt restart). WARNING: This will delete all the records in your local database! NEVER use this method in production--only in local development!
docker-compose down -v (removes all containers and deletes all associated volumes)
docker system prune -f (removes all unused data)
docker-compose up --build (rebuilds all the containers without caching)
- If you are getting DB errors that the relation "django-session" doesn't exist, you need to run the migration command listed in the "how to run" section to recreate all the tables that Django expects to be in the database.

## How to get myBama auth working
- Get a personal Azure tenant ID and secret by creating an Azure account, or ask me for mine (I shared a doc with instructions for creating your own Azure credentials)
- Put your Azure tenant ID and secret in .env (follow the instructions in .env-example)
- Go to /accounts/microsoft/login and it should let you authenticate with myBama
- If you want to be automatically logged in to the admin portal with myBama, you will need to follow these steps:
    - Log in with myBama--this will create a user in the system for you
    - Log out
    - Create a superuser: docker-compose exec backend python manage.py createsuperuser
    - Log in to the admin portal as the superuser
    - Use the admin portal to give your myBama user superuser permissions
    - Delete the manually created superuser when you are done for security
    - Now when you log in with your crimson email you should automatically be able to see the admin dashboard!