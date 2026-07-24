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

## Phase 3: Analytics & Insights — DONE
Goal: understand who visits, where they come from, what they read, and how the site grows.

**Stack:** Vercel Web Analytics + Vercel Speed Insights (both native to Vercel dashboard)

- [x] Enable Vercel Web Analytics in the Vercel dashboard (project → Analytics tab)
- [x] Add `@vercel/analytics` script tag to `public/index.html`
- [x] Add Vercel Speed Insights script tag to `public/index.html`

## Phase 4: Newsletter
Goal: let readers subscribe and receive the daily digest by email automatically.

**Service:** Buttondown (account live, newsletter `pazmino`, free tier ≤100 subscribers).
Confirmation flow (double opt-in) is ON by default → GDPR/LOPDGDD covered. Public page: https://buttondown.com/pazmino

**Design decision — no serverless proxy.** The subscribe endpoint (`https://buttondown.com/api/emails/embed-subscribe/pazmino`) is public, so there is no API key to hide. Use Buttondown's native `<form>` POST, styled 100% in brand — no `/api/subscribe` function. (The `ANTHROPIC_API_KEY`-style secrecy that justifies the chat's `api/chat.js` does not apply here.)

**Two distinct surfaces, different brand fidelity:**
- Subscribe form (lives on the site) → ~100% brand, our own styled HTML
- Email body (lands in the inbox) → ~60-80% brand — email-safe HTML: inline styles, tables, serif fallback for Fraunces, no CSS variables / grain / `data-theme`

### 4a — Subscribe form (small)
- [ ] Add styled native `<form>` to `public/index.html` posting to the Buttondown embed endpoint; brand the input/button/success + error states
- [ ] Optional: submit via `fetch()` to stay on-page instead of redirecting to Buttondown
- [ ] Add `buttondown.com` to `form-action`/`connect-src` in `vercel.json` CSP

### 4b — Email body template (the real work)
- [ ] Build an email-safe HTML template from the same structured items the digest already produces (not from `public/digest.json`, which targets browser HTML)
- [ ] Serif fallback for Fraunces; gold accents; clean single-column layout
- [ ] Test rendering in Gmail + Apple Mail + Outlook before first send

### 4c — Send integration (in `run_updates.sh`, from the Mac, after deploy)
- [ ] Send via `POST https://api.buttondown.com/v1/emails` (Token auth, key in `.env` local only)
- [ ] Guard 1 — do not send if the digest came back degraded (the ⚠️ silent-summarizer-failure case)
- [ ] Guard 2 — do not double-send on a manual re-run (create as draft, or a "sent today" marker)

### 4d — Compliance
- [ ] Privacy note linked from the form (reuse the personal-site `privacy.html` shape)
- [ ] Confirm "Powered by Buttondown" free-tier footer is acceptable, or plan the paid tier to remove it

## Phase 5: Quality & Depth
- [ ] Pull full article text for Anthropic Engineering posts (richer LLM summaries)
- [ ] Score and rank engineering posts by recency (no dates exposed — investigate JSON-LD or meta tags)
- [ ] Tune summarizer prompt: reduce flat/generic descriptions
- [ ] Add source diversity guard (cap Reddit/HN to avoid crowding out official sources)
