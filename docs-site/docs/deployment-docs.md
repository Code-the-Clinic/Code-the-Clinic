---
hide:
  - navigation
---

# How to deploy the application
Hi! Here's how to run our application locally, run tests, and deploy it in the cloud. In case you need to change Azure accounts later (for example, to move the application into the university tenant), you can use the Azure CLI and the bicep template files we've included to deploy without spending hours clicking through Azure's terrible GUI :)

## How to run in development
- To run the docs and the main application: `docker-compose up`
- To run the docs and the main application and rebuild the docker container (for example, if you added new dependencies to requirements.txt): `docker-compose up --build`
- To update the local database:
    - Create migration: `docker-compose exec backend python manage.py makemigrations clinic_reports`
        - Use the name of the data model instead of clinic_reports if updating a different model (for example, core)
    - Run migration: `docker-compose exec backend python manage.py migrate`
- To create a superuser (required to locally test the admin page without a Microsoft account): docker-compose exec backend python manage.py createsuperuser

## How to test
- To run all tests: `docker-compose exec backend python manage.py test`
- To run all tests for a specific app (currently our only two apps are clinic_reports and core): `docker-compose exec backend python manage.py test app-name`
    - For example, `python manage.py test clinic_reports` would run all the tests under the clinic_reports app (these check whether the form authentication and submission logic works correctly).

## How to debug locally
- If you are getting Django import errors after force-quitting and restarting Docker Desktop, try these steps to force re-creating all Docker containers without cache (in case the cache got corrupted during the abrupt restart). WARNING: This will delete all the records in your local database! NEVER use this method in production--only in local development!
`docker-compose down -v` (removes all containers and deletes all associated volumes)
`docker system prune -f` (removes all unused data)
`docker-compose up --build` (rebuilds all the containers without caching)
- If you are getting DB errors that the relation "django-session" doesn't exist, you need to run the migration command listed in the "how to run" section to recreate all the tables that Django expects to be in the database.

## How to get myBama auth working (locally--it should "just work" in the cloud)
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

## How to deploy to the cloud

### Pre-deployment todos
- Fill in environment variables in main.bicepparam (before doing this, make your own local copy of main.bicepparam (main-local.bicepparam) that is gitignored so so environment variables aren't in a public github)

### Deploying the application
- Run `az login` to log into the Azure CLI and then select the subscription you want to copy the application into.
- Run this command in your terminal to deploy the bicep file to a new Azure resource group: 
```bash
az deployment group create \
    -g <new-azure-resource-group> \
    -f main.bicep \
    -p main.bicepparam
```
### Post-deployment todos (TODO: Add more detailed instructions for these)
- Add all secrets to Key Vault
- Run SQL to give the App Service permission to create a table in the DB
- Promote yourself to a superuser in Django (you will need to do this the first time you deploy the app so you can access the admin pages on the site)

### Smoke testing
- Go to "log stream" under the App Service settings. You should be able to see "platform logs" (logs from the underlying server that is running the app) and "runtime logs" (logs from the app itself). If you don't see any runtime logs, check the platform logs to see what might be going wrong. Platform logs are where you would see problems pulling the Docker container from GitHub Container Registry or problems pinging the app for health checks. Runtime logs are where you would see Django errors (failed to run migrations, normal website errors like 403/400/etc.)
### Troubleshooting and known issues
- If the app seems to start (check runtime Log Stream in the app service for gunicorn logs) but you are getting "gateway timeout" or "application error" because Azure is failing to ping the application, check Deployment Center => Containers => main => Port and make sure it is set to 8000. If it isn't set to 8000, Azure will ping the wrong port and won't be able to reach Django.

## Future considerations
- Entra to Okta auth migration
- Add teammates as key vault service officers