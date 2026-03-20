"""Summarize collected updates using Ollama."""

import logging

import ollama

import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Write a markdown newsletter digest. Group items by category. Do not ask questions.
For each item use EXACTLY this format:

- **Short Descriptive Title**
  One-line description of what this is about.
  [Read on Platform](url)

Rules:
- Title: 3–6 words describing the content — NEVER the source/platform name
- Description: exactly one line, no source name
- Link: [Read on Platform](url) using the platform label provided
- Blank line between items. Use ## for category headings only."""

PLATFORM_MAP = {
    "Chase AI Blog": "Chase AI",
    "Chase AI YouTube": "YouTube",
    "GitHub Releases": "GitHub",
    "Anthropic Blog": "Anthropic",
    "Docs Changelog": "Anthropic Docs",
    "Claude Release Notes": "Anthropic",
    "Tyler Germain Gists": "GitHub",
}


def _format_item(item):
    platform = PLATFORM_MAP.get(item["source"], item["source"])
    return f"- {item['title'][:120]} | {item['url']} | platform: {platform}"


def summarize(items, feature_items=None, news_items=None, pinned_news_items=None):
    """Send collected items to Ollama for summarization.

    feature_items: pre-selected list of exactly 5 items for New Features.
    news_items: optional news pool (Anthropic Blog + Docs Changelog).
    pinned_news_items: items always included in General News regardless of LLM selection.
    items: all collected items (fallback).
    """
    if not items and not feature_items:
        return "No new Claude Code updates found today."

    # Build feature section input (exactly 5 pre-selected items, numbered to prevent LLM from dropping any)
    feature_parts = [f"{n}. {_format_item(i)}" for n, i in enumerate((feature_items or items)[:5], 1)]
    feature_text = "\n".join(feature_parts)

    # Build General News input
    pinned_pool = pinned_news_items or []
    news_pool = news_items if news_items is not None else []
    pinned_parts = [_format_item(i) for i in pinned_pool]
    optional_parts = [_format_item(i) for i in news_pool[:5]]
    pinned_text = "\n".join(pinned_parts) if pinned_parts else ""
    news_text = "\n".join(optional_parts) if optional_parts else "(no news items available today)"

    user_content = (
        f"Write a newsletter with two sections in this exact order: New Features, General News.\n\n"
        f"## New Features\n"
        f"Write EXACTLY one entry per numbered item below — all 5, no skipping:\n{feature_text}\n\n"
        f"## General News\n"
        + (f"ALWAYS include these pinned items first (mandatory):\n{pinned_text}\n\n" if pinned_text else "")
        + f"Then include additional items from below (max 4). These are Anthropic/Claude company-level announcements "
        f"— model releases, funding, partnerships, industry news:\n{news_text}\n\n"
        f"For EVERY item follow this EXACT 3-line format:\n"
        f"- **Short Descriptive Title**\n"
        f"  One-line description.\n"
        f"  [Read on Platform](url)\n\n"
        f"CRITICAL: The bold title must be 3–6 words describing the content — "
        f"NEVER write the platform name (Chase AI, Anthropic, GitHub, etc.) as the title. "
        f"Use the 'platform:' label in each item to build the link text. "
        f"Blank line between items."
    )

    try:
        response = ollama.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        summary = response["message"]["content"]
        logger.info(f"Ollama summarization complete ({len(summary)} chars)")
        return summary
    except Exception as e:
        logger.error(f"Ollama summarization failed: {e}")
        return f"⚠️ Summarization unavailable. Raw updates:\n\n{feature_text}"
