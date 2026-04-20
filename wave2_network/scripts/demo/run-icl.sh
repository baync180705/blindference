#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=./common.sh
source "${SCRIPT_DIR}/common.sh"

load_icl_env

cd "${ICL_DIR}"

export BLINDFERENCE_ATTESTOR_ADDRESS
export BLINDFERENCE_UNDERWRITER_ADDRESS
export BLINDFERENCE_AGENT_ADDRESS
export MOCK_ORACLE_ADDRESS

./.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
