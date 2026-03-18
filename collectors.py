"""Collectors for Claude Code update sources."""

import logging
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "ClaudeCodeUpdates/1.0"
}


def collect_github_releases():
    """Fetch latest Claude Code releases from GitHub API."""
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS)

    try:
        resp = requests.get(config.GITHUB_RELEASES_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        releases = resp.json()

        for release in releases:
            published = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
            if published < cutoff:
                break
            items.append({
                "title": release.get("name") or release.get("tag_name", "Untitled"),
                "date": published.isoformat(),
                "content": release.get("body", "")[:2000],
                "source": "GitHub Releases",
                "url": release.get("html_url", ""),
            })

        logger.info(f"GitHub releases: found {len(items)} recent release(s)")
    except Exception as e:
        logger.warning(f"GitHub releases collector failed: {e}")

    return items


def collect_anthropic_blog():
    """Scrape Anthropic blog for Claude Code related posts."""
    items = []

    try:
        resp = requests.get(config.ANTHROPIC_BLOG_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find article/post elements - Anthropic uses various structures
        articles = soup.find_all("a", href=True)
        seen_urls = set()

        for a in articles:
            href = a.get("href", "")
            if "/news/" not in href or href in seen_urls:
                continue
            seen_urls.add(href)

            text = a.get_text(separator=" ", strip=True).lower()
            if not any(kw in text for kw in config.KEYWORDS + ["claude"]):
                continue

            title = a.get_text(separator=" ", strip=True)[:200]
            url = href if href.startswith("http") else f"https://www.anthropic.com{href}"

            items.append({
                "title": title,
                "date": datetime.now(timezone.utc).isoformat(),
                "content": title,
                "source": "Anthropic Blog",
                "url": url,
            })

        logger.info(f"Anthropic blog: found {len(items)} relevant post(s)")
    except Exception as e:
        logger.warning(f"Anthropic blog collector failed: {e}")

    return items


def collect_changelog():
    """Fetch and parse the Anthropic docs changelog."""
    items = []

    try:
        resp = requests.get(config.DOCS_CHANGELOG_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Changelog entries are typically in heading + content blocks
        headings = soup.find_all(["h2", "h3"])
        cutoff = datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS)

        for h in headings:
            heading_text = h.get_text(strip=True)

            # Try to parse a date from the heading
            date_parsed = None
            for fmt in ["%B %d, %Y", "%Y-%m-%d", "%b %d, %Y"]:
                try:
                    date_parsed = datetime.strptime(heading_text, fmt).replace(tzinfo=timezone.utc)
                    break
                except ValueError:
                    continue

            if date_parsed and date_parsed < cutoff:
                continue

            # Collect sibling content until next heading
            content_parts = []
            for sib in h.find_next_siblings():
                if sib.name in ["h2", "h3"]:
                    break
                content_parts.append(sib.get_text(separator=" ", strip=True))

            content = "\n".join(content_parts)[:2000]
            if not content:
                continue

            # Filter for Claude Code relevance
            combined = (heading_text + " " + content).lower()
            if not any(kw in combined for kw in config.KEYWORDS + ["claude"]):
                continue

            items.append({
                "title": heading_text,
                "date": date_parsed.isoformat() if date_parsed else datetime.now(timezone.utc).isoformat(),
                "content": content,
                "source": "Docs Changelog",
                "url": config.DOCS_CHANGELOG_URL,
            })

        logger.info(f"Docs changelog: found {len(items)} relevant entry(ies)")
    except Exception as e:
        logger.warning(f"Docs changelog collector failed: {e}")

    return items


def collect_chase_ai():
    """Scrape Chase AI blog for Claude Code related posts."""
    items = []

    try:
        resp = requests.get(config.CHASE_AI_BLOG_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find blog post links
        articles = soup.find_all("a", href=True)
        seen_urls = set()

        for a in articles:
            href = a.get("href", "")
            if "/blog/" not in href or href in seen_urls or href == "/blog/":
                continue
            seen_urls.add(href)

            text = a.get_text(separator=" ", strip=True).lower()
            if not any(kw in text for kw in config.KEYWORDS + ["claude"]):
                continue

            title = a.get_text(separator=" ", strip=True)[:200]
            url = href if href.startswith("http") else f"https://www.chaseai.io{href}"

            items.append({
                "title": title,
                "date": datetime.now(timezone.utc).isoformat(),
                "content": title,
                "source": "Chase AI Blog",
                "url": url,
            })

        logger.info(f"Chase AI blog: found {len(items)} relevant post(s)")
    except Exception as e:
        logger.warning(f"Chase AI blog collector failed: {e}")

    return items


def collect_tylergermain_gists():
    """Scrape tylergermain's GitHub Gists for Claude Code related entries."""
    items = []

    try:
        resp = requests.get(config.TYLERGERMAIN_GISTS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Each gist is listed as an <article> or a link with /tylergermain/ in href
        seen_urls = set()
        for a in soup.find_all("a", href=True):
            href = a.get("href", "")
            # Gist links look like /tylergermain/<hex-id>
            if not href.startswith("/tylergermain/") or href in seen_urls:
                continue
            parts = href.strip("/").split("/")
            if len(parts) != 2:
                continue
            seen_urls.add(href)

            text = a.get_text(separator=" ", strip=True)
            combined = text.lower()
            if not any(kw in combined for kw in config.KEYWORDS + ["claude"]):
                continue

            url = f"https://gist.github.com{href}"
            items.append({
                "title": text[:200] or href,
                "date": datetime.now(timezone.utc).isoformat(),
                "content": text[:2000],
                "source": "Tyler Germain Gists",
                "url": url,
            })

        logger.info(f"Tyler Germain Gists: found {len(items)} relevant gist(s)")
    except Exception as e:
        logger.warning(f"Tyler Germain Gists collector failed: {e}")

    return items


def collect_all():
    """Run all collectors and return combined results."""
    all_items = []
    collectors = [
        ("GitHub Releases", collect_github_releases),
        ("Anthropic Blog", collect_anthropic_blog),
        ("Docs Changelog", collect_changelog),
        ("Chase AI Blog", collect_chase_ai),
        ("Tyler Germain Gists", collect_tylergermain_gists),
    ]

    for name, fn in collectors:
        try:
            items = fn()
            all_items.extend(items)
        except Exception as e:
            logger.error(f"Collector {name} crashed: {e}")

    return all_items
