# Progress Log

## Current Status
**Phase:** Phase 5 — Quality & Depth
**Next action:** Generate an RSS feed (`public/feed.xml`) alongside `digest.json` on each pipeline run

**Live and running daily:** pipeline + site + chat assistant (Asistente IA) + Buttondown newsletter.
**Open items:** email rendering never checked in Apple Mail or Outlook; "Powered by Buttondown" free-tier footer pending Juan's decision; chat prompt occasionally returns 3 links instead of the 2-link cap.

---

## Log

| Date | Description |
|---|---|
| 2026-04-08 | Fixed Anthropic Blog collector: removed keyword filter that was dropping posts like Project Glasswing |
| 2026-04-08 | Fixed Anthropic Blog path filter to accept non-/news/ URLs (e.g. /glasswing) |
| 2026-04-08 | Added Anthropic Engineering blog collector (anthropic.com/engineering, top 8 posts) |
| 2026-04-08 | Wired Anthropic Engineering into General News pool and official_sources scoring |
| 2026-04-08 | Added Anthropic Engineering to PLATFORM_MAP in summarizer_v2.py |
| 2026-04-08 | Ran competitive analysis: identified RSS feed and email delivery as key distribution gaps |
| 2026-04-10 | Rebranded frontend to the BRAND.md design system (Fraunces + Jost + IBM Plex Mono, dual theme) and moved to the claudecodedigest.com domain |
| 2026-04-14 | Switched the scheduler from LaunchAgent to Automator + Calendar; fixed PATH so `npx` resolves under a minimal launch environment |
| 2026-07-12 | Polished frontend UI, updated the byline link, archived legacy summarizer v3 |
| 2026-07-22 | Added the Asistente IA chat: `knowledge.json` archive, `api/chat.js` Vercel Function (Haiku 4.5), floating widget, `backfill_knowledge.py` seed of 190 items, pipeline archive step |
| 2026-07-24 | Shipped Phase 4 newsletter: Buttondown subscribe form (native POST, no proxy), email-safe template, send step with degraded + double-send guards |
| 2026-07-24 | Added `privacy.html` and linked it from the subscribe form |
| 2026-07-24 | Hardened the chat assistant against scraped-content injection and link poisoning (commit `8878505`) |
| 2026-07-25 | Documented the Buttondown newsletter in CLAUDE.md |
| 2026-08-02 | Newsletter reparto changed from 2 features + 2 news to 3 features + 1 news; verified by content against the day's real digest and re-sent to the (single) subscriber |
| 2026-08-02 | Reconciled this plan with reality: Phase 3.5 (chat assistant) added retroactively, Phase 4 marked live, RSS feed moved into Phase 5 |
