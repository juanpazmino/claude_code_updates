#!/usr/bin/env python3
"""Email-safe HTML template for the Claude Code Daily Digest (Buttondown).

BUILD-AND-REVIEW ONLY — not wired into run_updates.sh / generate_digest.py.
Nothing here sends mail; it only renders HTML for manual review.

Input shape matches public/digest.json exactly (generated_at, date_display,
summary_html, tip), so the pipeline's existing output can be handed straight
to render_email_html() once this is ever wired up. summary_html is parsed
(rather than re-deriving from raw markdown) to avoid duplicating the
markdown parsing logic that already lives in generate_digest.py.

Email clients are not browsers: no CSS variables, no external fonts, no
box-shadow/grain/vignette tricks, no <script>. Everything below is inline
styles on a table-based layout, targeting Gmail/Outlook/Apple Mail.
Colors are flattened, opaque hex — derived by blending the light-mode rgba
tokens from BRAND.md over the light-mode --bg (#F5F0E8), since translucent
colors are unreliable across email clients.
"""

import html
from html.parser import HTMLParser

# ── Flattened brand colors (light mode only — email ignores prefers-color-scheme) ──
# Each value below is BRAND.md's light-mode rgba token composited over --bg #F5F0E8,
# rounded to the nearest hex. See module docstring for why: email clients render
# alpha channels inconsistently, so an opaque approximation is more reliable.
BG = "#F5F0E8"          # --bg, used as-is (already opaque)
SURFACE = "#FFFCF7"     # --surface rgba(255,252,247,0.95) over --bg
GOLD = "#97773B"        # --gold rgba(140,105,40,0.90) over --bg
GOLD_HI = "#897246"     # --gold-hi rgba(110,82,30,0.80) over --bg
TEXT = "#363330"        # --cream rgba(20,18,14,0.85) over --bg (near-black body text)
MUTED = "#85817B"       # --muted rgba(20,18,14,0.50) over --bg
BORDER = "#E8E3DB"      # rgba(20,18,14,0.06) over --bg — hairline separators
TIP_BG = "#F1E9D8"      # rgba(140,105,40,0.06) over --bg — tip box tint

# Font stacks standing in for the brand fonts, which won't load in mail clients.
SERIF = "Georgia, 'Times New Roman', Times, serif"      # stands in for Fraunces
SANS = "Arial, Helvetica, sans-serif"                    # stands in for Jost
MONO = "'Courier New', Courier, monospace"               # stands in for IBM Plex Mono


def get_subject_line(date_display):
    """Return the Buttondown subject line, e.g. 'Claude Code Daily Digest · July 24, 2026'.

    date_display is expected in the "%B %d, %Y" format generate_digest.py already writes.
    """
    return f"Claude Code Daily Digest · {date_display}"


class _SectionParser(HTMLParser):
    """Extracts sections/items from generate_digest.markdown_to_html() output.

    That function always emits this stable shape:
      <section class="section"><h2 class="section-heading">HEADING</h2>
        <div class="item">
          <div class="item-title">TITLE</div>   (optional — New Versions has none)
          <div class="item-desc">DESC</div>
          <a class="item-link" href="URL">LINK TEXT</a>  (optional)
        </div>
        ...
      </section>
    """

    def __init__(self):
        super().__init__()
        self.sections = []
        self._section = None
        self._item = None
        self._field = None   # 'heading' | 'title' | 'desc' | 'link' | None
        self._href = ""

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "")
        if tag == "h2" and "section-heading" in cls:
            self._field = "heading"
        elif tag == "div" and cls == "item":
            self._item = {"title": "", "desc": "", "link_text": "", "link_href": ""}
        elif tag == "div" and "item-title" in cls:
            self._field = "title"
        elif tag == "div" and "item-desc" in cls:
            self._field = "desc"
        elif tag == "a" and "item-link" in cls:
            self._field = "link"
            self._href = dict(attrs).get("href", "")

    def handle_endtag(self, tag):
        if tag == "section":
            if self._section:
                self.sections.append(self._section)
            self._section = None
        elif tag == "div" and self._field in ("title", "desc"):
            self._field = None
        elif tag == "a" and self._field == "link":
            if self._item is not None:
                self._item["link_href"] = self._href
            self._field = None
        elif tag == "div" and self._item is not None and self._field is None:
            # Closing tag of the outer <div class="item">
            if self._section is not None:
                self._section["items"].append(self._item)
            self._item = None

    def handle_data(self, data):
        if self._field == "heading":
            self._section = {"heading": data.strip(), "items": []}
            self._field = None
        elif self._field == "title" and self._item is not None:
            self._item["title"] += data
        elif self._field == "desc" and self._item is not None:
            self._item["desc"] += data
        elif self._field == "link" and self._item is not None:
            self._item["link_text"] += data


def _parse_sections(summary_html):
    parser = _SectionParser()
    parser.feed(summary_html or "")
    return parser.sections


def _esc(text):
    return html.escape((text or "").strip())


def _safe_href(url):
    """Only allow http(s) links — mirrors the boundary check generate_digest._safe_link does."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return ""
    return html.escape(url, quote=True)


def _render_item(item, is_last):
    border = "border-bottom:1px solid " + BORDER + ";" if not is_last else ""
    title_html = ""
    if item["title"]:
        title_html = (
            f'<div style="font-family:{SERIF};font-size:16px;line-height:1.3;'
            f'color:{GOLD_HI};margin:0 0 8px;">{_esc(item["title"])}</div>'
        )
    desc_html = ""
    if item["desc"]:
        desc_html = (
            f'<div style="font-family:{SANS};font-size:13px;line-height:1.6;'
            f'color:{MUTED};margin:0 0 10px;">{_esc(item["desc"])}</div>'
        )
    link_html = ""
    href = _safe_href(item["link_href"])
    if href and item["link_text"]:
        link_html = (
            f'<a href="{href}" style="font-family:{SANS};font-style:italic;'
            f'font-size:13px;color:{GOLD};text-decoration:none;">{_esc(item["link_text"])}</a>'
        )
    return (
        f'<tr><td style="padding:18px 0;{border}">{title_html}{desc_html}{link_html}</td></tr>'
    )


def _render_cta():
    """Final call-to-action shown just before the byline/footer.

    'Read more at:' in plain gold, with only the domain bold + underlined as the
    clickable link — a quiet nudge back to the site for the items that didn't make
    the 4-item cut.
    """
    href = "https://www.claudecodedigest.com"
    return (
        f'<div style="margin:0 0 48px;font-family:{SANS};font-size:17px;color:{GOLD};text-align:center;">'
        f'Read more at:<br>'
        f'<a href="{href}" style="color:{GOLD};font-weight:bold;text-decoration:underline;">www.claudecodedigest.com</a>'
        f'</div>'
    )


def _render_section(section, cta_html="", show_heading=True):
    # The merged News & Features section omits its heading (show_heading=False):
    # that heading lives in the email header alongside the date instead.
    spacer = '<tr><td style="padding-bottom:16px;"></td></tr>' if show_heading else ""
    heading = ""
    if show_heading:
        heading = (
            f'<tr><td style="padding:0 0 14px;border-bottom:1px solid {GOLD};">'
            f'<span style="font-family:{MONO};font-size:12px;font-weight:bold;color:{GOLD};'
            f'letter-spacing:2px;text-transform:uppercase;">{_esc(section["heading"])}</span>'
            f'</td></tr>'
        )
    items = section["items"]
    rows = "".join(_render_item(it, i == len(items) - 1) for i, it in enumerate(items))
    return (
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="margin:0 0 4px;">{spacer}'
        f'{heading}{rows}{cta_html}</table>'
    )


def _render_tip(tip):
    command = _esc(tip.get("command"))
    description = _esc(tip.get("description"))
    if not command:
        return ""
    return f"""
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 36px;">
      <tr><td style="padding:0 0 14px;border-bottom:1px solid {GOLD};">
        <span style="font-family:{MONO};font-size:12px;font-weight:bold;color:{GOLD};letter-spacing:2px;text-transform:uppercase;">Tip of the Day</span>
      </td></tr>
      <tr><td style="padding:18px 0 0;">
        <div style="font-family:{MONO};font-size:14px;color:{GOLD_HI};margin:0 0 8px;">{command}</div>
        <div style="font-family:{SANS};font-size:12px;line-height:1.6;color:{MUTED};">{description}</div>
      </td></tr>
    </table>"""


def render_email_html(digest):
    """Render a complete email-safe HTML document from a digest.json-shaped dict.

    Expects the keys generate_digest.py already writes to public/digest.json:
    generated_at, date_display, summary_html, tip. Unknown/missing keys degrade
    gracefully (empty sections/tip are simply omitted).

    The email is intentionally shorter than the site: "New Features" and
    "General News" are merged into one "News & Features" section (first 2
    items from each, 4 total) with a section-level CTA back to the site for
    anyone who wants the rest. "New Versions" is dropped entirely — version
    bumps read as noise in an inbox digest.
    """
    date_display = digest.get("date_display", "")
    sections = _parse_sections(digest.get("summary_html", ""))
    tip = digest.get("tip") or {}

    features = next((s for s in sections if s["heading"] == "New Features"), None) or {"items": []}
    news = next((s for s in sections if s["heading"] == "General News"), None) or {"items": []}
    merged_items = features["items"][:2] + news["items"][:2]

    sections_html = ""
    if merged_items:
        merged_section = {"heading": "News & Features", "items": merged_items}
        sections_html = _render_section(merged_section, show_heading=False)

    tip_html = _render_tip(tip)
    cta_html = _render_cta() if merged_items else ""
    subject = get_subject_line(date_display)

    return f"""<!doctype html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<title>{_esc(subject)}</title>
<!--[if mso]>
<style type="text/css">
table {{ border-collapse: collapse; }}
</style>
<![endif]-->
</head>
<body style="margin:0;padding:0;background-color:{BG};">
<!-- Preheader (hidden, improves inbox preview text) -->
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">
  Today's Claude Code features, news, and latest version — curated automatically.
</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{BG};">
<tr><td align="center" style="padding:24px 0;">

<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background-color:{BG};">

  <!-- Header: News & Features label + date, sharing the gold section rule -->
  <tr><td style="padding:8px 32px 0;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:1px solid {GOLD};">
      <tr>
        <td style="padding:0 0 14px;font-family:{MONO};font-size:12px;font-weight:bold;color:{GOLD};letter-spacing:2px;text-transform:uppercase;">News &amp; Features</td>
        <td align="right" style="padding:0 0 14px;font-family:{MONO};font-size:13px;color:{MUTED};white-space:nowrap;">{_esc(date_display)}</td>
      </tr>
    </table>
  </td></tr>

  <!-- Body: News & Features items, Tip, read-more CTA, then the byline before the footer -->
  <tr><td style="padding:8px 32px 0;">
    {sections_html}
    {tip_html}
    {cta_html}
    <div style="font-family:{SANS};font-size:10px;color:{GOLD_HI};text-align:right;margin:0 0 4px;">
      Built by <a href="https://www.juanpazminob.com" style="color:{GOLD_HI};font-weight:bold;text-decoration:underline;">Juan Pazmino B, AI Consultant</a>
    </div>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:0 32px 40px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:1px solid {BORDER};">
      <tr><td style="padding:24px 0 0;">
        <div style="font-family:{MONO};font-size:10px;line-height:1.5;color:{MUTED};">
          &copy; 2026 Juan Pazmino B &middot; AI Consultant &middot; Independent, unofficial aggregator — not affiliated with Anthropic, PBC. &ldquo;Claude&rdquo; and &ldquo;Claude Code&rdquo; are trademarks of Anthropic, PBC.
        </div>
        <!--
          Buttondown auto-appends its required unsubscribe link below the content it
          sends — do not hand-roll one here. This comment marks where it will land
          when this template is actually wired into a send.
        -->
      </td></tr>
    </table>
  </td></tr>

</table>

</td></tr>
</table>
</body>
</html>
"""


if __name__ == "__main__":
    # Manual review helper: render against the real generated digest.json and
    # write email_sample.html next to this file. Does not send anything.
    import json
    import os

    root = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(root, "public", "digest.json")) as f:
        digest = json.load(f)

    out_path = os.path.join(root, "email_sample.html")
    with open(out_path, "w") as f:
        f.write(render_email_html(digest))

    print(f"Subject: {get_subject_line(digest.get('date_display', ''))}")
    print(f"Wrote {out_path}")
