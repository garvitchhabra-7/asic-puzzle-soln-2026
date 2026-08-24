#!/bin/bash
# Usage: run_solve.sh [--validate | --sim]
# Generates the SAT script, runs Yosys, and extracts the solution.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG="$PROJECT_DIR/logs/yosys_solve.log"

mkdir -p "$PROJECT_DIR/logs"

echo "==> Generating SAT script..."
python3 "$SCRIPT_DIR/gen_solve_ys.py" "$@"

echo "==> Running Yosys SAT solver (log: $LOG)..."
cd "$PROJECT_DIR"
yosys scripts/solve.ys 2>&1 | tee "$LOG"

if [[ " $* " != *"--sim"* ]]; then
    echo "==> Extracting solution..."
    python3 "$SCRIPT_DIR/extract_solution.py" "$LOG"
fi
