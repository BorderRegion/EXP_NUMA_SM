#!/usr/bin/env bash
set -euo pipefail
TASK_ROOT="$(cd -- "$(dirname -- "$0")/.." && pwd)"
TASK_PYTHON='/home/ws/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3'
export PYTHONPATH="$TASK_ROOT/.analysis_libs${PYTHONPATH:+:$PYTHONPATH}"
"$TASK_PYTHON" "$TASK_ROOT/experiment/analyze.py"
"$TASK_PYTHON" "$TASK_ROOT/experiment/report.py"
