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

## Phase 3.5: Chat Assistant (Asistente IA) — DONE
Goal: answer Claude Code questions from the archive the digest already accumulates.
Built 2026-07-22, hardened 2026-07-24. Not planned in advance — added here retroactively so the plan matches reality.

- [x] `knowledge.json` permanent append-only archive, fed by each pipeline run
- [x] `backfill_knowledge.py` one-off seed from `seen_urls.json` (190 items, run 2026-07-22)
- [x] `api/chat.js` Vercel Function — Haiku 4.5, full knowledge inlined with prompt caching, sole holder of the API key
- [x] Floating widget (`chatbot.js` / `chatbot.css`) cloned from the juanpazminob.com bot, "Asistente IA" label for EU AI Act Art. 50
- [x] In-memory rate limit (20 req / 10 min per IP) + request validation
- [x] `dev/server.mjs` local harness emulating the Function
- [x] Security hardening (commit `8878505`): scraped-content injection fence + deterministic URL allow-list belt
- [ ] Prompt occasionally returns 3 links instead of the 2-link cap — open fine-tuning

## Phase 4: Newsletter — LIVE since 2026-07-24 · 2 open items
Goal: let readers subscribe and receive the daily digest by email automatically.

**Service:** Buttondown (account live, newsletter `pazmino`, free tier ≤100 subscribers).
Confirmation flow (double opt-in) is ON by default → GDPR/LOPDGDD covered. Public page: https://buttondown.com/pazmino

**Design decision — no serverless proxy.** The subscribe endpoint (`https://buttondown.com/api/emails/embed-subscribe/pazmino`) is public, so there is no API key to hide. Use Buttondown's native `<form>` POST, styled 100% in brand — no `/api/subscribe` function. (The `ANTHROPIC_API_KEY`-style secrecy that justifies the chat's `api/chat.js` does not apply here.)

**Two distinct surfaces, different brand fidelity:**
- Subscribe form (lives on the site) → ~100% brand, our own styled HTML
- Email body (lands in the inbox) → ~60-80% brand — email-safe HTML: inline styles, tables, serif fallback for Fraunces, no CSS variables / grain / `data-theme`

### 4a — Subscribe form (small)
- [x] Add styled native `<form>` to `public/index.html` posting to the Buttondown embed endpoint; brand the input/button/success + error states
- [~] Optional: submit via `fetch()` to stay on-page instead of redirecting to Buttondown — **dropped.** The native form POST works and needs no `connect-src` widening; the redirect to Buttondown's confirmation page is acceptable.
- [x] Add `buttondown.com` to `form-action` in `vercel.json` CSP (`connect-src` not needed — no `fetch()`)

### 4b — Email body template (the real work)
- [x] Build an email-safe HTML template (`email_template.py`) — table layout, inline styles, flattened opaque light-mode brand colors
- [x] Serif fallback for Fraunces (Georgia); gold accents; clean single-column layout
- [x] Merge **New Features** + **General News** into one 4-item **News & Features** block; drop **New Versions** — the email is deliberately shorter than the site
- [x] Reparto changed 2+2 → **3 features + 1 news** (2026-08-02), verified by content against a real digest
- [ ] Test rendering in Apple Mail + Outlook — **Gmail verified live** (2026-08-02); the other two clients never checked

### 4c — Send integration (in `run_updates.sh`, from the Mac, after deploy)
- [x] Send via `POST https://api.buttondown.com/v1/emails` (Token auth, key local only) — `send_email.py`
- [x] Guard 1 — do not send if the digest came back degraded (the ⚠️ silent-summarizer-failure case)
- [x] Guard 2 — do not double-send on a manual re-run (`.email_sent.json` "sent today" marker)
- [x] `X-Buttondown-Live-Dangerously: true` header — required since API version 2026-04-01 made `draft` the default

### 4d — Compliance
- [x] Privacy note linked from the form (`public/privacy.html`, commit `19a1849`)
- [ ] Confirm "Powered by Buttondown" free-tier footer is acceptable, or plan the paid tier to remove it — **needs Juan's call**

## Phase 5: Quality & Depth — NEXT
- [ ] Generate an RSS feed (`public/feed.xml`) alongside `digest.json` on each pipeline run — carried over from the April 2026 distribution analysis, never built; it was PROGRESS.md's stale "next action" for four months
- [ ] Pull full article text for Anthropic Engineering posts (richer LLM summaries)
- [ ] Score and rank engineering posts by recency (no dates exposed — investigate JSON-LD or meta tags)
- [ ] Tune summarizer prompt: reduce flat/generic descriptions
- [ ] Add source diversity guard (cap Reddit/HN to avoid crowding out official sources)
