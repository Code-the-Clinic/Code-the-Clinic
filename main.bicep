// Resource naming parameters
param sites_code_the_clinic_name string
param serverfarms_ASP_capstone_976d_name string
param vaults_code_the_clinic_vault_name string
param virtualNetworks_code_the_clinic_vnet_name string
param privateEndpoints_code_the_clinic_db_pe_name string
param flexibleServers_code_the_clinic_db_name string
param privateDnsZones_privatelink_postgres_database_azure_com_name string

// Location parameters
param location string
param locationLower string

// Networking parameters
param networkAddressSpace string
param subnetDefault string
param subnetAppService string
param subnetDeploymentScript string
param vaultSubnetIpAddress string

// Application parameters
param containerImage string
param containerPort string
param siteContainerUserName string
param minTlsVersion string = '1.2'
param healthCheckPath string = '/health/'

// Environment variables (not secrets--secrets are stored in Key Vault!)
param allowedDomains string
param allowedHosts string
param csrfTrustedOrigins string

// Database parameters
param tenantId string = subscription().tenantId
@description('The Object ID of the Entra user/group to be the DB Admin')
param dbAdminObjectIds array = []

resource flexibleServers_code_the_clinic_db_name_resource 'Microsoft.DBforPostgreSQL/flexibleServers@2025-01-01-preview' = {
  name: flexibleServers_code_the_clinic_db_name
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    replica: {
      role: 'Primary'
    }
    storage: {
      iops: 120
      tier: 'P4'
      storageSizeGB: 32
      autoGrow: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Enabled'
    }
    dataEncryption: {
      type: 'SystemManaged'
    }
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenantId
    }
    version: '15'
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    maintenanceWindow: {
      customWindow: 'Disabled'
      dayOfWeek: 0
      startHour: 0
      startMinute: 0
    }
    replicationRole: 'Primary'
  }
}

resource privateDnsZones_privatelink_postgres_database_azure_com_name_resource 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: privateDnsZones_privatelink_postgres_database_azure_com_name
  location: 'global'
  properties: {}
}

resource virtualNetworks_code_the_clinic_vnet_name_resource 'Microsoft.Network/virtualNetworks@2024-07-01' = {
  name: virtualNetworks_code_the_clinic_vnet_name
  location: locationLower
  properties: {
    addressSpace: {
      addressPrefixes: [
        networkAddressSpace
      ]
    }
    encryption: {
      enabled: false
      enforcement: 'AllowUnencrypted'
    }
    privateEndpointVNetPolicies: 'Disabled'
    subnets: [
      {
        name: 'default'
        properties: {
          addressPrefixes: [
            subnetDefault
          ]
          delegations: []
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: 'app-service-subnet'
        properties: {
          addressPrefixes: [
            subnetAppService
          ]
          serviceEndpoints: [
            {
              service: 'Microsoft.KeyVault'
              locations: [
                '*'
              ]
            }
            {
              service: 'Microsoft.Sql'
              locations: [
                locationLower
              ]
            }
          ]
          delegations: [
            {
              name: 'Microsoft.Web/serverFarms'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
      {
        name: 'deployment-script-subnet'
        properties: {
          addressPrefixes: [
            subnetDeploymentScript
          ]
          serviceEndpoints: []
          delegations: [
            {
              name: 'Microsoft.ContainerInstance.containerGroups'
              properties: {
                serviceName: 'Microsoft.ContainerInstance/containerGroups'
              }
            }
          ]
          privateEndpointNetworkPolicies: 'Disabled'
          privateLinkServiceNetworkPolicies: 'Enabled'
        }
      }
    ]
    virtualNetworkPeerings: []
    enableDdosProtection: false
  }
}

resource serverfarms_ASP_capstone_976d_name_resource 'Microsoft.Web/serverfarms@2024-11-01' = {
  name: serverfarms_ASP_capstone_976d_name
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
    size: 'B1'
    family: 'B'
    capacity: 1
  }
  kind: 'linux'
  properties: {
    perSiteScaling: false
    elasticScaleEnabled: false
    maximumElasticWorkerCount: 1
    isSpot: false
    reserved: true
    isXenon: false
    hyperV: false
    targetWorkerCount: 0
    targetWorkerSizeId: 0
    zoneRedundant: false
    asyncScalingEnabled: false
  }
}

// Create Entra admins (put teammates' object IDs in dbAdminObjectIds)
resource postgresAdmin 'Microsoft.DBforPostgreSQL/flexibleServers/administrators@2025-01-01-preview' = [for (adminId, i) in dbAdminObjectIds: {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: adminId
  properties: {
    principalName: 'Admin-${i}' // Generic label for the portal
    principalType: 'User'
    tenantId: tenantId
  }
}]

resource flexibleServers_code_the_clinic_db_name_Default 'Microsoft.DBforPostgreSQL/flexibleServers/advancedThreatProtectionSettings@2025-01-01-preview' = {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: 'Default'
  properties: {
    state: 'Disabled'
  }
}

resource flexibleServers_code_the_clinic_db_name_flexibleServers_code_the_clinic_db_name 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-01-01-preview' = {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: flexibleServers_code_the_clinic_db_name
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// Temporary bootstrap rule so Azure-hosted deployment script can reach PostgreSQL public endpoint.
// Remove/lock down after deployment, then disable public network access again.
resource flexibleServerAllowAzureServices 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2025-01-01-preview' = {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource vaults_code_the_clinic_vault_name_resource 'Microsoft.KeyVault/vaults@2024-12-01-preview' = {
  name: vaults_code_the_clinic_vault_name
  location: locationLower
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    networkAcls: {
      bypass: 'AzureServices'
      defaultAction: 'Deny'
      ipRules: [
        {
          value: vaultSubnetIpAddress
        }
      ]
      virtualNetworkRules: [
        {
          id: '${virtualNetworks_code_the_clinic_vnet_name_resource.id}/subnets/app-service-subnet'
          ignoreMissingVnetServiceEndpoint: false
        }
      ]
    }
    accessPolicies: []
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    enableRbacAuthorization: true
    vaultUri: 'https://${vaults_code_the_clinic_vault_name}${environment().suffixes.keyvaultDns}'
    provisioningState: 'Succeeded'
    publicNetworkAccess: 'Enabled'
  }
}

resource vaults_code_the_clinic_vault_name_azure_client_id 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'azure-client-id'
  properties: {
    value: ''
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_azure_secret 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'azure-secret'
  properties: {
    value: ''
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_azure_tenant_id 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'azure-tenant-id'
  properties: {
    value: tenantId
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_db_host 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'db-host'
  properties: {
    value: '${flexibleServers_code_the_clinic_db_name_resource.name}.postgres.database.azure.com'
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_django_secret_key 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'django-secret-key'
  properties: {
    value: ''
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_postgres_db 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'postgres-db'
  properties: {
    value: flexibleServers_code_the_clinic_db_name_resource.name
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_postgres_user 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'postgres-user'
  properties: {
    value: sites_code_the_clinic_name_resource.name
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_microsoft_login_client_id 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'microsoft-login-client-id'
  properties: {
    value: ''
    attributes: {
      enabled: true
    }
  }
}

resource Microsoft_Network_privateDnsZones_SOA_privateDnsZones_privatelink_postgres_database_azure_com_name 'Microsoft.Network/privateDnsZones/SOA@2024-06-01' = {
  parent: privateDnsZones_privatelink_postgres_database_azure_com_name_resource
  name: '@'
  properties: {
    ttl: 3600
    soaRecord: {
      email: 'azureprivatedns-host.microsoft.com'
      expireTime: 2419200
      host: 'azureprivatedns.net'
      minimumTtl: 10
      refreshTime: 3600
      retryTime: 300
      serialNumber: 1
    }
  }
}

resource sites_code_the_clinic_name_ftp 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: sites_code_the_clinic_name_resource
  name: 'ftp'
  properties: {
    allow: false
  }
}

resource sites_code_the_clinic_name_scm 'Microsoft.Web/sites/basicPublishingCredentialsPolicies@2024-11-01' = {
  parent: sites_code_the_clinic_name_resource
  name: 'scm'
  properties: {
    allow: false
  }
}

resource sites_code_the_clinic_name_web 'Microsoft.Web/sites/config@2024-11-01' = {
  parent: sites_code_the_clinic_name_resource
  name: 'web'
  properties: {
    numberOfWorkers: 1
    defaultDocuments: [
      'Default.htm'
      'Default.html'
      'Default.asp'
      'index.htm'
      'index.html'
      'iisstart.htm'
      'default.aspx'
      'index.php'
      'hostingstart.html'
    ]
    netFrameworkVersion: 'v4.0'
    linuxFxVersion: 'sitecontainers'
    requestTracingEnabled: false
    remoteDebuggingEnabled: false
    remoteDebuggingVersion: 'VS2022'
    httpLoggingEnabled: true
    acrUseManagedIdentityCreds: false
    logsDirectorySizeLimit: 35
    detailedErrorLoggingEnabled: false
    publishingUsername: 'REDACTED'
    scmType: 'None'
    use32BitWorkerProcess: true
    webSocketsEnabled: false
    alwaysOn: false
    managedPipelineMode: 'Integrated'
    virtualApplications: [
      {
        virtualPath: '/'
        physicalPath: 'site\\wwwroot'
        preloadEnabled: false
      }
    ]
    loadBalancing: 'LeastRequests'
    experiments: {
      rampUpRules: []
    }
    autoHealEnabled: false
    vnetName: 'app-service-subnet'
    vnetRouteAllEnabled: true
    vnetPrivatePortsCount: 0
    publicNetworkAccess: 'Enabled'
    localMySqlEnabled: false
    managedServiceIdentityId: 13915
    ipSecurityRestrictions: [
      {
        ipAddress: 'Any'
        action: 'Allow'
        priority: 2147483647
        name: 'Allow all'
        description: 'Allow all access'
      }
    ]
    scmIpSecurityRestrictions: [
      {
        ipAddress: 'Any'
        action: 'Allow'
        priority: 2147483647
        name: 'Allow all'
        description: 'Allow all access'
      }
    ]
    scmIpSecurityRestrictionsUseMain: false
    http20Enabled: false
    minTlsVersion: minTlsVersion
    scmMinTlsVersion: minTlsVersion
    ftpsState: 'Disabled'
    preWarmedInstanceCount: 0
    elasticWebAppScaleLimit: 0
    healthCheckPath: healthCheckPath
    functionsRuntimeScaleMonitoringEnabled: false
    minimumElasticInstanceCount: 1
    azureStorageAccounts: {}
    http20ProxyFlag: 0
  }
}

resource sites_code_the_clinic_name_main 'Microsoft.Web/sites/sitecontainers@2024-11-01' = {
  parent: sites_code_the_clinic_name_resource
  name: 'main'
  properties: {
    image: containerImage
    targetPort: containerPort
    isMain: true
    authType: 'UserCredentials'
    userName: siteContainerUserName
    volumeMounts: []
    environmentVariables: []
    inheritAppSettingsAndConnectionStrings: true
  }
}

resource privateDnsZones_privatelink_postgres_database_azure_com_name_gbuncm7wbtfng 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: privateDnsZones_privatelink_postgres_database_azure_com_name_resource
  name: 'gbuncm7wbtfng'
  location: 'global'
  properties: {
    registrationEnabled: false
    resolutionPolicy: 'Default'
    virtualNetwork: {
      id: virtualNetworks_code_the_clinic_vnet_name_resource.id
    }
  }
}

resource privateEndpoints_code_the_clinic_db_pe_name_resource 'Microsoft.Network/privateEndpoints@2024-07-01' = {
  name: privateEndpoints_code_the_clinic_db_pe_name
  location: locationLower
  properties: {
    privateLinkServiceConnections: [
      {
        name: privateEndpoints_code_the_clinic_db_pe_name
        properties: {
          privateLinkServiceId: flexibleServers_code_the_clinic_db_name_resource.id
          groupIds: [
            'postgresqlServer'
          ]
          privateLinkServiceConnectionState: {
            status: 'Approved'
            description: 'Auto-Approved'
          }
        }
      }
    ]
    manualPrivateLinkServiceConnections: []
    customNetworkInterfaceName: '${privateEndpoints_code_the_clinic_db_pe_name}-nic'
    subnet: {
      id: '${virtualNetworks_code_the_clinic_vnet_name_resource.id}/subnets/default'
    }
    ipConfigurations: []
    customDnsConfigs: []
  }
}

resource privateEndpoints_code_the_clinic_db_pe_name_default 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-07-01' = {
  parent: privateEndpoints_code_the_clinic_db_pe_name_resource
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'privatelink-postgres-database-azure-com'
        properties: {
          privateDnsZoneId: privateDnsZones_privatelink_postgres_database_azure_com_name_resource.id
        }
      }
    ]
  }
}

resource sites_code_the_clinic_name_resource 'Microsoft.Web/sites@2024-11-01' = {
  name: sites_code_the_clinic_name
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    enabled: true
    hostNameSslStates: [
      {
        name: '${sites_code_the_clinic_name}.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Standard'
      }
      {
        name: '${sites_code_the_clinic_name}.scm.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Repository'
      }
    ]
    serverFarmId: serverfarms_ASP_capstone_976d_name_resource.id
    reserved: true
    isXenon: false
    hyperV: false
    dnsConfiguration: {}
    outboundVnetRouting: {
      allTraffic: false
      applicationTraffic: true
      contentShareTraffic: false
      imagePullTraffic: false
      backupRestoreTraffic: false
    }
    siteConfig: {
      numberOfWorkers: 1
      linuxFxVersion: 'sitecontainers'
      acrUseManagedIdentityCreds: false
      alwaysOn: false
      http20Enabled: false
      functionAppScaleLimit: 0
      minimumElasticInstanceCount: 1
    }
    scmSiteAlsoStopped: false
    clientAffinityEnabled: false
    clientAffinityProxyEnabled: false
    clientCertEnabled: false
    clientCertMode: 'Required'
    hostNamesDisabled: false
    ipMode: 'IPv4'
    // customDomainVerificationId: 'REPLACE_WITH_YOUR_CUSTOM_DOMAIN_VERIFICATION_ID' // Set this when using custom domains
    containerSize: 0
    dailyMemoryTimeQuota: 0
    httpsOnly: true
    endToEndEncryptionEnabled: false
    redundancyMode: 'None'
    publicNetworkAccess: 'Enabled'
    storageAccountRequired: false
    virtualNetworkSubnetId: '${virtualNetworks_code_the_clinic_vnet_name_resource.id}/subnets/app-service-subnet'
    keyVaultReferenceIdentity: 'SystemAssigned'
    autoGeneratedDomainNameLabelScope: 'TenantReuse'
    sshEnabled: true
  }
}

// Set app environment variables
resource siteConfigSettings 'Microsoft.Web/sites/config@2024-11-01' = {
  name: 'appsettings'
  parent: sites_code_the_clinic_name_resource
  properties: {
    // Values read from Key Vault
    AZURE_SECRET: '@Microsoft.KeyVault(VaultName=${vaults_code_the_clinic_vault_name_resource.name};SecretName=azure-secret)'
    AZURE_TENANT_ID: '@Microsoft.KeyVault(VaultName=${vaults_code_the_clinic_vault_name_resource.name};SecretName=azure-tenant-id)'
    DJANGO_SECRET_KEY: '@Microsoft.KeyVault(VaultName=${vaults_code_the_clinic_vault_name_resource.name};SecretName=django-secret-key)'
    MICROSOFT_LOGIN_CLIENT_ID: '@Microsoft.KeyVault(VaultName=${vaults_code_the_clinic_vault_name_resource.name};SecretName=microsoft-login-client-id)'
    POSTGRES_DB: '@Microsoft.KeyVault(VaultName=${vaults_code_the_clinic_vault_name_resource.name};SecretName=postgres-db)'
    POSTGRES_HOST: '@Microsoft.KeyVault(VaultName=${vaults_code_the_clinic_vault_name_resource.name};SecretName=db-host)'
    POSTGRES_USER: '@Microsoft.KeyVault(VaultName=${vaults_code_the_clinic_vault_name_resource.name};SecretName=postgres-user)'

    // Regular environment variables (no Key Vault needed)
    DEBUG: 'False' // Always set DEBUG=False in production
    ALLOWED_DOMAINS: allowedDomains
    ALLOWED_HOSTS: allowedHosts
    CSRF_TRUSTED_ORIGINS: csrfTrustedOrigins
    PORT: '8000'
    WEBSITE_HEALTHCHECK_MAXPINGFAILURES: '10'
    WEBSITE_HTTPLOGGING_RETENTION_DAYS: '10'
    WEBSITES_ENABLE_APP_SERVICE_STORAGE: 'false'
    WEBSITES_PORT: '8000'
  }
}

resource sites_code_the_clinic_name_app_service_subnet_connection 'Microsoft.Web/sites/virtualNetworkConnections@2024-11-01' = {
  parent: sites_code_the_clinic_name_resource
  name: 'app-service-subnet'
  properties: {
    vnetResourceId: '${virtualNetworks_code_the_clinic_vnet_name_resource.id}/subnets/app-service-subnet'
    isSwift: true
  }
}

resource kvRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(vaults_code_the_clinic_vault_name_resource.id, sites_code_the_clinic_name_resource.id, 'Key Vault Secrets User')
  scope: vaults_code_the_clinic_vault_name_resource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // ID for "Key Vault Secrets User"
    principalId: sites_code_the_clinic_name_resource.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource deploymentScriptUserAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${sites_code_the_clinic_name}-dbscript-mi'
  location: location
}

resource deploymentScriptServerContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(flexibleServers_code_the_clinic_db_name_resource.id, deploymentScriptUserAssignedIdentity.id, 'Contributor')
  scope: flexibleServers_code_the_clinic_db_name_resource
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', 'b24988ac-6180-42a0-ab88-20f7382dd24c') // Contributor
    principalId: deploymentScriptUserAssignedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource dbIdentitySetupScript 'Microsoft.Resources/deploymentScripts@2023-08-01' = {
  name: '${sites_code_the_clinic_name}-db-identity-setup'
  location: location
  kind: 'AzureCLI'
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${deploymentScriptUserAssignedIdentity.id}': {}
    }
  }
  properties: {
    azCliVersion: '2.63.0'
    timeout: 'PT30M'
    cleanupPreference: 'OnSuccess'
    retentionInterval: 'P1D'
    environmentVariables: [
      {
        name: 'DB_HOST'
        value: '${flexibleServers_code_the_clinic_db_name_resource.name}.postgres.database.azure.com'
      }
      {
        name: 'DB_NAME'
        value: flexibleServers_code_the_clinic_db_name_resource.name
      }
      {
        name: 'RESOURCE_GROUP_NAME'
        value: resourceGroup().name
      }
      {
        name: 'SUBSCRIPTION_ID'
        value: subscription().subscriptionId
      }
      {
        name: 'ARM_ENDPOINT'
        value: environment().resourceManager
      }
      {
        name: 'TENANT_ID'
        value: tenantId
      }
      {
        name: 'APP_SERVICE_NAME'
        value: sites_code_the_clinic_name_resource.name
      }
      {
        name: 'APP_OBJECT_ID'
        value: sites_code_the_clinic_name_resource.identity.principalId
      }
      {
        name: 'SCRIPT_MI_NAME'
        value: deploymentScriptUserAssignedIdentity.name
      }
      {
        name: 'SCRIPT_MI_PRINCIPAL_ID'
        value: deploymentScriptUserAssignedIdentity.properties.principalId
      }
      {
        name: 'SCRIPT_MI_CLIENT_ID'
        value: deploymentScriptUserAssignedIdentity.properties.clientId
      }
    ]
    scriptContent: '''
#!/usr/bin/env bash
set -euo pipefail

echo "Ensuring PostgreSQL client (psql) is available..."
if ! command -v psql >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update -y && apt-get install -y postgresql-client
  elif command -v tdnf >/dev/null 2>&1; then
    tdnf install -y postgresql
  elif command -v yum >/dev/null 2>&1; then
    yum install -y postgresql
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y postgresql
  elif command -v apk >/dev/null 2>&1; then
    apk add --no-cache postgresql-client
  else
    echo "No supported package manager found to install psql."
    exit 1
  fi
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is still unavailable after installation attempt."
  exit 1
fi

echo "Signing in with deployment script managed identity..."
az login --identity --username "$SCRIPT_MI_CLIENT_ID" --allow-no-subscriptions 1>/dev/null

echo "Setting deployment script managed identity as PostgreSQL Entra admin..."
az rest --method PUT \
  --url "${ARM_ENDPOINT}/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP_NAME}/providers/Microsoft.DBforPostgreSQL/flexibleServers/${DB_NAME}/administrators/${SCRIPT_MI_PRINCIPAL_ID}?api-version=2025-01-01-preview" \
  --body "{\"properties\":{\"principalName\":\"${SCRIPT_MI_NAME}\",\"principalType\":\"ServicePrincipal\",\"tenantId\":\"${TENANT_ID}\"}}" 1>/dev/null

echo "Waiting for PostgreSQL Entra admin propagation..."
sleep 45

echo "Getting PostgreSQL Entra token..."
export PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv)

echo "Applying DB identity mapping and grants for $APP_SERVICE_NAME..."
psql "host=$DB_HOST port=5432 dbname=postgres user=$SCRIPT_MI_NAME sslmode=require" -v ON_ERROR_STOP=1 -v app_role="$APP_SERVICE_NAME" -v app_oid="$APP_OBJECT_ID" -v db_name="$DB_NAME" <<'SQL'
SELECT format('CREATE ROLE %I WITH LOGIN', :'app_role')
WHERE NOT EXISTS (
  SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = :'app_role'
) \gexec

SELECT format('SECURITY LABEL FOR pgaadauth ON ROLE %I IS %L', :'app_role', format('aadauth,oid=%s,type=service', :'app_oid')) \gexec
SELECT format('GRANT CONNECT ON DATABASE %I TO %I', :'db_name', :'app_role') \gexec
SQL

psql "host=$DB_HOST port=5432 dbname=$DB_NAME user=$SCRIPT_MI_NAME sslmode=require" -v ON_ERROR_STOP=1 -v app_role="$APP_SERVICE_NAME" <<'SQL'
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT CREATE ON SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO %I', :'app_role') \gexec
SELECT format('GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO %I', :'app_role') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO %I', :'app_role') \gexec
SELECT format('ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO %I', :'app_role') \gexec
SQL

echo "Identity setup complete."

echo ""
echo "Bootstrap complete! Post-deployment cleanup:"
echo "  1. Verify app works and can access database"
echo "  2. DISABLE PostgreSQL public network access (set to 'Disabled')"
echo "  3. Remove deployment script MI from PostgreSQL Entra admins"
echo "  4. Remove Contributor role from deployment script MI on PostgreSQL server"
'''
  }
  dependsOn: [
    deploymentScriptServerContributorRoleAssignment
    flexibleServerAllowAzureServices
    flexibleServers_code_the_clinic_db_name_flexibleServers_code_the_clinic_db_name
    privateEndpoints_code_the_clinic_db_pe_name_default
  ]
}
