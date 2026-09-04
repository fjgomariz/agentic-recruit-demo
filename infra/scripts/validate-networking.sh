#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 --resource-group <name> --environment-name <name>"
}

RESOURCE_GROUP=""
ENVIRONMENT_NAME=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --resource-group)
      RESOURCE_GROUP="${2:-}"
      shift 2
      ;;
    --environment-name)
      ENVIRONMENT_NAME="${2:-}"
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$RESOURCE_GROUP" || -z "$ENVIRONMENT_NAME" ]]; then
  usage
  exit 2
fi

require_value() {
  local description="$1"
  local value="$2"

  if [[ -z "$value" || "$value" == "None" || "$value" == "null" ]]; then
    echo "FAIL: Could not resolve $description."
    exit 1
  fi
}

assert_equal() {
  local description="$1"
  local expected="$2"
  local actual="$3"

  if [[ "$actual" != "$expected" ]]; then
    echo "FAIL: $description. Expected '$expected', found '$actual'."
    exit 1
  fi

  echo "PASS: $description"
}

WORKLOAD_NAME="recruitment"
VNET_NAME="vnet-${WORKLOAD_NAME}-${ENVIRONMENT_NAME}"
CONTAINER_APPS_SUBNET_NAME="snet-container-apps"
CONTAINER_APPS_ENVIRONMENT_NAME="cae-${WORKLOAD_NAME}-${ENVIRONMENT_NAME}"

SUBSCRIPTION_ID="$(az account show --query id --output tsv)"
EXPECTED_SUBNET_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/virtualNetworks/${VNET_NAME}/subnets/${CONTAINER_APPS_SUBNET_NAME}"

STORAGE_ACCOUNT_NAME="$(az resource list --resource-group "$RESOURCE_GROUP" --resource-type Microsoft.Storage/storageAccounts --query "[?tags.environment=='${ENVIRONMENT_NAME}'].name | [0]" --output tsv)"
COSMOS_ACCOUNT_NAME="$(az resource list --resource-group "$RESOURCE_GROUP" --resource-type Microsoft.DocumentDB/databaseAccounts --query "[?tags.environment=='${ENVIRONMENT_NAME}'].name | [0]" --output tsv)"
require_value "the tagged Storage account" "$STORAGE_ACCOUNT_NAME"
require_value "the tagged Cosmos DB account" "$COSMOS_ACCOUNT_NAME"

BLOB_PRIVATE_ENDPOINT_NAME="pe-${STORAGE_ACCOUNT_NAME}-blob"
COSMOS_PRIVATE_ENDPOINT_NAME="pe-${COSMOS_ACCOUNT_NAME}-sql"
STORAGE_SUFFIX="$(az cloud show --query suffixes.storageEndpoint --output tsv)"
BLOB_PRIVATE_DNS_ZONE="privatelink.blob.${STORAGE_SUFFIX}"
COSMOS_PRIVATE_DNS_ZONE="privatelink.documents.azure.com"
VNET_LINK_NAME="link-${VNET_NAME}"

ENVIRONMENT_INTERNAL="$(az containerapp env show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_APPS_ENVIRONMENT_NAME" --query properties.vnetConfiguration.internal --output tsv)"
ENVIRONMENT_PUBLIC_ACCESS="$(az containerapp env show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_APPS_ENVIRONMENT_NAME" --query properties.publicNetworkAccess --output tsv)"
ENVIRONMENT_SUBNET_ID="$(az containerapp env show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_APPS_ENVIRONMENT_NAME" --query properties.vnetConfiguration.infrastructureSubnetId --output tsv)"
assert_equal "Container Apps Environment is external" "false" "${ENVIRONMENT_INTERNAL,,}"
assert_equal "Container Apps Environment public network access is enabled" "Enabled" "$ENVIRONMENT_PUBLIC_ACCESS"
assert_equal "Container Apps Environment uses the expected subnet" "${EXPECTED_SUBNET_ID,,}" "${ENVIRONMENT_SUBNET_ID,,}"

STORAGE_PUBLIC_ACCESS="$(az storage account show --resource-group "$RESOURCE_GROUP" --name "$STORAGE_ACCOUNT_NAME" --query publicNetworkAccess --output tsv)"
STORAGE_DEFAULT_ACTION="$(az storage account show --resource-group "$RESOURCE_GROUP" --name "$STORAGE_ACCOUNT_NAME" --query networkRuleSet.defaultAction --output tsv)"
COSMOS_PUBLIC_ACCESS="$(az cosmosdb show --resource-group "$RESOURCE_GROUP" --name "$COSMOS_ACCOUNT_NAME" --query publicNetworkAccess --output tsv)"
assert_equal "Storage public network access is disabled" "Disabled" "$STORAGE_PUBLIC_ACCESS"
assert_equal "Storage default network action is Deny" "Deny" "$STORAGE_DEFAULT_ACTION"
assert_equal "Cosmos DB public network access is disabled" "Disabled" "$COSMOS_PUBLIC_ACCESS"

BLOB_CONNECTION_STATUS="$(az network private-endpoint show --resource-group "$RESOURCE_GROUP" --name "$BLOB_PRIVATE_ENDPOINT_NAME" --query privateLinkServiceConnections[0].privateLinkServiceConnectionState.status --output tsv)"
COSMOS_CONNECTION_STATUS="$(az network private-endpoint show --resource-group "$RESOURCE_GROUP" --name "$COSMOS_PRIVATE_ENDPOINT_NAME" --query privateLinkServiceConnections[0].privateLinkServiceConnectionState.status --output tsv)"
assert_equal "Blob private endpoint exists and is approved" "Approved" "$BLOB_CONNECTION_STATUS"
assert_equal "Cosmos DB private endpoint exists and is approved" "Approved" "$COSMOS_CONNECTION_STATUS"

BLOB_LINK_VNET_ID="$(az network private-dns link vnet show --resource-group "$RESOURCE_GROUP" --zone-name "$BLOB_PRIVATE_DNS_ZONE" --name "$VNET_LINK_NAME" --query virtualNetwork.id --output tsv)"
COSMOS_LINK_VNET_ID="$(az network private-dns link vnet show --resource-group "$RESOURCE_GROUP" --zone-name "$COSMOS_PRIVATE_DNS_ZONE" --name "$VNET_LINK_NAME" --query virtualNetwork.id --output tsv)"
EXPECTED_VNET_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/virtualNetworks/${VNET_NAME}"
assert_equal "Blob Private DNS zone is linked to the application VNet" "${EXPECTED_VNET_ID,,}" "${BLOB_LINK_VNET_ID,,}"
assert_equal "Cosmos DB Private DNS zone is linked to the application VNet" "${EXPECTED_VNET_ID,,}" "${COSMOS_LINK_VNET_ID,,}"

BLOB_ZONE_GROUP_ID="$(az network private-endpoint dns-zone-group show --resource-group "$RESOURCE_GROUP" --endpoint-name "$BLOB_PRIVATE_ENDPOINT_NAME" --name default --query privateDnsZoneConfigs[0].privateDnsZoneId --output tsv)"
COSMOS_ZONE_GROUP_ID="$(az network private-endpoint dns-zone-group show --resource-group "$RESOURCE_GROUP" --endpoint-name "$COSMOS_PRIVATE_ENDPOINT_NAME" --name default --query privateDnsZoneConfigs[0].privateDnsZoneId --output tsv)"
EXPECTED_BLOB_ZONE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/privateDnsZones/${BLOB_PRIVATE_DNS_ZONE}"
EXPECTED_COSMOS_ZONE_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Network/privateDnsZones/${COSMOS_PRIVATE_DNS_ZONE}"
assert_equal "Blob private endpoint DNS zone group is configured" "${EXPECTED_BLOB_ZONE_ID,,}" "${BLOB_ZONE_GROUP_ID,,}"
assert_equal "Cosmos DB private endpoint DNS zone group is configured" "${EXPECTED_COSMOS_ZONE_ID,,}" "${COSMOS_ZONE_GROUP_ID,,}"

CONTAINER_APPS_ENVIRONMENT_ID="$(az containerapp env show --resource-group "$RESOURCE_GROUP" --name "$CONTAINER_APPS_ENVIRONMENT_NAME" --query id --output tsv)"
CONTAINER_APPS_PRIVATE_ENDPOINT_COUNT="$(az network private-endpoint list --resource-group "$RESOURCE_GROUP" --query "[?privateLinkServiceConnections[?privateLinkServiceId=='${CONTAINER_APPS_ENVIRONMENT_ID}'] || manualPrivateLinkServiceConnections[?privateLinkServiceId=='${CONTAINER_APPS_ENVIRONMENT_ID}']] | length(@)" --output tsv)"
assert_equal "No private endpoint targets the Container Apps Environment" "0" "$CONTAINER_APPS_PRIVATE_ENDPOINT_COUNT"

echo
echo "Configuration validation passed."
echo "DNS resolution must be tested from a VNet-connected workload. No temporary compute was created."
echo "From that workload, verify the normal Blob and Cosmos hostnames resolve to private IP addresses."
