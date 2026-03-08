---
hide:
  - navigation
---

# How to deploy the application
Hi! Here's how to run our application locally, run tests, and deploy it in the cloud. In case you need to change Azure accounts later (for example, to move the application fully into the university tenant), you can use the Azure CLI and the bicep template files we've included to deploy without spending hours clicking through Azure's terrible GUI :)

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
- For dbAdminPrincipalName, run this command in Azure Cloud Shell or in your local terminal and copy/paste the result into your LOCAL bicepparam file: `az ad signed-in-user show --query "userPrincipalName" -o tsv`

### Deploying the application
- Run `az login` to log into the Azure CLI and then select the subscription you want to copy the application into.
- Run this command in your terminal to validate the bicep file and its associated params file for any errors:
```bash
az deployment group validate -g <new-resource-group> -f main.bicep -p main-local.bicepparam --query "properties.validationResultItems[?severity=='Error']"
```
- Run this command to preview the resources that will be created:
```bash
az deployment group what-if --resource-group <new-resource-group> -f main.bicep -p main-local.bicepparam
```
- Run either of these commands to deploy the bicep file to a new Azure resource group: 
```bash
az deployment group create \
    -g <new-azure-resource-group> \
    -f main.bicep \
    -p main.bicepparam
```
```bash
az stack group create --name clinic-test-stack --resource-group <new-resource-group> --template-file main.bicep --parameters main-local.bicepparam --deny-settings-mode none --action-on-unmanage detachAll
```
### Post-deployment todos
- Add yourself as a Key Vault Secrets Officer
    - Go to your Key Vault => Access control (IAM) => Role assignments => New role assignment => Assign yourself the Key Vault Secrets Officer role. This will let you view, add, and edit secrets, which you will need to do to set up the application.
- If you can't access the "Secrets" tab in your Key Vault because of a firewall rule:
    - Go into the networking tab and temporarily add your client IP address under firewall rules. If this doesn't work (for example, if you are on campus and using a UA IP that constantly changes), you can temporarily select "allow public access from all networks"--just make sure to change this back to the original secure setting (allow public access from specific virtual networks...") once you're done!
- Add all secrets to Key Vault
    - azure-client-id (Client ID from Azure app registration, NOT app service)
    - microsoft-login-client-id (same as azure-client-id)
    - azure-secret (Add a new client secret under your Azure app registration and add the secret to Key Vault)
    - azure-tenant-id (Tenant ID from Azure app registration, NOT app service)
        - If you aren't using a single-tenant setup for myBama authentication (i.e. the university's tenant), you can just set this to "common". Otherwise use the tenant ID from the Azure app registration.
    - django-secret-key (**TODO: Generate a new Django secret key and add it to Key Vault**)
    - postgres-db (This isn't really a secret--it can be moved outside of key vault if needed. Name of the database within your PostgreSQL server in Azure where your Django tables are. You can find your databases in your PostgreSQL server settings => Databases.)
    - db-host (the domain of your Postgre DB--can be found in the Overview section if you click on your Postgres DB in the Azure portal)
    - postgres-user (the name of the App Service, since the App Service uses a Managed Identity to communicate with the DB)
- Update environment variables (if needed) to match this state:
    - For variables that are in Key Vault, use a string like this: `@Microsoft.KeyVault(SecretUri=<https://<vault-name>.vault.azure.net/secrets/<secret-name>/)`
    - MICROSOFT_LOGIN_CLIENT_ID = In key vault (azure-client-id)
    - AZURE_SECRET = In key vault (azure-secret)
    - AZURE_TENANT_ID = In key vault (azure-tenant-id)
    - DJANGO_SECRET_KEY = In key vault (django-secret-key)
    - POSTGRES_DB = In key vault (postgres-db)
    - POSTGRES_HOST = In key vault (db-host)
    - POSTGRES_USER = In key vault (postgres-user)
    - ALLOWED_HOSTS = 'localhost,127.0.0.1,0.0.0.0,<domain-of-app-service-application>,https://<domain-of-app-service-application>'
    - Other environment variables should be OK to leave as the default values set in the template.
- Give the App Service permission to pull the latest Docker image from GHCR
    - Get GitHub Personal Access Token (PAT) with read:packages permission
    - Go to your new App Service => Deployment Center => click on "main" => paste the PAT into the password field and click "ok"
- NOTE: If the app isn't working at this point (after you restart it in the App Service overview page), temporarily swich DEBUG to True in the environment variables to see the stack trace. It's usually one of these problems:
    - You didn't add the App Service's domain to ALLOWED_HOSTS (this usually results in a 400 error). Try adding the exact domain listed in the error message to the ALLOWED_HOSTS environment variable and restart the app.
    - There was an issue with one of your Key Vault secrets and you fixed it, but the app isn't "seeing" it because it is just pulling a cached version of what's in Key Vault (this usually results in a 500 error). Try temporarily changing an environment variable and then changing it back--this should solve the problem.
    - You try to login with myBama and see a Microsoft login error page that says something about a redirect URL. Make sure that your App Service's domain (exactly as specified in the error message) is listed as a Redirect URL under the App Registration you are using for myBama auth.
    - You try to login with myBama and get a "cannot assign requested address" or similar OS error. If this happens, just refresh and try logging in again--this is a transient error that only happens once, and only happens for completely new users. After refreshing and re-authenticating, the app should work as expected.
- Promote yourself to a superuser in Django (you will need to do this the first time you deploy the app so you can access the admin pages on the site)
    - Temporarily add yourself as an Entra admin on the DB
        - If you didn't specify Entra administrators in the Bicep params: Go to the PostgreSQL server, Security => Authentication, and add yourself as an Entra administrator
    - Run these commands in the Azure Cloud Shell or local terminal, one at a time:
        ```bash
        USERNAME=$(az ad signed-in-user show --query "userPrincipalName" -o tsv)
        TOKEN=$(az account get-access-token --resource-type oss-rdbms --query "[accessToken]" -o tsv)
        az postgres flexible-server execute --name <postgres-server-name> --admin-user $USERNAME --admin-password $TOKEN --database-name=<db-name-should-be-same-as-postgres-server-name> --querytext "UPDATE auth_user SET is_staff = true, is_superuser = true WHERE email = '<your-crimson-email>';" 
        ```
    - Remove your Entra admin status in the PostgreSQL server settings
- [IMPORTANT] Remove public access to the database
    - Go to the database => Networking and disable public access (the DB and the App Service will still be able to communicate via their shared VNET)
    - Recommended: Also delete the AllowAzureServices firewall rule, since after initial setup only the app service should be able to access the DB.
- [IMPORTANT] Remove Contributor role assignment from the deployment-script managed identity (this identity was created solely to set up initial DB permissions and is no longer needed.)
- [IMPORTANT] Revoke Entra admin status from the "test-dbscript" managed identity
    - Run these commands in the Azure Cloud Shell or local terminal, one at a time:
        ```bash
        USERNAME=$(az ad signed-in-user show --query "userPrincipalName" -o tsv)
        TOKEN=$(az account get-access-token --resource-type oss-rdbms --query "[accessToken]" -o tsv)
        ```
    - Run this command twice, once with db-name="postgres" and once with db-name="postgresql-server-name":
        ```bash
        az postgres flexible-server execute --name <postgres-server-name> --admin-user $USERNAME --admin-password $TOKEN --database-name=<db-name> --querytext "REASSIGN OWNED BY \"code-the-clinic-test-dbscript-mi\" TO \"<your-admin-role>\"; DROP OWNED BY "code-the-clinic-test-dbscript-mi";
        ```
    - Then delete the managed identity from the Entra admin list under your PostgreSQL server => Authentication
    - (Recommended) Remove yourself as an Entra admin (you can always add yourself back later if there's an emergency where you need to directly access the DB)
- [IMPORTANT] Make sure Key Vault access is restricted to only the virtual network containing the app service (you can check this in the key vault's Networking settings)
- Once you are a Django admin, open the Excel file [Dropdown Options.xlsx](https://bama365-my.sharepoint.com/:x:/g/personal/hrhendersonboyer_crimson_ua_edu/IQByqE9LpDuiSqtylUDZcGq5AWHkIQcn_vfJskrzJZno9HU?e=qZJt1R) from the AT department, and then go to the Django admin portal. Add the list under "Clinical Sites" as new Sport records under the Sports section of the admin portal, and add the list under "Other Health Professions" as new Healthcare Provider records under the Healthcare Providers section of the admin portal.

### Smoke testing
- If you are experiencing HTTP errors and need to get clear error messages, you can temporarily set DEBUG=True in the App Service's environment variables. However, this makes the application more vulnerable since an attacker could see exactly what was preventing them from accessing a certain page. For this reason, you should immediately change DEBUG back to False after testing, and ideally never set DEBUG=True in the Azure portal at all (just do your testing locally instead).
- If the app service isn't starting, you can see detailed logs in "log stream" under the App Service settings => Monitoring. You should be able to see "platform logs" (logs from the underlying server that is running the app) and "runtime logs" (logs from the app itself). If you don't see any runtime logs, check the platform logs to see what might be going wrong. Platform logs are where you would see problems pulling the Docker container from GitHub Container Registry or problems pinging the app for health checks. Runtime logs are where you would see Django errors (failed to run migrations, normal website errors like 403/400/etc.)
### Troubleshooting and known issues
- If the app seems to start (check runtime Log Stream in the app service for gunicorn logs) but you are getting "gateway timeout" or "application error" because Azure is failing to ping the application, check Deployment Center => Containers => main => Port and make sure it is set to 8000. If it isn't set to 8000, Azure will ping the wrong port and won't be able to reach Django.

## Future considerations
- Entra to Okta auth migration
- Add teammates as key vault service officers