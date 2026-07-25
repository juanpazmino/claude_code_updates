#!/usr/bin/env python3
"""Send the daily digest email to Buttondown subscribers.

Run after a successful `npx vercel deploy` in run_updates.sh, so subscribers
never get a link to a site that isn't live yet.

Two guards prevent an unwanted send:
  1. Degraded-digest guard — skip if the summarizer fell back to its
     ⚠️ failure marker (see CLAUDE.md "Summarizer failure is graceful but
     silent"). Never email a raw feature dump.
  2. Double-send guard — skip if today's digest date is already recorded in
     .email_sent.json (gitignored), so a re-run of the pipeline can't send
     the same digest twice.

All failure paths (missing digest, missing API key, network/API error) log a
warning and return without raising, so this never kills the pipeline.
"""

import json
import logging
import os

import requests
from dotenv import load_dotenv

from email_template import get_subject_line, render_email_html

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("send_email")

ROOT = os.path.dirname(os.path.abspath(__file__))
DIGEST_PATH = os.path.join(ROOT, "public", "digest.json")
SENT_MARKER_PATH = os.path.join(ROOT, ".email_sent.json")
BUTTONDOWN_API_URL = "https://api.buttondown.com/v1/emails"

# summarizer_v2.py prefixes a degraded (API-failure) summary with this marker —
# it survives markdown_to_html() unescaped since html.escape() doesn't touch it.
DEGRADED_MARKER = "⚠️"


def _load_sent_marker():
    """Return the last-sent digest's date_display, or None if never sent."""
    if not os.path.exists(SENT_MARKER_PATH):
        return None
    try:
        with open(SENT_MARKER_PATH) as f:
            return json.load(f).get("last_sent_date")
    except Exception:
        return None


def _save_sent_marker(date_display):
    with open(SENT_MARKER_PATH, "w") as f:
        json.dump({"last_sent_date": date_display}, f, indent=2)


def send_email():
    try:
        with open(DIGEST_PATH) as f:
            digest = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read {DIGEST_PATH}: {e}")
        return

    # Guard 1: never email a degraded digest.
    if DEGRADED_MARKER in digest.get("summary_html", ""):
        logger.warning("Digest is degraded (⚠️ marker present) — skipping email send.")
        return

    date_display = digest.get("date_display", "")

    # Guard 2: never send the same day's digest twice.
    if date_display and _load_sent_marker() == date_display:
        logger.warning(f"Digest for {date_display} was already sent — skipping.")
        return

    api_key = os.environ.get("BUTTONDOWN_API_KEY")
    if not api_key:
        logger.warning("BUTTONDOWN_API_KEY not set — skipping email send.")
        return

    subject = get_subject_line(date_display)
    body = render_email_html(digest)

    try:
        response = requests.post(
            BUTTONDOWN_API_URL,
            headers={
                "Authorization": f"Token {api_key}",
                # API version 2026-04-01 made `draft` the default and requires
                # this header the first time a key sends with `about_to_send`
                # (returns 400 sending_requires_confirmation otherwise). Harmless
                # on later sends, so we always include it.
                "X-Buttondown-Live-Dangerously": "true",
            },
            json={"subject": subject, "body": body, "status": "about_to_send"},
            timeout=30,
        )
        response.raise_for_status()
    except Exception as e:
        logger.warning(f"Buttondown send failed: {e}")
        return

    # Only mark as sent once Buttondown has confirmed the request succeeded.
    _save_sent_marker(date_display)
    logger.info(f"Email sent to Buttondown subscribers: {subject}")


if __name__ == "__main__":
    send_email()
