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
param vaultSubnetIpAddress string

// Application parameters
param containerImage string
param containerPort string
param siteContainerUserName string
param minTlsVersion string = '1.2'
param healthCheckPath string = '/health/'

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
      publicNetworkAccess: 'Disabled'
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


resource flexibleServers_code_the_clinic_db_name_azure_maintenance 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-01-01-preview' = {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: 'azure_maintenance'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource flexibleServers_code_the_clinic_db_name_azure_sys 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-01-01-preview' = {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: 'azure_sys'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
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

resource flexibleServers_code_the_clinic_db_name_postgres 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2025-01-01-preview' = {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: 'postgres'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

resource flexibleServers_code_the_clinic_db_name_flexibleServers_code_the_clinic_db_name_pe_c2060ad2_39f0_4ed2_8050_d0e4f8490363 'Microsoft.DBforPostgreSQL/flexibleServers/privateEndpointConnections@2025-01-01-preview' = {
  parent: flexibleServers_code_the_clinic_db_name_resource
  name: '${flexibleServers_code_the_clinic_db_name}-pe.c2060ad2-39f0-4ed2-8050-d0e4f8490363'
  properties: {
    privateEndpoint: {}
    privateLinkServiceConnectionState: {
      status: 'Approved'
      description: 'Auto-Approved'
      actionsRequired: 'None'
    }
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
    vaultUri: 'https://${vaults_code_the_clinic_vault_name}.${environment().suffixes.keyvaultDns}'
    provisioningState: 'Succeeded'
    publicNetworkAccess: 'Enabled'
  }
}

resource vaults_code_the_clinic_vault_name_azure_client_id 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'azure-client-id'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_azure_secret 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'azure-secret'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_azure_tenant_id 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'azure-tenant-id'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_db_host 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'db-host'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_django_secret_key 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'django-secret-key'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_postgres_db 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'postgres-db'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource vaults_code_the_clinic_vault_name_postgres_user 'Microsoft.KeyVault/vaults/secrets@2024-12-01-preview' = {
  parent: vaults_code_the_clinic_vault_name_resource
  name: 'postgres-user'
  properties: {
    attributes: {
      enabled: true
    }
  }
}

resource privateDnsZones_privatelink_postgres_database_azure_com_name_code_the_clinic_db 'Microsoft.Network/privateDnsZones/A@2024-06-01' = {
  parent: privateDnsZones_privatelink_postgres_database_azure_com_name_resource
  name: 'code-the-clinic-db'
  properties: {
    metadata: {
      creator: 'created by private endpoint code-the-clinic-db-pe with resource guid cee5551c-d8eb-4682-accd-7758eea1f99d'
    }
    ttl: 10
    aRecords: [
      {
        ipv4Address: '10.0.0.4'
      }
    ]
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

resource sites_code_the_clinic_name_sites_code_the_clinic_name_c8b8cxb8bgareygs_northcentralus_01_azurewebsites_net 'Microsoft.Web/sites/hostNameBindings@2024-11-01' = {
  parent: sites_code_the_clinic_name_resource
  name: '${sites_code_the_clinic_name}-c8b8cxb8bgareygs.${locationLower}-01.azurewebsites.net'
  properties: {
    siteName: 'code-the-clinic'
    hostNameType: 'Verified'
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
        name: '${sites_code_the_clinic_name}-c8b8cxb8bgareygs.${locationLower}-01.azurewebsites.net'
        sslState: 'Disabled'
        hostType: 'Standard'
      }
      {
        name: '${sites_code_the_clinic_name}-c8b8cxb8bgareygs.scm.${locationLower}-01.azurewebsites.net'
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

resource sites_code_the_clinic_name_app_service_subnet_connection 'Microsoft.Web/sites/virtualNetworkConnections@2024-11-01' = {
  parent: sites_code_the_clinic_name_resource
  name: 'app-service-subnet'
  properties: {
    vnetResourceId: '${virtualNetworks_code_the_clinic_vnet_name_resource.id}/subnets/app-service-subnet'
    isSwift: true
  }
}
