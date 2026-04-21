"""Summarize collected updates using a local Ollama model."""

import logging

import requests

import config

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"

SYSTEM_PROMPT = """Write structured markdown. Group items by category. Do not add a title or heading. Do not ask questions.
For each item use EXACTLY this format:

- **Short Descriptive Title**
  One-line description of what this is about.
  [Read on Platform](url)

Rules:
- Title: MUST be wrapped in **double asterisks** — e.g. **Short Descriptive Title** — 3–6 words describing the content, never the source/platform name, version numbers, or release names
- Description: exactly one sentence, no source name, no copying raw content
- Link: [Read on Platform](url) using the platform label provided
- Blank line between items. Use ## for category headings only."""

PLATFORM_MAP = {
    "Chase AI Blog": "Chase AI",
    "Chase AI YouTube": "YouTube",
    "GitHub Releases": "GitHub",
    "Anthropic Blog": "Anthropic",
    "Anthropic Engineering": "Anthropic Engineering",
    "Docs Changelog": "Anthropic Docs",
    "Claude Release Notes": "Anthropic",
    "Tyler Germain Gists": "GitHub",
    "Hacker News": "Hacker News",
    "Reddit r/ClaudeAI": "Reddit",
}


def _format_item(item):
    platform = PLATFORM_MAP.get(item["source"], item["source"])
    content = item.get("content", "").strip()
    content_hint = f" | content: {content[:300]}" if content else ""
    return f"- {item['title'][:120]} | {item['url']} | platform: {platform}{content_hint}"


def summarize(items, feature_items=None, news_items=None, pinned_news_items=None):
    """Send collected items to local Ollama model for summarization.

    feature_items: pre-selected list of exactly 5 items for New Features.
    news_items: optional news pool (Anthropic Blog + Docs Changelog).
    pinned_news_items: items always included in General News regardless of LLM selection.
    items: all collected items (fallback).
    """
    if not items and not feature_items:
        return "No new Claude Code updates found today."

    # Build feature section input (numbered to ensure all 5 are rendered)
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
        f"Write exactly one entry per numbered item below — all 5, in order:\n{feature_text}\n\n"
        f"## General News\n"
        + (f"Always include these pinned items first:\n{pinned_text}\n\n" if pinned_text else "")
        + f"Then include up to 4 additional items from below. These are Anthropic/Claude company-level "
        f"announcements — model releases, funding, partnerships, industry news:\n{news_text}\n\n"
        f"For every item follow the 3-line format from the system prompt exactly. "
        f"The title MUST use **double asterisks** and describe the specific content — "
        f"NEVER use a version number or release tag as the title. "
        f"For GitHub release items, read the 'content:' field and name the single most notable feature or fix "
        f"(e.g. **Session Header Added for API Requests**, **VCS Directory Exclusions in Config**). "
        f"Use the 'platform:' label in each item to build the link text."
    )

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": config.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "stream": False,
                "options": {"num_predict": 2048},
            },
            timeout=120,
        )
        response.raise_for_status()
        summary = response.json()["message"]["content"]
        logger.info(f"Ollama summarization complete ({len(summary)} chars)")
        return summary
    except Exception as e:
        if "Connection" in type(e).__name__:
            logger.error("Ollama summarization failed — is Ollama running? %s", e)
        else:
            logger.error("Ollama summarization failed: %s", e)
        return f"⚠️ Summarization unavailable. Raw updates:\n\n{feature_text}"
