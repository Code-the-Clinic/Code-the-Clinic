# Backend README

## IMPORTANT security tasks
- Create local .env file: We can't store secret keys in the code, so we use environment variables in a .env file. .env has been added to gitignore, so it shouldn't publish to GitHub. For local Django testing, create your own Django secret key with this command:
    - python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
- After creating the key, add it to your .env file using the template given in .env-example. Now you should be able to run the app with your local secret key.
- Do the same thing for other credentials (Azure, etc.)--always store them in your local .env, NOT in .env-example or other files that are published to Git!
- To run the app in production, set DEBUG=False in settings.py! Setting it to True is insecure for a production environment.

## How to run
- To run the docs AND the django backend: docker-compose up
- To update the local database: docker-compose exec backend python manage.py migrate