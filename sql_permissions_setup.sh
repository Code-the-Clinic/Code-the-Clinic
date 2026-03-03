# Replace variables in <brackets> with the actual names
# 1. Set your variables (Match these to your Bicep outputs)
export DB_HOST="codetheclinicdbtest.postgres.database.azure.com"
export DB_NAME="codetheclinicdbtest"
export DB_NAME_DEFAULT = "postgres"
export DB_USER=$(az ad signed-in-user show --query "userPrincipalName" -o tsv)
export APP_SERVICE_NAME="code-the-clinic-test"

# 2. Fetch the Entra Access Token (This is your temporary password)
export PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms --query "[accessToken]" -o tsv)

# 3. Create the SQL file in the Cloud Shell
cat <<EOF > init_db_permissions.sql
-- 1. Ensure the extension is actually active in THIS database
CREATE EXTENSION IF NOT EXISTS pgaadauth;

-- 2. Use the FULL PATH to the function to avoid "not found" errors
DO \$\$
BEGIN
    -- Calling the function with the public schema prefix
    PERFORM pgaadauth_create_principal('$APP_SERVICE_NAME', false, false);
EXCEPTION
    WHEN duplicate_object THEN
        NULL;
    WHEN undefined_function THEN
        -- Fallback: try calling it without the prefix if the extension 
        -- was already installed elsewhere
        PERFORM public.pgaadauth_create_principal('$APP_SERVICE_NAME', false, false);
END \$\$;

GRANT CONNECT ON DATABASE "$DB_NAME" TO "$APP_SERVICE_NAME";
GRANT USAGE ON SCHEMA public TO "$APP_SERVICE_NAME";
GRANT CREATE ON SCHEMA public TO "$APP_SERVICE_NAME";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "$APP_SERVICE_NAME";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "$APP_SERVICE_NAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO "$APP_SERVICE_NAME";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO "$APP_SERVICE_NAME";
EOF

# 4. Execute the script
psql "host=$DB_HOST port=5432 dbname=$DB_NAME user=$DB_USER sslmode=require" -f init_db_permissions.sql