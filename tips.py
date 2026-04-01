"""Daily tips for Claude Code commands and features."""

import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DOCS_CLI_REFERENCE_URL = "https://docs.anthropic.com/en/docs/claude-code/cli-reference"

# Static fallback tips used when the docs fetch fails
TIPS = [
    {
        "command": "/btw",
        "description": "Ask a question while Claude is running a task — no need to interrupt the current work.",
    },
    {
        "command": "/compact",
        "description": "Compress conversation context when you're running low. Keeps the important bits, drops the noise.",
    },
    {
        "command": "/copy N",
        "description": "Copy the Nth-latest assistant response to clipboard. Just `/copy` grabs the most recent one.",
    },
    {
        "command": "/review",
        "description": "Ask Claude to review your code changes before committing — catches bugs and style issues.",
    },
    {
        "command": "/commit",
        "description": "Let Claude generate a commit message from your staged changes and create the commit for you.",
    },
    {
        "command": "/fast",
        "description": "Toggle fast mode for quicker responses using the same Opus model — great for simple tasks.",
    },
    {
        "command": "Shift+Tab",
        "description": "Switch between Plan mode and Act mode. Plan first, then execute — avoids wasted iterations.",
    },
    {
        "command": "/feedback",
        "description": "Send feedback directly to Anthropic about Claude Code. Help shape the tool you use daily.",
    },
    {
        "command": "CLAUDE.md",
        "description": "Add a CLAUDE.md file to your project root with instructions Claude should always follow — persistent context across sessions.",
    },
    {
        "command": "/skills",
        "description": "List all available skills (slash commands). Skills are text prompts that extend Claude's capabilities with specialized workflows.",
    },
    {
        "command": "Hooks",
        "description": "Configure shell commands that run automatically before/after tool calls. Great for auto-formatting, linting, or custom validation.",
    },
    {
        "command": "Esc key",
        "description": "Press Escape to cancel Claude's current operation. Press it twice quickly to clear your input.",
    },
    {
        "command": "/context",
        "description": "Check your current token usage and see how much context window remains. Useful for long sessions.",
    },
    {
        "command": "Agent tool",
        "description": "Claude can spawn sub-agents to handle tasks in parallel — like running tests while writing code.",
    },
    {
        "command": "--resume",
        "description": "Resume your last conversation with `claude --resume`. Pick up exactly where you left off.",
    },
]


def fetch_dynamic_tips():
    """Scrape Claude Code CLI reference docs and return a list of {command, description} tips."""
    try:
        resp = requests.get(
            DOCS_CLI_REFERENCE_URL,
            headers={"User-Agent": "ClaudeCodeUpdates/1.0"},
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        tips = []

        # Strategy 1: table rows (command | description)
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                import re as _re
                command = cells[0].get_text(separator=" ", strip=True)
                description = _re.sub(r'\s+([.,;:/])', r'\1', cells[1].get_text(separator=" ", strip=True))
                if command and len(description) > 10:
                    tips.append({"command": command, "description": description})

        # Strategy 2: definition lists or code elements in list items
        if len(tips) < 3:
            seen = set()
            for code in soup.find_all("code"):
                cmd = code.get_text(strip=True)
                if not cmd or cmd in seen:
                    continue
                if not (cmd.startswith("/") or cmd.startswith("--")):
                    continue
                seen.add(cmd)
                parent = code.find_parent(["li", "p", "dt", "dd"])
                if parent:
                    desc = parent.get_text(separator=" ", strip=True)
                    desc = desc.replace(cmd, "").strip(" –:-")
                    if len(desc) > 15:
                        tips.append({"command": cmd, "description": desc})

        if len(tips) >= 3:
            logger.info(f"Dynamic tips: fetched {len(tips)} tips from docs")
            return tips

        logger.warning("Dynamic tips: not enough entries parsed from docs, using fallback")
        return []

    except Exception as e:
        logger.warning(f"Dynamic tips fetch failed: {e}")
        return []


def get_tip_of_the_day():
    """Return a tip based on today's date, cycling sequentially. Uses live docs when available."""
    epoch = datetime(2025, 1, 1, tzinfo=timezone.utc)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    day_number = (today - epoch).days

    tips = fetch_dynamic_tips() or TIPS
    return tips[day_number % len(tips)]
