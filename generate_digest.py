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
    # Convert headings
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    # Links: unescape brackets first (escaped by html.escape), then validate URLs
    text = text.replace("&#x27;", "'")
    text = re.sub(r"\[(.+?)\]\((.+?)\)", _safe_link, text)
    # Convert bullet lines: - **Title** → structured item with title span + bullet
    text = re.sub(
        r"^- \*\*(.+?)\*\*$",
        r'<span class="item-title">• \1</span>',
        text,
        flags=re.MULTILINE,
    )
    # Remaining bold (non-bullet)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Indented summary/link lines — strip leading spaces
    text = re.sub(r"^ {1,4}", "", text, flags=re.MULTILINE)
    # Double newlines = item separation
    text = re.sub(r"\n\n+", "</div><div class=\"item\">", text)
    # Single newlines = line break within item
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

    # Step 2: Select feature items — Chase AI + non-GitHub, non-Chase sources
    chase_sources = {"Chase AI Blog", "Chase AI YouTube"}
    feature_excluded = chase_sources | {"GitHub Releases"}
    chase_items = [i for i in items if i["source"] in chase_sources]
    other_items = [i for i in items if i["source"] not in feature_excluded]
    n_chase = min(2, len(chase_items))
    n_other = min(5 - n_chase, len(other_items))
    selected = chase_items[:n_chase] + other_items[:n_other]
    # Backfill from Chase AI only (not GitHub Releases) if short
    if len(selected) < 5:
        remaining = 5 - len(selected)
        used = selected[:]
        extra = [i for i in chase_items + other_items if i not in used]
        selected = (selected + extra[:remaining])[:5]
    logger.info(f"Selected {len(selected)} feature items: {n_chase} Chase AI, {n_other} other")

    # Step 2b: Build General News items — only Anthropic Blog + Docs Changelog, never repeat features
    news_sources = {"Anthropic Blog", "Docs Changelog"}
    selected_urls = {i["url"] for i in selected}
    news_items = [i for i in items if i["source"] in news_sources and i["url"] not in selected_urls]
    logger.info(f"General News pool: {len(news_items)} items")

    # Step 3: Summarize with Ollama
    logger.info("Summarizing with Ollama...")
    summary = summarizer.summarize(items, feature_items=selected, news_items=news_items)
    logger.info("Summary generated.")

    # Step 3b: Append New Versions section (deterministic, not LLM-generated)
    latest = collectors.get_latest_github_release()
    if latest and latest["version"]:
        summary += f"\n\n## New Versions\n\nThe latest version of Claude Code is: {latest['version']} [GitHub Releases]({latest['url']})"
    else:
        summary += "\n\n## New Versions\n\nVersion data unavailable."

    # Step 4: Get tip of the day
    tip = get_tip_of_the_day()

    # Step 5: Build digest JSON
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

    # Step 6: Write to public/digest.json
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(digest, f, indent=2)

    logger.info(f"Digest written to {OUTPUT_PATH}")
    logger.info(f"Items: {len(items)}, Tip: {tip['command']}")


if __name__ == "__main__":
    main()
