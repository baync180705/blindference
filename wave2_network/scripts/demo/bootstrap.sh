#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

load_icl_env

curl -s -X POST "${ICL_BASE_URL}/admin/bootstrap-demo-nodes" \
  -H 'Content-Type: application/json' \
  -d '{"count":3}'
echo
