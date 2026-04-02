---
hide:
  - navigation
---

# How to deploy the application
Hi! Here's how to run our application locally, run tests, and deploy it in the cloud. In case you need to change Azure accounts later (for example, to move the application fully into the university tenant), you can use the Azure CLI and the bicep template files we've included to deploy without spending hours clicking through Azure's terrible GUI :)

## Required setup tools
- Docker Desktop (needed to run Docker locally)
- VS Code or preferred IDE

## How to run in development
- Set up environment variables
    - Open .env-example and set the environment variables according to the guidelines (but do this in a different file, .env, and put .env in gitignore so that you don't expose any secrets.)
    - For Azure credentials, see the "How to get myBama auth working..." section--local Azure credentials are only needed if you want to test myBama auth locally
- To run the documentation website and the django backend: `docker-compose up`
- To run the documentation website and the django backend and rebuild the docker container (for example, if you added new dependencies to requirements.txt): `docker-compose up --build`
- To update the local database:
    - Create migration: `docker-compose exec backend python manage.py makemigrations clinic_reports`
        - Use the name of the data model instead of clinic_reports if updating a different model
    - Run migration: `docker-compose exec backend python manage.py migrate`
- To create a superuser (required to locally test the admin page without a Microsoft account): `docker-compose exec backend python manage.py createsuperuser`

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

## How to get myBama auth working in your local environment
- Get a personal Azure tenant ID and secret by creating an Azure account
    1. Create the app registration
        - In your personal Azure Portal (portal.azure.com), search for "App registrations" and click "New registration".
        - If you don’t have an Azure account and see something like “tenant blocked due to inactivity,” make a new Azure account, wait 5 minutes, and try again. 
        - Name: Doesn't matter, make this whatever you want 
        - Supported account types: Select the option that says: "Accounts in any organizational directory (Any Microsoft Entra ID tenant - Multitenant)". Do NOT select "Personal Microsoft accounts only". 
        - Redirect URI: (For local development) Select Web and enter http://localhost:8000/accounts/microsoft/login/callback/. This allows us to test myBama auth locally.
        - Click Register. 

    2. Get your keys
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
az stack group create --name clinic-test-stack --resource-group <new-resource-group> --template-file main.bicep --parameters main-local.bicepparam --deny-settings-mode none --action-on-unmanage deleteAll
```

- NOTE: If the deployment fails midway through and you want a fresh start, if you used the second command (az stack group create ...) you can use this command to delete all the resources created via the deployment command. ONLY use this if you want to delete all the resources you just tried to deploy.

```bash
az stack group delete --name clinic-test-stack --resource-group <rg-name> --action-on-unmanage deleteAll
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
    - django-secret-key
        - Generate a new one with this command: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())`
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
    - CSRF_TRUSTED_ORIGINS = 'https://<domain-of-app-service-application>
    - ALLOW_PASSWORD_ADMIN_LOGIN = False (if you need to allow admin login with username/password in an emergency, you can set this to True later.)
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
- [IMPORTANT] Remove public access to the database
    - Go to the database => Networking and disable public access (the DB and the App Service will still be able to communicate via their shared VNET). If you ever need to connect to the database and run SQL, you can temporarily re-enable public access, but only allow your client IP--not access from all networks. Also, make sure to disable public access again as soon as you are done.
    - Recommended: Also delete the AllowAzureServices firewall rule, since after initial setup only the app service should be able to access the DB.
- [IMPORTANT] Make sure Key Vault access is restricted to only the virtual network containing the app service (you can check this in the key vault's Networking settings)
    - If there are any rules listed under Firewall, you can safely delete them--you only need the "code-the-clinic-vnet-test" or similar under Virtual Network Rules.
- Once you are a Django admin, open the Excel file [Dropdown Options.xlsx](https://bama365-my.sharepoint.com/:x:/g/personal/hrhendersonboyer_crimson_ua_edu/IQByqE9LpDuiSqtylUDZcGq5AWHkIQcn_vfJskrzJZno9HU?e=qZJt1R) from the AT department, and then go to the Django admin portal. Add the list under "Clinical Sites" as new Sport records under the Sports section of the admin portal, and add the list under "Other Health Professions" as new Healthcare Provider records under the Healthcare Providers section of the admin portal.

### Smoke testing
- If you are experiencing HTTP errors and need to get clear error messages, you can temporarily set DEBUG=True in the App Service's environment variables. However, this makes the application more vulnerable since an attacker could see exactly what was preventing them from accessing a certain page. For this reason, you should immediately change DEBUG back to False after testing, and ideally never set DEBUG=True in the Azure portal at all (just do your testing locally instead).
- If the app service isn't starting, you can see detailed logs in "log stream" under the App Service settings => Monitoring. You should be able to see "platform logs" (logs from the underlying server that is running the app) and "runtime logs" (logs from the app itself). If you don't see any runtime logs, check the platform logs to see what might be going wrong. Platform logs are where you would see problems pulling the Docker container from GitHub Container Registry or problems pinging the app for health checks. Runtime logs are where you would see Django errors (failed to run migrations, normal website errors like 403/400/etc.)

### Troubleshooting and known issues
- If the app seems to start (check runtime Log Stream in the app service for gunicorn logs) but you are getting "gateway timeout" or "application error" because Azure is failing to ping the application, check Deployment Center => Containers => main => Port and make sure it is set to 8000. If it isn't set to 8000, Azure will ping the wrong port and won't be able to reach Django.

## Future considerations
- Entra to Okta auth migration
- Add teammates as key vault secrets officers
- Automate Azure app service app restart after new code changes

# Info about the cloud deployment
## Primary Azure resources + descriptions
### Azure App Service
The App Service resource is where the Django application is hosted. It provides a web address for the application and a managed virtual machine that runs our Docker container. It also uses a GitHub Personal Access Token (PAT) to get permission from GitHub to pull our auto-built Docker container from the GitHub Container Registry. (If you are curious about how our Docker auto-build process works, it happens every time you merge a PR into `main`, and the code that runs it is located in `deploy.yml`.)

### Azure Database for PostgreSQL
This is the database that stores all the information collected via the clinic report form. It communicates with the App Service via a secure virtual network (VNet) that only the database, App Service, and Key Vault have access to.

### Key Vault
This is a secrets manager that stores sensitive deployment information like Django and Azure credentials. Key Vault uses the same VNet to connect to the App Service so that the application can pull secrets from Key Vault as if they were normal environment variables, while maintaining stronger security than a standard environment variable.

### VNet + private endpoint
The App Service, database, and Key Vault all use a shared VNet to communicate with each other so that traffic between these resources isn't exposed to the public internet. The database connects to the VNet using a private endpoint, whereas the App Service and Key Vault use built-in VNet integration.

## How to update the cloud app
- Merge code changes into the main branch of the repo--this will auto-build a Docker container and push it to the GitHub Container Registry
- Go into the Azure portal, navigate to the App Service resource for your cloud deployment (may be called code-the-clinic or similar) and click "restart" under the Overview tab. This will force the app to restart and pull the latest version of the Docker container from GitHub. You may also need to navigate to the app's website and reload it a couple of times to get the webpage to "fetch" the new version of the code.