#!/bin/bash
# Claude Code Daily Digest - Runner Script
# Schedule with: crontab -e → 0 8 * * * /path/to/Claude\ Code\ Updates/run_updates.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/updates.log"
VENV="$SCRIPT_DIR/.venv/bin/activate"

echo "$(date): Starting Claude Code Daily Digest" >> "$LOG_FILE"

source "$VENV"
cd "$SCRIPT_DIR"
python generate_digest.py 2>&1 | tee -a "$LOG_FILE"

echo "$(date): Deploying to Vercel" >> "$LOG_FILE"
npx vercel deploy --prod --yes 2>&1 | tee -a "$LOG_FILE"

echo "$(date): Finished" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
