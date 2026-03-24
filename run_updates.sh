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

echo "$(date): Pushing digest to GitHub (GitHub Actions will deploy to Vercel)" >> "$LOG_FILE"
git add public/digest.json
git commit -m "digest update $(date +%Y-%m-%d)" 2>&1 | tee -a "$LOG_FILE"
git push 2>&1 | tee -a "$LOG_FILE"

echo "$(date): Finished" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
