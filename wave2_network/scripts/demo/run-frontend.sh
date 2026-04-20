#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

load_icl_env

cd "${FRONTEND_DIR}"

if [[ -f ".env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source ".env"
  set +a
fi

export VITE_ICL_API_URL="${VITE_ICL_API_URL:-http://127.0.0.1:8000}"
export VITE_CHAIN_ID="${VITE_CHAIN_ID:-421614}"
export VITE_BLINDFERENCE_AGENT_ADDRESS="${VITE_BLINDFERENCE_AGENT_ADDRESS:-$DEFAULT_BLINDFERENCE_AGENT_ADDRESS}"
export VITE_BLINDFERENCE_INPUT_VAULT_ADDRESS="${VITE_BLINDFERENCE_INPUT_VAULT_ADDRESS:-$DEFAULT_BLINDFERENCE_INPUT_VAULT_ADDRESS}"

npm run dev -- --force
