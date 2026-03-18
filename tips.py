"""Daily tips for Claude Code commands and features."""

import hashlib
from datetime import datetime, timezone

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


def get_tip_of_the_day():
    """Return a deterministic tip based on today's date."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    index = int(hashlib.md5(today.encode()).hexdigest(), 16) % len(TIPS)
    return TIPS[index]
