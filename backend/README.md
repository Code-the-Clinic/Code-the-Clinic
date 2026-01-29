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
- To create a superuser (required to locally test the admin page without a Microsoft account): docker-compose exec backend python manage.py createsuperuser

## How to get myBama auth working
- Get a personal Azure tenant ID and secret by creating an Azure account, or ask me for mine
- Put your Azure tenant ID and secret in .env (follow the instructions in .env-example)
- Go to /accounts/microsoft/login and it should let you authenticate with myBama
- If you want to be automatically logged in to the admin portal with myBama, you will need to follow these steps:
    - Log in with myBama--this will create a user in the system for you
    - Log out
    - Create a superuser with the above command
    - Log in to the admin portal as the superuser
    - Use the admin portal to give your myBama user superuser permissions
    - Delete the manually created superuser when you are done for security
    - Now when you log in with your crimson email you should automatically be able to see the admin dashboard!