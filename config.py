"""Configuration for Claude Code Daily Digest."""

# Site settings
SITE_TITLE = "Claude Code Daily Digest"

# Ollama settings
OLLAMA_MODEL = "llama3.1:8b"

# Source URLs
GITHUB_RELEASES_URL = "https://api.github.com/repos/anthropics/claude-code/releases"
ANTHROPIC_BLOG_RSS_URL = "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml"
CLAUDE_RELEASE_NOTES_URL = "https://support.claude.com/en/articles/12138966-release-notes"
DOCS_CHANGELOG_URL = "https://raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md"
CHASE_AI_BLOG_URL = "https://www.chaseai.io/blog"
CHASE_AI_YOUTUBE_URL = "https://www.youtube.com/@Chase-H-AI/videos"
TYLERGERMAIN_GISTS_URL = "https://gist.github.com/tylergermain"

# Keywords to filter relevant posts
KEYWORDS = ["claude code", "claude-code", "claudecode", "cli"]

# How many hours back to look for updates
LOOKBACK_HOURS = 24

# Anthropic Model
ANTHROPIC_MODEL = "claude-haiku-4-5"