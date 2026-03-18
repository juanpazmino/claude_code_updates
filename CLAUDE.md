# CLAUDE.md

## Project Overview

Claude Code Daily Digest — a self-updating web page that collects, summarizes, and publishes daily Claude Code updates. Runs locally with Python + Ollama, deploys to Vercel as a static site.

**Live site:** https://claude-code-digest.vercel.app

## Tech Stack

- **Backend:** Python 3.10+ (requests, beautifulsoup4, ollama)
- **LLM:** Ollama with `qwen2.5` model (local, no API keys)
- **Frontend:** Vanilla HTML/CSS/JS, single `index.html` file
- **Hosting:** Vercel static site (no serverless functions)
- **Deploy tool:** Vercel CLI installed locally via npm (`npx vercel`)

## Pipeline

```
collect (4 sources) → summarize (Ollama) → write digest.json → deploy (Vercel)
```

1. `collectors.py` scrapes GitHub Releases, Anthropic Blog, Docs Changelog, Chase AI Blog
2. `summarizer.py` sends items to Ollama, outputs markdown grouped by: New Features, News, New Versions
3. `generate_digest.py` converts markdown → HTML, adds tip-of-the-day, writes `public/digest.json`
4. `run_updates.sh` runs the pipeline + `npx vercel deploy --prod --yes`

## Key Commands

```bash
source .venv/bin/activate
python generate_digest.py              # Generate digest
python generate_digest.py --collect    # Only collect, print raw items
python generate_digest.py --dry-run    # Collect + summarize, don't write
npx vercel deploy --prod --yes         # Deploy to Vercel
./run_updates.sh                       # Full pipeline + deploy
```

## Conventions

- Config in `config.py` (UPPERCASE constants, no personal data)
- Collectors return standardized items: `{title, date, content, source, url}`
- Error handling: try/except with `logging.warning`, graceful degradation
- Logging: module-based `logging.getLogger(__name__)` pattern
- Frontend: dark theme (#0d0d0d bg, #C46849 accent), DM Sans + JetBrains Mono fonts
- Vercel CLI is local (use `npx vercel`, not `vercel`)
- `public/digest.json` is gitignored — generated artifact, not source

## Rules

- All Playwright screenshots must be saved to the `screenshots_playwright/` folder, not the project root.

## Important Notes

- Ollama must be running before `generate_digest.py` (`ollama serve`)
- No API keys needed — all sources are public, LLM is local
- Cron at 8 AM daily: `0 8 * * * /path/to/Claude\ Code\ Updates/run_updates.sh`
- The summarizer prompt explicitly separates features vs news vs versions — if categorization is wrong, adjust the prompt in `summarizer.py`
