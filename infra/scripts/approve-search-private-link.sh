#!/usr/bin/env bash
# Approves the pending private endpoint connection that Azure AI Search creates on the storage
# account (shared private link), so its indexers can read the private knowledge source containers.
# Only connections that carry the exact request message from Bicep are approved. Idempotent.
set -euo pipefail

usage() {
  echo "Usage: $0 --storage-account-id <resource id> --request-message <message>"
}

STORAGE_ACCOUNT_ID=""
REQUEST_MESSAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --storage-account-id)
      STORAGE_ACCOUNT_ID="${2:-}"
      shift 2
      ;;
    --request-message)
      REQUEST_MESSAGE="${2:-}"
      shift 2
      ;;
    *)
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$STORAGE_ACCOUNT_ID" || -z "$REQUEST_MESSAGE" ]]; then
  usage
  exit 2
fi

API_VERSION="2023-05-01"
URL="https://management.azure.com${STORAGE_ACCOUNT_ID}/privateEndpointConnections"

# The connection is created asynchronously after the Search deployment finishes.
for attempt in $(seq 1 20); do
  pending="$(az rest --method get --url "${URL}?api-version=${API_VERSION}" \
    --query "value[?properties.privateLinkServiceConnectionState.status=='Pending' && properties.privateLinkServiceConnectionState.description=='${REQUEST_MESSAGE}'].id" \
    --output tsv)"
  approved="$(az rest --method get --url "${URL}?api-version=${API_VERSION}" \
    --query "length(value[?properties.privateLinkServiceConnectionState.status=='Approved' && properties.privateLinkServiceConnectionState.description=='${REQUEST_MESSAGE}'])" \
    --output tsv)"

  if [[ -n "$pending" ]]; then
    for connection_id in $pending; do
      body="{\"properties\":{\"privateLinkServiceConnectionState\":{\"status\":\"Approved\",\"description\":\"${REQUEST_MESSAGE}\"}}}"
      az rest --method put --url "https://management.azure.com${connection_id}?api-version=${API_VERSION}" \
        --body "$body" --output none
      echo "Approved ${connection_id##*/}"
    done
    exit 0
  fi

  if [[ "$approved" != "0" ]]; then
    echo "The Search private link is already approved"
    exit 0
  fi

  echo "Waiting for the Search private endpoint connection (${attempt}/20)"
  sleep 15
done

echo "No Search private endpoint connection with message '${REQUEST_MESSAGE}' was found" >&2
exit 1
