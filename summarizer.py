"""Summarize collected updates using Ollama."""

import logging

import ollama

import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Write a markdown newsletter digest. Group items by category. Do not ask questions.
For each item use EXACTLY this format (no bullet points, no dashes):

**Item Title**
One-line description. [Source Name](url)

Separate items with a blank line. Use ## for category headings only."""


def summarize(items):
    """Send collected items to Ollama for summarization."""
    if not items:
        return "No new Claude Code updates found today."

    # Build concise input — small models need shorter context
    parts = []
    for item in items[:20]:  # Cap at 20 items for small models
        parts.append(f"- [{item['source']}] {item['title'][:120]} | {item['url']}")
    input_text = "\n".join(parts)

    try:
        response = ollama.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Summarize these Claude Code updates into a newsletter with these categories in this exact order: New Features, News, New Versions. Rules: 'New Features' is ONLY for new product capabilities, tools, or technical features in Claude Code itself. 'News' is for announcements, blog posts, investments, acquisitions, and general company updates. 'New Versions' is for version releases. Do NOT use bullet points or dashes. For each item write the bold title on one line, then the description with source link on the next line. Skip tutorials and guides:\n\n{input_text}"},
            ],
        )
        summary = response["message"]["content"]
        logger.info(f"Ollama summarization complete ({len(summary)} chars)")
        return summary
    except Exception as e:
        logger.error(f"Ollama summarization failed: {e}")
        # Fallback: return raw items as formatted list
        return f"⚠️ Summarization unavailable. Raw updates:\n\n{input_text}"
