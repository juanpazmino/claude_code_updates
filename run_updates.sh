#!/bin/bash
# Claude Code Daily Digest - Runner Script
# Schedule with: crontab -e → 0 8 * * * /path/to/Claude\ Code\ Updates/run_updates.sh

export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.npm-global/bin"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/updates.log"
VENV="$SCRIPT_DIR/.venv/bin/activate"

echo "$(date): Starting Claude Code Daily Digest" >> "$LOG_FILE"

source "$VENV"
cd "$SCRIPT_DIR"
python generate_digest.py 2>&1 | tee -a "$LOG_FILE"
# PIPESTATUS[0] is python's exit code (plain $? would be tee's).
STATUS=${PIPESTATUS[0]}

# 3 = quiet day (sources answered, nothing new): no deploy, the site keeps
# yesterday's digest, subscribers get the short "you're up to date" email.
if [ "$STATUS" -eq 3 ]; then
    echo "$(date): Quiet day — no deploy, sending quiet email" >> "$LOG_FILE"
    python send_email.py --quiet 2>&1 | tee -a "$LOG_FILE"
    echo "$(date): Finished" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
    exit 0
fi

# Stop if generation failed or a source went silent: no empty site, no email.
if [ "$STATUS" -ne 0 ]; then
    echo "$(date): No digest generated — skipping deploy and email" >> "$LOG_FILE"
    echo "---" >> "$LOG_FILE"
    exit 0
fi

echo "$(date): Deploying to Vercel" >> "$LOG_FILE"
npx vercel deploy --prod --yes --scope juan-pazmino-bs-projects 2>&1 | tee -a "$LOG_FILE"

echo "$(date): Sending email to Buttondown subscribers" >> "$LOG_FILE"
python send_email.py 2>&1 | tee -a "$LOG_FILE"

echo "$(date): Finished" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
