# CLAUDE.md

## Project Overview

Claude Code Daily Digest — a self-updating web page that collects, summarizes, and publishes daily Claude Code updates. Runs locally with Python + Anthropic API, deploys to Vercel as a static site.

**Live site:** https://claude-code-digest.vercel.app

## Tech Stack

- **Backend:** Python 3.10+ (requests, beautifulsoup4, anthropic, python-dotenv)
- **LLM:** Anthropic Haiku (`claude-haiku-4-5`) via API — requires `ANTHROPIC_API_KEY` in `.env`
- **Frontend:** Vanilla HTML/CSS/JS, single `index.html` file
- **Hosting:** Vercel static site (no serverless functions)
- **Deploy tool:** Vercel CLI installed locally via npm (`npx vercel`)

## Pipeline

```
collect (10 sources) → seen-items filter → select features + news → summarize (Haiku) → append New Versions (Python) → write digest.json → deploy (Vercel)
```

1. `collectors.py` scrapes: GitHub Releases, Anthropic Blog (direct scrape), Anthropic Engineering Blog, Claude Release Notes, Docs Changelog, Chase AI Blog, Chase AI YouTube, Tyler Germain Gists, Hacker News, Reddit r/ClaudeAI
2. `generate_digest.py` loads `seen_urls.json`, prefers unseen items, selects: 2 Chase AI + up to 3 from GitHub Releases/Gists for New Features; Anthropic Blog + Anthropic Engineering + Claude Release Notes + Docs Changelog + Hacker News + Reddit for General News
3. **2 most recent** Claude Release Notes items are **pinned** — always appear first in General News regardless of LLM selection
4. `summarizer_v2.py` sends numbered items to Anthropic Haiku, outputs markdown with **New Features** and **General News** only
5. `generate_digest.py` appends **New Versions** deterministically via `collectors.get_latest_github_release()` — never LLM-generated
6. `generate_digest.py` converts markdown → HTML, adds tip-of-the-day, writes `public/digest.json`
7. `generate_digest.py` saves selected feature URLs + top 5 shown news URLs to `seen_urls.json` (30-day TTL) so next run prefers fresh items
8. `run_updates.sh` runs the pipeline + `npx vercel deploy --prod --yes`

### Section definitions

| Section | What goes in it | Sources |
|---|---|---|
| `## New Features` | Claude Code CLI capabilities, version updates, plugin/tool guides | Chase AI Blog (2) + GitHub Releases + Gists (fills to 5) |
| `## General News` | Anthropic/Claude company-level news: product launches, funding, partnerships | Claude Release Notes (2 pinned) + Anthropic Blog + Anthropic Engineering + Docs Changelog + Hacker News + Reddit r/ClaudeAI |
| `## New Versions` | Latest Claude Code GitHub release — deterministic Python, never LLM | GitHub Releases API |

## Key Commands

```bash
source .venv/bin/activate
python generate_digest.py              # Generate digest
python generate_digest.py --collect    # Only collect, print raw items
python generate_digest.py --dry-run    # Collect + summarize, don't write
npx vercel deploy --prod --yes         # Deploy to Vercel
./run_updates.sh                       # Full pipeline + deploy
# generate_digest.command              # macOS double-click launcher (runs full pipeline)
```

## Conventions

- Config in `config.py` (UPPERCASE constants, no personal data) — includes `HN_SEARCH_URL`, `REDDIT_CLAUDEAI_URL`, `CHASE_AI_YOUTUBE_CHANNEL_ID`, and all source URLs
- Collectors return standardized items: `{title, date, content, source, url}`
- Error handling: try/except with `logging.warning`, graceful degradation
- Logging: module-based `logging.getLogger(__name__)` pattern
- Frontend: dark theme (#0d0d0d bg, #C46849 accent), DM Sans + JetBrains Mono fonts
- Byline "by Juan Pazmino B" shown beneath the main title in the header
- Footer has dynamic "Last updated" timestamp + static legal/copyright block (font-size 0.65rem)
- Vercel CLI is local (use `npx vercel`, not `vercel`)
- `public/digest.json` is gitignored — generated artifact, not source
- `seen_urls.json` is gitignored — tracks shown item URLs with 30-day TTL; deleted manually to reset freshness
- `tips.py` — `get_tip_of_the_day()` uses sequential day-number rotation (epoch 2025-01-01); tries `fetch_dynamic_tips()` from Anthropic docs first, falls back to static `TIPS` list; `fetch_dynamic_tips()` uses `separator=" "` + `re.sub` punctuation cleanup to fix space-before-period artifacts from BeautifulSoup parsing
- `summarizer_v2.py` — active summarizer; uses Anthropic Haiku via `anthropic` SDK; `PLATFORM_MAP` maps source names to display labels (e.g. "Chase AI Blog" → "Chase AI", "Reddit r/ClaudeAI" → "Reddit", "Hacker News" → "Hacker News", "Anthropic Engineering" → "Anthropic Engineering"); feature items are numbered 1–5; `summarize()` accepts `pinned_news_items` for mandatory General News entries; loads `ANTHROPIC_API_KEY` from `.env` via `python-dotenv`
- `summarizer.py` — legacy Ollama summarizer; kept for reference but no longer used by the pipeline
- `generate_digest.py` — `_ensure_complete_descriptions(md)` post-processes LLM output before HTML conversion; `_load_seen_urls()` / `_save_seen_urls()` manage the freshness filter; `_prefer_unseen()` sorts item pools so unseen items come first; `markdown_to_html()` bullet regex accepts titles with or without `**` bold markers for LLM compatibility; `feature_excluded` set blocks Anthropic Blog, Anthropic Engineering, Docs Changelog, HN, and Reddit from Features; `news_sources` set includes Anthropic Blog, Anthropic Engineering, Docs Changelog, HN, and Reddit for General News; `official_sources` includes Anthropic Blog, Anthropic Engineering, Docs Changelog, Claude Release Notes — these get a baseline score of 50 in the two-tier sort; `_prefer_unseen()` is applied after score sort so unseen items still surface first within each tier
- `updates.log` — generated by `run_updates.sh` (pipeline stdout), gitignored; useful for debugging cron runs

### Collector details

| Collector | Source | Notes |
|---|---|---|
| `collect_anthropic_blog()` | `anthropic.com/news` (direct scrape) | Uses semantic `<time>` + heading/`<span>`/`img[alt]` elements; accepts any internal path with a `<time>` element (not just `/news/`); no keyword filter — all items on the page are included; sorted by date desc; top 10 |
| `collect_anthropic_engineering()` | `anthropic.com/engineering` (direct scrape) | No dates on listing page — all items assigned today's date; `seen_urls.json` prevents repeats across runs; top 8 posts; General News only; scored as `official_sources` (baseline 50) |
| `collect_claude_release_notes()` | `support.claude.com/en/articles/12138966-release-notes` | Intercom HTML, `h3` = date, bold text = title; top 7 entries; 2 most recent always pinned in General News |
| `collect_changelog()` | Raw `CHANGELOG.md` from GitHub | Parses `## X.Y.Z` blocks; top 5 versions; each version gets unique URL anchor (`#X-Y-Z`) |
| `collect_chase_ai()` | `chaseai.io/blog` | Uses `img[alt]` for clean article title (avoids tag-noise from `get_text()`) |
| `collect_chase_ai_youtube()` | YouTube channel Atom RSS feed | Uses hardcoded `CHASE_AI_YOUTUBE_CHANNEL_ID` from config; falls back to page scrape if missing |
| `collect_github_releases()` | GitHub API | Date-filtered by `LOOKBACK_HOURS`; release body (up to 2000 chars) passed as `content` to LLM for New Features; also used for New Versions (deterministic) |
| `collect_tylergermain_gists()` | `gist.github.com/tylergermain` | Keyword-filtered |
| `collect_hacker_news()` | Algolia HN search API (`hn.algolia.com`) | `LOOKBACK_HOURS * 2` cutoff; min 5 points; skips raw GitHub issue URLs; General News only |
| `collect_reddit_claudeai()` | `reddit.com/r/ClaudeAI/new.json` + `/hot.json` | `LOOKBACK_HOURS * 2` cutoff; min score 2; deduped by post ID; uses external URL for non-native links; General News only |

### Item format (LLM output, all sections except New Versions)

```
- **Short Descriptive Title**
  One-line description.
  [Read on Platform](url)
```

- Title: 3–6 words describing content, never the source/platform name
- Link text: "Read on Platform" (e.g. Read on GitHub, Watch on YouTube, Read on Anthropic)

### Frontend visual hierarchy

| Tier | Element | Size | Color | Weight |
|---|---|---|---|---|
| Section heading | `h2` | 18px | #f0f0f0 | 600 |
| Article title | `.item-title` | 15px | #f0f0f0 | 600 |
| Summary | `.item` text | 14px | #999 | 400 |
| Read More link | `a` | 13px | #C46849 | 400 |

## Rules

- All Playwright screenshots must be saved to the `screenshots_playwright/` folder, not the project root.
- `vercel.json` sets `"deploymentEnabled": false` — this disables Vercel's GitHub auto-deploy, which would overwrite the generated `digest.json` with an empty/stale version on every push. Deploy manually via `npx vercel deploy --prod --yes` or `./run_updates.sh`.

## Gotchas

- **CSP blocks external images** — `vercel.json` sets `img-src 'self'`; any `<img>` pointing to an external URL in `index.html` silently fails. Update the CSP header before adding external thumbnails or avatars.
- **Summarizer failure is graceful but silent** — if the Anthropic API call fails, `summarizer_v2.py` returns a raw feature dump with a ⚠️ prefix; the pipeline still writes and deploys a degraded digest without erroring out.
- **Only top 5 optional news items reach the LLM** — `optional_parts = news_pool[:5]` in `summarizer_v2.py`; items ranked 6+ are never summarized regardless of score, making the two-tier sort in `generate_digest.py` load-bearing.
- **`LOOKBACK_HOURS` is asymmetric** — GitHub Releases uses exactly `LOOKBACK_HOURS` (24h); HN and Reddit use `LOOKBACK_HOURS * 2` (48h). Changing the value in `config.py` does not affect all sources equally.

## Important Notes

- `ANTHROPIC_API_KEY` must be set in `.env` — see `.env.example`; the pipeline will fail without it
- Cron at 12 PM daily: `0 12 * * * /path/to/Claude\ Code\ Updates/run_updates.sh`
- The summarizer prompt explicitly separates features vs news — if categorization is wrong, adjust the prompt in `summarizer_v2.py`
- GitHub Releases body content (up to 2000 chars) is passed to the LLM; the prompt instructs Haiku to name the most notable feature/fix, never the version number
- General News deduplication is enforced in `generate_digest.py` by `selected_urls` set — items in Features never appear in News
- If the site shows stale content, delete `seen_urls.json` to reset the freshness filter — the next run will re-evaluate all items
- `anthropic.com/news` scraper uses semantic elements (`<time>`, heading, last `<span>`) to avoid fragile hashed CSS class names — but may need updating if Anthropic restructures the page
- `support.claude.com` release notes is the authoritative source for Claude.ai product features (Cowork, Dispatch, memory, etc.) that don't appear on the main Anthropic blog
