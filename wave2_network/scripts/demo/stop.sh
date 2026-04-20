#!/usr/bin/env bash

set -euo pipefail

pkill -f 'uvicorn main:app --host 127.0.0.1 --port 8000' || true
pkill -f 'python -m blindference_node.cli start' || true
