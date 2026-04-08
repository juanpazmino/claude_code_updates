# Claude Code Daily Digest — Plan

## Phase 1: Core Pipeline — DONE
- [x] Python collectors for GitHub Releases, Anthropic Blog, Docs Changelog, Claude Release Notes
- [x] Chase AI Blog and Chase AI YouTube collectors
- [x] Tyler Germain Gists collector
- [x] Hacker News collector (Algolia API)
- [x] Reddit r/ClaudeAI collector
- [x] LLM summarizer via Anthropic Haiku (summarizer_v2.py)
- [x] seen_urls.json freshness filter (30-day TTL)
- [x] Tip of the day (sequential rotation + dynamic fetch from docs)
- [x] Static frontend (dark theme, DM Sans + JetBrains Mono)
- [x] Vercel static deploy via CLI (npx vercel)
- [x] run_updates.sh full pipeline + deploy script
- [x] macOS double-click launcher (generate_digest.command)
- [x] Daily cron at 12 PM

## Phase 2: Source Quality — DONE
- [x] Fix Anthropic Blog collector: remove keyword filter (was dropping Glasswing and non-Claude-named posts)
- [x] Fix Anthropic Blog path filter: accept /glasswing-style URLs, not only /news/
- [x] Add Anthropic Engineering blog collector (anthropic.com/engineering, top 8 posts)
- [x] Wire Anthropic Engineering into General News + official_sources scoring
- [x] Add Anthropic Engineering to PLATFORM_MAP in summarizer_v2.py
- [x] YouTube RSS fix
- [x] OG meta tags for social sharing
- [x] Improved Reddit scoring and tips parsing

## Phase 3: Distribution — NEXT
- [ ] Generate RSS feed (feed.xml) alongside digest.json on each pipeline run
- [ ] Add RSS feed link to site header/footer
- [ ] Explore email digest option (Buttondown or similar, low-friction)

## Phase 4: Quality & Depth
- [ ] Pull full article text for Anthropic Engineering posts (richer LLM summaries)
- [ ] Score and rank engineering posts by recency (no dates exposed — investigate JSON-LD or meta tags)
- [ ] Tune summarizer prompt: reduce flat/generic descriptions
- [ ] Add source diversity guard (cap Reddit/HN to avoid crowding out official sources)
