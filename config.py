"""Configuration for Claude Code Daily Digest."""

# Site settings
SITE_TITLE = "Claude Code Daily Digest"

# Ollama settings
OLLAMA_MODEL = "qwen2.5"

# Source URLs
GITHUB_RELEASES_URL = "https://api.github.com/repos/anthropics/claude-code/releases"
ANTHROPIC_BLOG_URL = "https://www.anthropic.com/news"
DOCS_CHANGELOG_URL = "https://docs.anthropic.com/en/docs/changelog"
CHASE_AI_BLOG_URL = "https://www.chaseai.io/blog"

# Keywords to filter relevant posts
KEYWORDS = ["claude code", "claude-code", "claudecode", "cli"]

# How many hours back to look for updates
LOOKBACK_HOURS = 24
