#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: bash wave2_network/scripts/demo/file-dispute.sh <request_id> <developer_address> [notes]" >&2
  exit 1
fi

REQUEST_ID="$1"
DEVELOPER_ADDRESS="$2"
NOTES="${3:-manual review requested}"
EVIDENCE_HASH="demo:${REQUEST_ID}:$(date +%s)"

curl -s -X POST "http://127.0.0.1:8000/v1/disputes/${REQUEST_ID}" \
  -H 'Content-Type: application/json' \
  -d "{
    \"developer_address\": \"${DEVELOPER_ADDRESS}\",
    \"evidence_hash\": \"${EVIDENCE_HASH}\",
    \"evidence_uri\": \"inline://${REQUEST_ID}\",
    \"notes\": \"${NOTES}\"
  }"
echo
