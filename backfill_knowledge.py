"""One-off backfill: build knowledge.json from seen_urls.json.

seen_urls.json only has {url: timestamp} — no titles/descriptions. This script:
1. Derives `source` and `date` deterministically from the URL/timestamp.
2. For URLs with a descriptive slug, batches them to Anthropic Haiku to infer
   a title + description from the slug alone (cheap, no network fetch).
3. For URLs whose slug is opaque (YouTube IDs, HN item ids, tweet ids, bare
   reddit post ids), fetches the page first and feeds the extracted
   title/og:description to the model instead.
4. Never drops an item — a failed fetch still gets a generic entry.

Run once: .venv/bin/python backfill_knowledge.py
"""

import json
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SEEN_URLS_PATH = "seen_urls.json"
OUTPUT_PATH = "knowledge.json"
MODEL = "claude-haiku-4-5-20251001"
BATCH_SIZE = 40
FETCH_TIMEOUT = 10
USER_AGENT = "Mozilla/5.0 (compatible; ClaudeCodeDigestBackfill/1.0)"

# Items with no content value — never include.
EXCLUDED_URLS = {"https://github.com/anthropics/claude-code/issues"}


def derive_source(url: str) -> str:
    """Map a URL's domain (and sometimes path) to a display source label."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.lower()

    if host == "chaseai.io":
        return "Chase AI Blog"
    if host == "youtube.com":
        return "Chase AI YouTube"
    if host == "github.com" and path.startswith("/anthropics/claude-code/releases"):
        return "GitHub Releases"
    if host == "gist.github.com":
        return "Tyler Germain Gists"
    if host == "news.ycombinator.com":
        return "Hacker News"
    if host == "reddit.com" or host.endswith(".reddit.com"):
        return "Reddit r/ClaudeAI"
    if host == "anthropic.com" and path.startswith("/news"):
        return "Anthropic Blog"
    if host == "anthropic.com" and path.startswith("/engineering"):
        return "Anthropic Engineering"
    if host == "support.claude.com":
        return "Claude Release Notes"
    if host == "code.claude.com" and path.startswith("/docs"):
        return "Docs Changelog"
    # Anything else: bare domain (already stripped of "www.")
    return host


def is_opaque(url: str) -> bool:
    """True if the URL's path/slug carries no descriptive content, so the
    page must be fetched to get a title/description instead of inferring
    one from the slug."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path

    if host == "youtube.com":
        return True  # watch?v=<id> or /shorts/<id> — always an opaque video id
    if host == "news.ycombinator.com":
        return True  # item?id=<id>
    if host in ("twitter.com", "x.com"):
        return True  # status/<id>
    if host == "gist.github.com":
        return True  # hash-based path
    if host == "reddit.com" or host.endswith(".reddit.com"):
        segments = [s for s in path.split("/") if s]
        if "comments" in segments:
            idx = segments.index("comments")
            # .../comments/<id>/<slug>/ has a descriptive slug after the id
            return len(segments) <= idx + 2
        return True
    if path in ("", "/"):
        return True  # no path at all — nothing to infer from
    return False


def to_date(timestamp: str) -> str:
    """Extract YYYY-MM-DD from an ISO timestamp string."""
    return datetime.fromisoformat(timestamp).astimezone(timezone.utc).date().isoformat()


def fetch_page_text(url: str) -> str | None:
    """Fetch a page and extract title + og:title + og:description as a
    single text blob for the model to summarize. None on any failure."""
    try:
        resp = requests.get(url, timeout=FETCH_TIMEOUT, headers={"User-Agent": USER_AGENT})
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        parts = []
        if soup.title and soup.title.string:
            parts.append(soup.title.string.strip())
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            parts.append(og_title["content"].strip())
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            parts.append(og_desc["content"].strip())

        text = " | ".join(p for p in parts if p)
        return text or None
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return None


BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["index", "title", "description"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["results"],
    "additionalProperties": False,
}


def call_llm_batch(client: anthropic.Anthropic, batch: list[dict]) -> dict[int, dict]:
    """Send a batch of {index, url, hint} to Haiku, get back
    {index: {title, description}}. Falls back to an empty dict (caller
    handles the fallback per-item) if the call fails."""
    lines = []
    for item in batch:
        hint = f" | extracted page info: {item['hint']}" if item.get("hint") else ""
        lines.append(f"{item['index']}. {item['url']}{hint}")
    user_content = (
        "For each numbered URL below, infer a title and one-line description of what the "
        "linked content covers. Base this on the URL slug and, when given, the extracted "
        "page info. Title must be 3-6 words. Description must be one sentence. Never mention "
        "the source/platform name in the title or description.\n\n"
        + "\n".join(lines)
    )
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            output_config={"format": {"type": "json_schema", "schema": BATCH_SCHEMA}},
            messages=[{"role": "user", "content": user_content}],
        )
        text = response.content[0].text
        parsed = json.loads(text)
        return {entry["index"]: entry for entry in parsed.get("results", []) if "index" in entry}
    except Exception as e:
        logger.warning(f"LLM batch call failed ({len(batch)} items): {e}")
        return {}


def main():
    api_key = os.environ["ANTHROPIC_API_KEY"]
    client = anthropic.Anthropic(api_key=api_key)

    with open(SEEN_URLS_PATH) as f:
        seen_urls = json.load(f)

    # Build the base record set — dedup, skip excluded, derive source/date.
    records = {}
    for url, timestamp in seen_urls.items():
        if url in EXCLUDED_URLS or url in records:
            continue
        records[url] = {
            "url": url,
            "source": derive_source(url),
            "date": to_date(timestamp),
        }

    urls = list(records.keys())
    logger.info(f"Loaded {len(urls)} unique URLs to process")

    # Split into: needs-fetch (opaque slug) vs slug-only (descriptive slug).
    opaque_urls = [u for u in urls if is_opaque(u)]
    slug_urls = [u for u in urls if u not in set(opaque_urls)]
    logger.info(f"{len(slug_urls)} slug-based, {len(opaque_urls)} need page fetch")

    # Fetch opaque URLs first; failures get a generic fallback with no LLM call.
    fetch_hints = {}
    fallback_urls = set()
    for url in opaque_urls:
        text = fetch_page_text(url)
        if text:
            fetch_hints[url] = text
        else:
            fallback_urls.add(url)

    # Build the combined LLM batch input: slug URLs (no hint) + successfully
    # fetched URLs (with hint). Fallback URLs are handled without the LLM.
    llm_input_urls = slug_urls + [u for u in opaque_urls if u not in fallback_urls]
    index_to_url = {i: u for i, u in enumerate(llm_input_urls, 1)}
    url_to_index = {u: i for i, u in index_to_url.items()}

    results = {}
    for start in range(0, len(llm_input_urls), BATCH_SIZE):
        chunk_urls = llm_input_urls[start:start + BATCH_SIZE]
        batch = [
            {"index": url_to_index[u], "url": u, "hint": fetch_hints.get(u)}
            for u in chunk_urls
        ]
        logger.info(f"Sending batch of {len(batch)} URLs to {MODEL}")
        batch_results = call_llm_batch(client, batch)
        results.update(batch_results)

    # Assemble final records.
    knowledge = []
    for url in urls:
        record = records[url]
        if url in fallback_urls:
            record["title"] = urlparse(url).netloc.removeprefix("www.")
            record["description"] = "Sin descripción disponible"
        else:
            idx = url_to_index.get(url)
            llm_entry = results.get(idx) if idx is not None else None
            if llm_entry and llm_entry.get("title") and llm_entry.get("description"):
                record["title"] = llm_entry["title"]
                record["description"] = llm_entry["description"]
            else:
                logger.warning(f"No LLM result for {url}, using fallback")
                record["title"] = urlparse(url).netloc.removeprefix("www.")
                record["description"] = "Sin descripción disponible"
        knowledge.append(record)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)

    logger.info(f"Wrote {len(knowledge)} items to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
