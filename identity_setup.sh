# 1. Variables - Ensure these match your environment
export DB_HOST="codetheclinicdbtest.postgres.database.azure.com"
export DB_NAME="codetheclinicdbtest"
export APP_SERVICE_NAME="code-the-clinic-test"
export RESOURCE_GROUP="your-resource-group-name"

# 2. Get your University Admin credentials
export DB_USER=$(az ad signed-in-user show --query "userPrincipalName" -o tsv)
export PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms --query "[accessToken]" -o tsv)

# 3. Fetch the App Service Object ID (The "Missing Key")
echo "Fetching Object ID for $APP_SERVICE_NAME..."
export APP_OBJECT_ID=$(az webapp identity show --name "$APP_SERVICE_NAME" --resource-group "$RESOURCE_GROUP" --query principalId -o tsv)

if [ -z "$APP_OBJECT_ID" ]; then
    echo "❌ Error: Could not find Object ID. Is System Identity enabled on the App Service?"
    exit 1
fi

echo "Found Object ID: $APP_OBJECT_ID"

# 4. Apply the Security Label (The Handshake)
# We connect to 'postgres' because that's where the security metadata lives.
echo "Applying security label to link Entra ID to SQL role..."
psql "host=$DB_HOST port=5432 dbname=postgres user=$DB_USER sslmode=require" -c \
"SECURITY LABEL FOR pgaadauth ON ROLE \"$APP_SERVICE_NAME\" IS 'aadauth,oid=$APP_OBJECT_ID,type=service';"

echo "✅ Identity mapping complete!"