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


def _parse_anthropic_cards(html, href_prefixes):
    """Extract (title, url, date) from anthropic.com listing cards.

    Since the Oct 2026 redesign the <time> sits in the card header and the post
    link wraps only the headline, so each card is found from its <time> upwards
    to the nearest element that also holds a headline.
    """
    BASE_URL = "https://www.anthropic.com"
    soup = BeautifulSoup(html, "html.parser")
    cards, seen = [], set()

    for time_el in soup.find_all("time"):
        try:
            published = datetime.strptime(time_el.get_text(strip=True), "%b %d, %Y").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        card = time_el.parent
        for _ in range(5):  # climb a few levels at most: header -> card
            if card is None or card.find(["h2", "h3", "h4", "h5"]):
                break
            card = card.parent
        heading = card.find(["h2", "h3", "h4", "h5"]) if card else None
        link = heading.find_parent("a", href=True) if heading else None
        if not link or not link["href"].startswith(href_prefixes):
            continue

        url = BASE_URL + link["href"]
        if url in seen:  # carousels repeat cards
            continue
        seen.add(url)
        cards.append({"title": heading.get_text(strip=True), "url": url, "date": published})

    cards.sort(key=lambda c: c["date"], reverse=True)
    return cards


def collect_anthropic_blog():
    """Fetch the latest Anthropic news posts from anthropic.com/news."""
    items = []
    try:
        resp = requests.get("https://www.anthropic.com/news", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        for card in _parse_anthropic_cards(resp.text, ("/news/",))[:10]:
            items.append({
                "title": card["title"],
                "date": card["date"].isoformat(),
                "content": "",
                "source": "Anthropic Blog",
                "url": card["url"],
            })
        logger.info(f"Anthropic blog: found {len(items)} relevant post(s)")
    except Exception as e:
        logger.warning(f"Anthropic blog collector failed: {e}")

    return items


def collect_anthropic_engineering():
    """Fetch recent posts from anthropic.com/engineering.

    Posts now live under /research/ (old ones were archived as /engineering/),
    so only posts from the last ENGINEERING_LOOKBACK_DAYS are kept — otherwise
    every old post would come back as "new" under its new URL.
    """
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.ENGINEERING_LOOKBACK_DAYS)
    try:
        resp = requests.get("https://www.anthropic.com/engineering", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        for card in _parse_anthropic_cards(resp.text, ("/engineering/", "/research/")):
            if card["date"] < cutoff:
                continue
            items.append({
                "title": card["title"],
                "date": card["date"].isoformat(),
                "content": "",
                "source": "Anthropic Engineering",
                "url": card["url"],
            })
        logger.info(f"Anthropic engineering: found {len(items)} post(s) in the last {config.ENGINEERING_LOOKBACK_DAYS} days")
    except Exception as e:
        logger.warning(f"Anthropic engineering collector failed: {e}")

    return items


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
    """Fetch Chase AI YouTube videos via the channel's Atom RSS feed."""
    import re as _re
    items = []

    try:
        # Use hardcoded channel ID (scraping the channel page is blocked by YouTube's consent wall)
        channel_id = config.CHASE_AI_YOUTUBE_CHANNEL_ID
        if not channel_id:
            # Fallback: try to extract from channel page
            resp = requests.get(config.CHASE_AI_YOUTUBE_URL, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            match = _re.search(r"channel_id=(UC[^\"&]+)", resp.text)
            if not match:
                logger.warning("Chase AI YouTube: could not find channel ID in page")
                return items
            channel_id = match.group(1)

        rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        rss_resp = requests.get(rss_url, headers=HEADERS, timeout=15)
        rss_resp.raise_for_status()

        root = ET.fromstring(rss_resp.content)
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "yt": "http://www.youtube.com/xml/schemas/2015",
        }

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            video_id_el = entry.find("yt:videoId", ns)

            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue
            if not any(kw in title.lower() for kw in config.KEYWORDS + ["claude"]):
                continue

            video_id = video_id_el.text if video_id_el is not None else ""
            url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""
            for link_el in entry.findall("atom:link", ns):
                if link_el.get("rel") == "alternate":
                    url = link_el.get("href", url)
                    break

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


def collect_hacker_news():
    """Fetch Hacker News stories about Claude/Anthropic via Algolia search API."""
    items = []
    cutoff_ts = int((datetime.now(timezone.utc) - timedelta(hours=config.LOOKBACK_HOURS * 2)).timestamp())
    keywords = config.KEYWORDS + ["claude", "anthropic"]

    try:
        resp = requests.get(
            config.HN_SEARCH_URL,
            params={
                "query": "claude anthropic",
                "tags": "story",
                "hitsPerPage": 20,
                "numericFilters": f"created_at_i>{cutoff_ts}",
            },
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        for hit in data.get("hits", []):
            title = hit.get("title", "")
            if not any(kw in title.lower() for kw in keywords):
                continue
            # Require minimum engagement to filter out noise
            if (hit.get("points") or 0) < 5:
                continue
            hn_permalink = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
            url = hit.get("url") or hn_permalink
            # Skip raw GitHub issue URLs — those are bug reports, not news
            if "github.com" in url and "/issues/" in url:
                continue
            items.append({
                "title": title[:200],
                "date": hit.get("created_at", datetime.now(timezone.utc).isoformat()),
                "content": title[:2000],
                "source": "Hacker News",
                "url": url,
                # Discussion permalink: the chat bot archives this instead of the
                # submitter-supplied external URL, so a link post can't put an
                # attacker's domain into the bot's set of linkable URLs.
                "permalink": hn_permalink,
                "score": hit.get("points") or 0,
            })

        logger.info(f"Hacker News: found {len(items)} relevant story(ies)")
    except Exception as e:
        logger.warning(f"Hacker News collector failed: {e}")

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


def collect_claude_dev():
    """Fetch posts from claude.dev, the blog of Anthropic's developers, via its RSS feed.

    The feed carries real publication dates, so only posts from the last
    CLAUDE_DEV_LOOKBACK_DAYS are kept; knowledge.json keeps them from repeating.
    """
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.CLAUDE_DEV_LOOKBACK_DAYS)

    try:
        resp = requests.get(config.CLAUDE_DEV_RSS_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)

        for entry in root.iter("item"):
            title = (entry.findtext("title") or "").strip()
            url = (entry.findtext("link") or "").strip()
            if not title or not url.startswith("https://claude.dev/"):
                continue
            try:
                published = parsedate_to_datetime(entry.findtext("pubDate") or "")
            except (TypeError, ValueError):
                continue
            if published.tzinfo is None:  # "-0000" dates parse as naive; treat them as UTC
                published = published.replace(tzinfo=timezone.utc)
            if published < cutoff:
                continue

            items.append({
                "title": title,
                "date": published.isoformat(),
                "content": (entry.findtext("description") or "").strip()[:2000],
                "source": "claude.dev",
                "url": url,
            })

        logger.info(f"claude.dev: found {len(items)} post(s) in the last {config.CLAUDE_DEV_LOOKBACK_DAYS} days")
    except Exception as e:
        logger.warning(f"claude.dev collector failed: {e}")

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
        # Before GitHub: the Features "other" pool keeps collection order, so claude.dev gets first pick
        ("claude.dev", collect_claude_dev),
        ("GitHub Releases", collect_github_releases),
        ("Anthropic Blog", collect_anthropic_blog),
        ("Anthropic Engineering", collect_anthropic_engineering),
        ("Docs Changelog", collect_changelog),
        ("Claude Release Notes", collect_claude_release_notes),
        ("Tyler Germain Gists", collect_tylergermain_gists),
        ("Hacker News", collect_hacker_news),
    ]

    for name, fn in collectors:
        try:
            result = fn()
            all_items.extend(result)
        except Exception as e:
            logger.error(f"Collector {name} crashed: {e}")

    return all_items
