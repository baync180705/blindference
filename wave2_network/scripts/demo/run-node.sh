#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: bash wave2_network/scripts/demo/run-node.sh <leader|verifier1|verifier2>" >&2
  exit 1
fi

ROLE="$1"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

load_icl_env
resolve_operator_keys

case "${ROLE}" in
  leader)
    OPERATOR_KEY="${DEMO_OPERATOR_PRIVATE_KEY1}"
    CALLBACK_PORT="9101"
    CALLBACK_PUBLIC_URL="${LEADER_CALLBACK_PUBLIC_URL:-http://127.0.0.1:${CALLBACK_PORT}}"
    ;;
  verifier1)
    OPERATOR_KEY="${DEMO_OPERATOR_PRIVATE_KEY2}"
    CALLBACK_PORT="9102"
    CALLBACK_PUBLIC_URL="${VERIFIER1_CALLBACK_PUBLIC_URL:-http://127.0.0.1:${CALLBACK_PORT}}"
    ;;
  verifier2)
    OPERATOR_KEY="${DEMO_OPERATOR_PRIVATE_KEY3}"
    CALLBACK_PORT="9103"
    CALLBACK_PUBLIC_URL="${VERIFIER2_CALLBACK_PUBLIC_URL:-http://127.0.0.1:${CALLBACK_PORT}}"
    ;;
  *)
    echo "Unknown node role: ${ROLE}" >&2
    exit 1
    ;;
esac

cd "${NODE_DIR}"

export BLINDFERENCE_NODE_OPERATOR_PRIVATE_KEY="${OPERATOR_KEY}"
export BLINDFERENCE_NODE_RPC_URL="${ARBITRUM_SEPOLIA_RPC}"
export BLINDFERENCE_NODE_CALLBACK_PORT="${CALLBACK_PORT}"
export BLINDFERENCE_NODE_CALLBACK_PUBLIC_URL="${CALLBACK_PUBLIC_URL}"
export BLINDFERENCE_NODE_ICL_BASE_URL="${ICL_BASE_URL}"
export BLINDFERENCE_NODE_COFHE_CHAIN_ID="${COFHE_CHAIN_ID}"
export BLINDFERENCE_NODE_GROQ_API_KEY="${GROQ_API_KEY:-}"
export BLINDFERENCE_NODE_GEMINI_API_KEY="$(resolve_gemini_api_key)"
export BLINDFERENCE_NODE_MOCK_CLOUD_INFERENCE=false
export BLINDFERENCE_NODE_RUNTIME_REGISTRATION_INTERVAL_SECONDS="${BLINDFERENCE_NODE_RUNTIME_REGISTRATION_INTERVAL_SECONDS:-30}"
export PYTHONPATH=src
export PYTHONUNBUFFERED=1

../icl/.venv/bin/python -m blindference_node.cli start
