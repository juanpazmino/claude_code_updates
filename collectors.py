"""Collectors for Claude Code update sources."""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

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
    """Fetch Anthropic news by scraping anthropic.com/news directly.

    Uses semantic <time> + <span> elements — avoids hashed CSS class names.
    """
    items = []
    keywords = config.KEYWORDS + ["claude", "anthropic"]
    BASE_URL = "https://www.anthropic.com"
    seen_urls = set()

    try:
        resp = requests.get(f"{BASE_URL}/news", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if not href.startswith("/news/") or href == "/news":
                continue
            url = BASE_URL + href
            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Rely on semantic elements rather than hashed class names
            time_el = a.find("time")
            if not time_el:
                continue
            try:
                published = datetime.strptime(time_el.get_text(strip=True), "%b %d, %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            # Featured cards use a heading; list items use the last <span>
            heading = a.find(["h2", "h3", "h4", "h5"])
            if heading:
                title = heading.get_text(strip=True)
            else:
                spans = a.find_all("span")
                title = spans[-1].get_text(strip=True) if spans else ""
            if not title:
                continue

            if not any(kw in (title + " " + href).lower() for kw in keywords):
                continue

            items.append({
                "title": title,
                "date": published.isoformat(),
                "content": "",
                "source": "Anthropic Blog",
                "url": url,
            })

        items.sort(key=lambda x: x["date"], reverse=True)
        logger.info(f"Anthropic blog: found {len(items[:10])} relevant post(s)")
    except Exception as e:
        logger.warning(f"Anthropic blog collector failed: {e}")

    return items[:10]


def collect_changelog():
    """Fetch and parse the Claude Code CHANGELOG.md from GitHub."""
    import re as _re
    items = []
    VIEW_URL = "https://code.claude.com/docs/en/changelog"
    MAX_VERSIONS = 5

    try:
        resp = requests.get(config.DOCS_CHANGELOG_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        text = resp.text

        # Split into version blocks on "## X.Y.Z" headings
        blocks = _re.split(r"\n(?=## \d+\.\d+\.\d+)", text)
        now = datetime.now(timezone.utc).isoformat()

        for block in blocks[1:MAX_VERSIONS + 1]:  # skip preamble, take top N versions
            lines = block.strip().splitlines()
            if not lines:
                continue

            version = lines[0].lstrip("#").strip()  # e.g. "2.1.80"
            bullet_lines = [l.strip() for l in lines[1:] if l.strip().startswith("-")]
            if not bullet_lines:
                continue

            content = "\n".join(bullet_lines)[:2000]
            anchor = version.replace(".", "-")  # e.g. "2-1-80"
            items.append({
                "title": f"Claude Code {version}",
                "date": now,
                "content": content,
                "source": "Docs Changelog",
                "url": f"{VIEW_URL}#{anchor}",
            })

        logger.info(f"Docs changelog: found {len(items)} relevant entry(ies)")
    except Exception as e:
        logger.warning(f"Docs changelog collector failed: {e}")

    return items


def collect_claude_release_notes():
    """Fetch recent entries from Claude's official release notes page."""
    items = []
    MAX_ENTRIES = 7

    try:
        resp = requests.get(config.CLAUDE_RELEASE_NOTES_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for h3 in soup.find_all("h3"):
            if len(items) >= MAX_ENTRIES:
                break
            date_text = h3.get_text(strip=True)
            try:
                entry_date = datetime.strptime(date_text, "%B %d, %Y").replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            # Collect paragraph divs that follow this h3's parent div
            parent_div = h3.parent
            paragraphs = []
            for sibling in parent_div.next_siblings:
                if not hasattr(sibling, "find_all"):
                    continue
                # Stop at the next date heading (h3 or h2)
                if sibling.find(["h2", "h3"]):
                    break
                if "intercom-interblocks-paragraph" in sibling.get("class", []):
                    text = sibling.get_text(separator=" ", strip=True)
                    if text:
                        paragraphs.append(text)

            if not paragraphs:
                continue

            content = "\n".join(paragraphs)[:2000]

            # Use first bold text as title, fall back to date string
            first_bold = None
            for p in paragraphs:
                # Bold text in the paragraph was <b>...</b>, get_text strips tags
                # Re-parse to find actual <b> tags
                break
            bold_tag = None
            for sibling in parent_div.next_siblings:
                if not hasattr(sibling, "find"):
                    continue
                if sibling.find(["h2", "h3"]):
                    break
                bold_tag = sibling.find("b")
                if bold_tag:
                    first_bold = bold_tag.get_text(strip=True)
                    break

            title = first_bold or date_text

            items.append({
                "title": title,
                "date": entry_date.isoformat(),
                "content": content,
                "source": "Claude Release Notes",
                "url": config.CLAUDE_RELEASE_NOTES_URL,
            })

        logger.info(f"Claude release notes: found {len(items)} recent entry(ies)")
    except Exception as e:
        logger.warning(f"Claude release notes collector failed: {e}")

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

            img_tag = a.find("img", alt=True)
            title_text = img_tag["alt"].strip() if img_tag and img_tag.get("alt", "").strip() else a.get_text(separator=" ", strip=True)[:200]
            text = title_text.lower()
            if not any(kw in text for kw in config.KEYWORDS + ["claude"]):
                continue
            title = title_text
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


def collect_chase_ai_youtube():
    """Scrape Chase AI YouTube channel for Claude Code related videos."""
    import json as _json
    import re as _re
    items = []

    try:
        resp = requests.get(config.CHASE_AI_YOUTUBE_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()

        # YouTube embeds initial data as JSON in a script tag
        match = _re.search(r"var ytInitialData\s*=\s*(\{.+?\});</script>", resp.text, _re.DOTALL)
        if not match:
            logger.warning("Chase AI YouTube: could not find ytInitialData")
            return items

        data = _json.loads(match.group(1))

        # Drill into the video grid
        tabs = (
            data.get("contents", {})
            .get("twoColumnBrowseResultsRenderer", {})
            .get("tabs", [])
        )
        video_items = []
        for tab in tabs:
            tab_content = tab.get("tabRenderer", {}).get("content", {})
            section_list = tab_content.get("sectionListRenderer", {}).get("contents", [])
            for section in section_list:
                for item in section.get("itemSectionRenderer", {}).get("contents", []):
                    grid = item.get("gridRenderer", {})
                    video_items.extend(grid.get("items", []))
                    rich_grid = item.get("richGridRenderer", {})
                    video_items.extend(rich_grid.get("contents", []))

        seen_ids = set()
        for vi in video_items:
            renderer = vi.get("richItemRenderer", {}).get("content", {}).get("videoRenderer") \
                       or vi.get("gridVideoRenderer")
            if not renderer:
                continue
            video_id = renderer.get("videoId", "")
            if not video_id or video_id in seen_ids:
                continue
            seen_ids.add(video_id)

            title = "".join(
                r.get("text", "") for r in renderer.get("title", {}).get("runs", [])
            )
            combined = title.lower()
            if not any(kw in combined for kw in config.KEYWORDS + ["claude"]):
                continue

            url = f"https://www.youtube.com/watch?v={video_id}"
            items.append({
                "title": title[:200],
                "date": datetime.now(timezone.utc).isoformat(),
                "content": title[:2000],
                "source": "Chase AI YouTube",
                "url": url,
            })

        logger.info(f"Chase AI YouTube: found {len(items)} relevant video(s)")
    except Exception as e:
        logger.warning(f"Chase AI YouTube collector failed: {e}")

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


def get_latest_github_release():
    """Return {version, url} for the most recent Claude Code release, or None."""
    try:
        resp = requests.get(config.GITHUB_RELEASES_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        releases = resp.json()
        if releases:
            r = releases[0]
            return {
                "version": r.get("name") or r.get("tag_name", ""),
                "url": r.get("html_url", ""),
            }
    except Exception as e:
        logger.warning(f"get_latest_github_release failed: {e}")
    return None


def collect_all():
    """Run all collectors and return combined results."""
    all_items = []
    collectors = [
        ("Chase AI Blog", collect_chase_ai),
        ("Chase AI YouTube", collect_chase_ai_youtube),
        ("GitHub Releases", collect_github_releases),
        ("Anthropic Blog", collect_anthropic_blog),
        ("Docs Changelog", collect_changelog),
        ("Claude Release Notes", collect_claude_release_notes),
        ("Tyler Germain Gists", collect_tylergermain_gists),
    ]

    for name, fn in collectors:
        try:
            items = fn()
            all_items.extend(items)
        except Exception as e:
            logger.error(f"Collector {name} crashed: {e}")

    return all_items
