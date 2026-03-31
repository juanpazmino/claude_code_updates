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
from datetime import datetime, timedelta, timezone

import collectors
import summarizer_v2 as summarizer
from tips import get_tip_of_the_day

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("generate_digest")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "public")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "digest.json")
SEEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seen_urls.json")
SEEN_TTL_DAYS = 30


def _load_seen_urls():
    """Load seen URLs dict {url: first_seen_iso}, pruning entries older than SEEN_TTL_DAYS."""
    if not os.path.exists(SEEN_PATH):
        return {}
    try:
        with open(SEEN_PATH) as f:
            data = json.load(f)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=SEEN_TTL_DAYS)).isoformat()
        return {url: ts for url, ts in data.items() if ts >= cutoff}
    except Exception:
        return {}


def _save_seen_urls(seen, new_urls):
    """Add new_urls to seen dict and write to disk."""
    now = datetime.now(timezone.utc).isoformat()
    for url in new_urls:
        if url not in seen:
            seen[url] = now
    try:
        with open(SEEN_PATH, "w") as f:
            json.dump(seen, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save seen_urls: {e}")


def _safe_link(match):
    """Create safe anchor tag, rejecting dangerous URL protocols."""
    text = html.escape(match.group(1))
    url = match.group(2)
    if not re.match(r"^https?://", url):
        return text
    url = html.escape(url, quote=True)
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{text}</a>'


def _ensure_complete_descriptions(md):
    """Clean description lines: strip trailing whitespace and bare URLs from prose."""
    # Strip any LLM-added top-level title that isn't a known section heading
    md = re.sub(r"^##\s+(?!New Features|General News|New Versions).+\n?", "", md, flags=re.MULTILINE)
    lines = md.split("\n")
    result = []
    for line in lines:
        # Description lines: indented 1–4 spaces, not a link ([...]), not empty
        if re.match(r"^ {1,4}[^\[\s]", line):
            line = line.rstrip()
            # Strip bare URLs that the LLM leaks into prose (not inside [text](url))
            if not re.search(r"\[.+\]\(.+\)", line):
                line = re.sub(r"\s+https?://\S+", "", line).rstrip()
        result.append(line)
    return "\n".join(result)


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
    # Convert bullet lines: - **Title** or - Title (bold markers optional for LLM compatibility)
    def _bullet_replace(m):
        title = m.group(1)
        desc = m.group(2)
        if desc and desc.strip():
            return f'<span class="item-title">• {title}</span>{desc.strip()}'
        return f'<span class="item-title">• {title}</span>'

    text = re.sub(
        r"^- (?:\*\*)?(.+?)(?:\*\*)?(?:\s*\|\s*(.+))?$",
        _bullet_replace,
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
    seen_urls = _load_seen_urls()

    def _prefer_unseen(pool):
        """Sort pool so unseen items come first, seen items last."""
        return [i for i in pool if i["url"] not in seen_urls] + \
               [i for i in pool if i["url"] in seen_urls]

    chase_sources = {"Chase AI Blog", "Chase AI YouTube"}
    feature_excluded = chase_sources | {"Anthropic Blog", "Claude Release Notes", "Docs Changelog", "Hacker News", "Reddit r/ClaudeAI"}
    chase_items = _prefer_unseen([i for i in items if i["source"] in chase_sources])
    other_items = _prefer_unseen([i for i in items if i["source"] not in feature_excluded])
    n_chase = min(2, len(chase_items))
    n_other = min(5 - n_chase, len(other_items))
    selected = chase_items[:n_chase] + other_items[:n_other]
    # Backfill if short
    if len(selected) < 5:
        remaining = 5 - len(selected)
        used = selected[:]
        extra = [i for i in chase_items + other_items if i not in used]
        selected = (selected + extra[:remaining])[:5]
    logger.info(f"Selected {len(selected)} feature items: {n_chase} Chase AI, {n_other} other")

    # Step 2b: Build General News items — only Anthropic Blog + Docs Changelog, never repeat features
    news_sources = {"Anthropic Blog", "Docs Changelog", "Claude Release Notes", "Hacker News", "Reddit r/ClaudeAI"}
    selected_urls = {i["url"] for i in selected}
    news_items = [i for i in items if i["source"] in news_sources and i["url"] not in selected_urls]

    # Pin the 2 most recent Claude Release Notes entries — always shown first in General News
    release_notes_items = [i for i in news_items if i["source"] == "Claude Release Notes"]
    pinned_news = release_notes_items[:2]
    optional_news = _prefer_unseen([i for i in news_items if i not in pinned_news])
    logger.info(f"General News pool: {len(news_items)} items ({len(pinned_news)} pinned)")

    # Step 3: Summarize with Ollama
    logger.info("Summarizing with LLM model...")
    summary = summarizer.summarize(items, feature_items=selected, news_items=optional_news, pinned_news_items=pinned_news)
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
        "summary_html": markdown_to_html(_ensure_complete_descriptions(summary)),
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

    # Step 7: Save seen URLs so next run prefers fresh content (features + top news shown to LLM)
    shown_news = pinned_news + optional_news[:5]
    _save_seen_urls(seen_urls, [i["url"] for i in selected + shown_news])


if __name__ == "__main__":
    main()
