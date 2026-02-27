// Make a copy of this and replace values as needed. If you are adding object IDs for Entra admins (dbAdminObjectIds),
// do NOT push your local version to github! Add it to gitignore and only use it locally.

using './main.bicep'

// Resource naming parameters
param sites_code_the_clinic_name = 'code-the-clinic'
param serverfarms_ASP_capstone_976d_name = 'ASP-capstone-976d'
param vaults_code_the_clinic_vault_name = 'code-the-clinic-vault'
param virtualNetworks_code_the_clinic_vnet_name = 'code-the-clinic-vnet'
param privateEndpoints_code_the_clinic_db_pe_name = 'code-the-clinic-db-pe'
param flexibleServers_code_the_clinic_db_name = 'code-the-clinic-db'
param privateDnsZones_privatelink_postgres_database_azure_com_name = 'privatelink.postgres.database.azure.com'

// Location parameters
param location = 'North Central US'
param locationLower = 'northcentralus'

// Networking parameters
param networkAddressSpace = '10.0.0.0/16'
param subnetDefault = '10.0.0.0/24'
param subnetAppService = '10.0.1.0/26'
param vaultSubnetIpAddress = '130.160.194.1/32'

// Application parameters
param containerImage = 'ghcr.io/code-the-clinic/code-the-clinic:main'
param containerPort = '8000'
param siteContainerUserName = 'supergeek57'

// Database parameters
// param dbAdminObjectIds = []  // Uncomment and add Entra user/group object IDs for DB admins
