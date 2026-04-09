// Make a copy of this and replace values as needed. If you are adding object IDs for Entra admins (dbAdminObjectIds),
// do NOT push your local version to github! Add it to gitignore and only use it locally.

using './main.bicep'

// Toggle manual vs automatic DB setup in case of permission issues
param runAutomatedDbIdentitySetup = true

// Resource naming parameters
param sites_code_the_clinic_name = 'code-the-clinic'
param serverfarms_ASP_capstone_976d_name = 'ASP-capstone-976d'
param vaults_code_the_clinic_vault_name = 'code-the-clinic-vault'
param virtualNetworks_code_the_clinic_vnet_name = 'code-the-clinic-vnet'
param privateEndpoints_code_the_clinic_db_pe_name = 'code-the-clinic-db-pe'
param flexibleServers_code_the_clinic_db_name = 'code-the-clinic-db'
param privateDnsZones_privatelink_postgres_database_azure_com_name = 'privatelink.postgres.database.azure.com'

// Location parameters
param location = 'East US'
param locationLower = 'eastus'

// Networking parameters
param networkAddressSpace = '10.0.0.0/16'
param subnetDefault = '10.0.0.0/24'
param subnetAppService = '10.0.1.0/26'
param subnetDeploymentScript = '10.0.2.0/27'
param vaultSubnetIpAddress = '130.160.194.1/32'

// Application parameters
param containerImage = 'ghcr.io/code-the-clinic/code-the-clinic:main'
param containerPort = '8000'
// siteContainerUserName: Used for pulling container from GHCR into Azure.
// Must be a GitHub username for someone who has permissions on the repository,
// and they will need to enter a personal access token in Azure later (instructions
// in deployment-docs.md) to give the App Service permission to pull from GHCR
param siteContainerUserName = 'your-github-username'
param minTlsVersion = '1.2'
param healthCheckPath = '/health/'

// Environment variables (replace items in <brackets> as needed)
param allowedDomains = '<comma-separated string of university email domains>'
param allowedHosts = 'localhost,127.0.0.1,0.0.0.0,<app-service-public-domain>,<app-service-ip-address>'
param csrfTrustedOrigins = '<app-service-public-domain>'

// Database parameters
// param dbAdminObjectIds = []  // Uncomment and add Entra user/group object IDs to auto-add DB admins
