#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/.venv/bin/activate"
cd "$SCRIPT_DIR"
bash run_updates.sh
echo ""
echo "Done. Press any key to close."
read -n 1
