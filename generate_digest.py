#!/usr/bin/env python3
"""Generate the Claude Code Daily Digest as a JSON file for the web frontend.

Usage:
    python generate_digest.py              # Full pipeline
    python generate_digest.py --collect    # Only collect, print raw items
    python generate_digest.py --dry-run    # Collect + summarize, skip writing
"""

import argparse
import html
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone

import collectors
import summarizer
from tips import get_tip_of_the_day

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("generate_digest")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "digest.json")


def _safe_link(match):
    """Create safe anchor tag, rejecting dangerous URL protocols."""
    text = html.escape(match.group(1))
    url = match.group(2)
    if not re.match(r"^https?://", url):
        return text
    url = html.escape(url, quote=True)
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{text}</a>'


def markdown_to_html(md):
    """Convert markdown summary to simple HTML with XSS protection."""
    # First, escape all HTML entities in the raw markdown
    text = html.escape(md)
    # Convert markdown formatting (now operating on escaped text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    # Links: unescape brackets first (escaped by html.escape), then validate URLs
    text = text.replace("&#x27;", "'")
    text = re.sub(r"\[(.+?)\]\((.+?)\)", _safe_link, text)
    # Strip leading dashes/bullets the model might still produce
    text = re.sub(r"^[-•]\s+", "", text, flags=re.MULTILINE)
    # Double newlines = item separation (div with margin)
    text = re.sub(r"\n\n+", "</div><div class=\"item\">", text)
    # Single newlines = tight line within an item
    text = text.replace("\n", "<br>")
    # Wrap in container
    text = '<div class="item">' + text + "</div>"
    return text


def main():
    parser = argparse.ArgumentParser(description="Generate Claude Code Daily Digest")
    parser.add_argument("--collect", action="store_true", help="Only collect, skip summarize")
    parser.add_argument("--dry-run", action="store_true", help="Collect + summarize, don't write")
    args = parser.parse_args()

    logger.info("Starting Claude Code Daily Digest generation...")

    # Step 1: Collect from all sources
    logger.info("Collecting updates from all sources...")
    items = collectors.collect_all()
    logger.info(f"Total items collected: {len(items)}")

    if args.collect:
        print(json.dumps(items, indent=2, default=str))
        return

    # Step 2: Summarize with Ollama
    logger.info("Summarizing with Ollama...")
    summary = summarizer.summarize(items)
    logger.info("Summary generated.")

    # Step 3: Get tip of the day
    tip = get_tip_of_the_day()

    # Step 4: Build digest JSON
    now = datetime.now(timezone.utc)
    digest = {
        "generated_at": now.isoformat(),
        "date_display": now.strftime("%B %d, %Y"),
        "summary_html": markdown_to_html(summary),
        "tip": {"command": tip["command"], "description": tip["description"]},
        "item_count": len(items),
    }

    if args.dry_run:
        print(json.dumps(digest, indent=2))
        logger.info("Dry run — not writing file.")
        return

    # Step 5: Write to public/digest.json
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(digest, f, indent=2)

    logger.info(f"Digest written to {OUTPUT_PATH}")
    logger.info(f"Items: {len(items)}, Tip: {tip['command']}")


if __name__ == "__main__":
    main()
