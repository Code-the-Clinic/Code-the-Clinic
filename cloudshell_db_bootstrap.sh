#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# Cloud Shell DB bootstrap for Code the Clinic
#
# Use this script from Azure Cloud Shell AFTER:
#   - main.bicep has been deployed with runAutomatedDbIdentitySetup = false
#   - You (or whoever runs this) is temporarily an Entra admin on the
#     PostgreSQL flexible server.
#
# This script will:
#   1. Fetch an Entra token for PostgreSQL (used as password)
#   2. Ensure the pgaadauth extension exists
#   3. Create a role matching the App Service name (if needed)
#   4. Apply the pgaadauth security label linking that role to the
#      App Service managed identity
#   5. Grant DB/schema/table/sequence permissions to that role
#
# After running, the App Service managed identity should be able to
# connect to the DB using Entra authentication.
# -----------------------------------------------------------------------------

# 1. Variables - update these to match your environment
#    You can copy most values from your bicep parameters.

# FQDN of the Postgres flexible server
DB_HOST="<db_name>.postgres.database.azure.com"
# Name of the application database (usually same as server name)
DB_NAME="<db_name>"             
# Name of the App Service (must match what Django uses as POSTGRES_USER)
APP_SERVICE_NAME="<app_service_name>"        
# Resource group containing the App Service
RESOURCE_GROUP="your-resource-group-here"
# Optional: if you already know the managed identity object ID for the App Service,
# you can set it here to avoid calling az webapp identity show (which may require extra permissions).
# Example: APP_OBJECT_ID="00000000-0000-0000-0000-000000000000"
APP_OBJECT_ID=""

# 2. Get your Entra principal and access token (you must be Postgres Entra admin)
echo "Fetching signed-in Entra user principal..."
DB_USER=$(az ad signed-in-user show --query "userPrincipalName" -o tsv)

if [ -z "${DB_USER:-}" ]; then
  echo "❌ Could not resolve signed-in Entra user (DB_USER). Are you logged in with az login?"
  exit 1
fi

echo "Fetching Entra access token for PostgreSQL..."
export PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms --query "[accessToken]" -o tsv)

if [ -z "${PGPASSWORD:-}" ]; then
  echo "❌ Could not obtain access token for PostgreSQL."
  exit 1
fi

# 3. Fetch or use the App Service managed identity object ID
if [ -n "${APP_OBJECT_ID:-}" ]; then
  echo "Using provided App Service object ID: ${APP_OBJECT_ID}"
else
  echo "Fetching managed identity principalId for App Service '${APP_SERVICE_NAME}' in resource group '${RESOURCE_GROUP}'..."
  APP_OBJECT_ID=$(az webapp identity show \
    --name "${APP_SERVICE_NAME}" \
    --resource-group "${RESOURCE_GROUP}" \
    --query principalId -o tsv)

  if [ -z "${APP_OBJECT_ID:-}" ]; then
    echo "❌ Error: Could not find App Service managed identity. Is system-assigned identity enabled on the App Service?"
    exit 1
  fi

  echo "Found App Service object ID: ${APP_OBJECT_ID}"
fi

# 4. Create role, apply security label, and grant permissions
#    We connect to the 'postgres' database for metadata (extension + label),
#    then to the application database for schema/table grants.

APP_ROLE="${APP_SERVICE_NAME}"

cat <<'SQL' | psql "host=${DB_HOST} port=5432 dbname=postgres user=${DB_USER} sslmode=require" \
  -v ON_ERROR_STOP=1 \
  -v app_role="${APP_ROLE}" \
  -v app_oid="${APP_OBJECT_ID}" \
  -v db_name="${DB_NAME}"
-- Create role for the App Service if it doesn't already exist
SELECT format('CREATE ROLE %I WITH LOGIN', :'app_role')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'app_role'
) \gexec

-- Apply security label tying the role to the App Service managed identity
SELECT format(
  'SECURITY LABEL FOR pgaadauth ON ROLE %I IS %L',
  :'app_role',
  format('aadauth,oid=%s,type=service', :'app_oid')
) \gexec

-- Grant CONNECT on the application database
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db_name', :'app_role') \gexec
SQL

# Now grant schema/table/sequence privileges inside the application database
cat <<'SQL' | psql "host=${DB_HOST} port=5432 dbname=${DB_NAME} user=${DB_USER} sslmode=require" \
  -v ON_ERROR_STOP=1 \
  -v app_role="${APP_ROLE}"
-- Basic schema and object permissions for the app role
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT CREATE ON SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %I', :'app_role') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO %I', :'app_role') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO %I', :'app_role') \gexec
SQL

echo "✅ DB identity bootstrap complete."
echo "The App Service managed identity '${APP_SERVICE_NAME}' should now be able to connect to '${DB_NAME}' on '${DB_HOST}' using Entra authentication."
