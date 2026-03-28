# Claude Code Daily Digest

A self-updating web page that collects, summarizes, and publishes daily Claude Code updates. Runs locally with Python + Anthropic API, deploys to Vercel as a static site.

## How it works

```
LOCAL (cron/manual)                   VERCEL (static hosting)
─────────────────                     ──────────────────────
python generate_digest.py             public/
  → collectors.collect_all()            → index.html  (designed page)
  → summarizer_v2.summarize()          → digest.json (generated data)
  → tips.get_tip_of_the_day()
  → writes public/digest.json
  → vercel deploy --prod
```

1. **Collect** — Fetches updates from GitHub Releases, Anthropic Blog, Claude Release Notes, Docs Changelog, and Chase AI Blog
2. **Summarize** — Sends collected items to Anthropic Haiku for a concise newsletter-style summary
3. **Deploy** — Writes `public/digest.json` and deploys the static site to Vercel

## File structure

```
├── .env                   # ANTHROPIC_API_KEY (gitignored)
├── .env.example           # Required env vars reference
├── .gitignore
├── .vercelignore
├── README.md
├── vercel.json
├── package.json           # Vercel CLI (local dependency)
├── requirements.txt
├── config.py              # Settings
├── collectors.py          # Source collectors
├── summarizer_v2.py       # Anthropic Haiku summarization (active)
├── summarizer.py          # Legacy Ollama summarizer (kept for reference)
├── tips.py                # Daily tips rotation
├── generate_digest.py     # Entry point
├── run_updates.sh         # Runner with deploy
└── public/
    ├── index.html         # Static web page
    └── digest.json        # Generated data (gitignored)
```

## Setup

### Prerequisites

- Python 3.10+
- Anthropic API key ([console.anthropic.com](https://console.anthropic.com))
- [Vercel CLI](https://vercel.com/docs/cli) (installed locally via `npm install`)

### Install

```bash
cd "Claude Code Updates"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm install
```

### Configure API key

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_key_here
```

### Link Vercel project

```bash
npx vercel link
```

## Usage

### Run manually

```bash
source .venv/bin/activate
python generate_digest.py           # Generate digest
npx vercel deploy --prod --yes      # Deploy to Vercel
```

### Run with script

```bash
./run_updates.sh
```

### Schedule via cron

```bash
crontab -e
# Add:
0 8 * * * /full/path/to/Claude\ Code\ Updates/run_updates.sh
```

### CLI options

```bash
python generate_digest.py --collect    # Only collect, print raw items
python generate_digest.py --dry-run    # Collect + summarize, don't write file
```

## Sources

- [Claude Code GitHub Releases](https://github.com/anthropics/claude-code/releases)
- [Anthropic Blog](https://www.anthropic.com/news)
- [Claude Release Notes](https://support.claude.com/en/articles/12138966-release-notes)
- [Anthropic Docs Changelog](https://code.claude.com/docs/en/changelog)
- [Chase AI Blog](https://www.chaseai.io/blog)
