"""Compose the briefing: notes -> model -> ready-to-send email HTML."""

from __future__ import annotations

import datetime as dt
import re
from typing import Any

from . import feeds, llm, notes

# Single surface color for the whole brief (also used for the native window bg,
# so the title bar and content are one uniform color).
LIGHT_BG = "#ffffff"
DARK_BG = "#1e1e1e"

# English weekday names for a nice date in the subject and greeting.
_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _human_date(today: dt.date) -> str:
    return f"{_DAYS[today.weekday()]}, {today.strftime('%d.%m.%Y')}"


def _strip_code_fences(text: str) -> str:
    """Remove any ```html ... ``` fencing from the model's response."""
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def wrap_html(inner: str, title: str) -> str:
    """Wrap the HTML fragment in a clean template that follows the system theme.

    Base styles are inline (light, email-safe everywhere); a dark palette is layered
    on via `prefers-color-scheme` with !important, so the on-screen window and
    dark-mode-aware clients (e.g. Apple Mail) switch to dark, while clients without
    support stay on the safe light version.
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light dark">
<style>
  :root {{ color-scheme: light dark; }}
  .ma-wrap hr {{ border: none; border-top: 1px solid #e6e6ea; margin: 22px 0; }}
  .ma-wrap a {{ color: #2563eb; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: {DARK_BG} !important; color: #ececec !important; }}
    .ma-wrap hr {{ border-top-color: #3a3a3c !important; }}
    .ma-wrap a {{ color: #6ca0ff !important; }}
    .ma-foot {{ color: #8e8e93 !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:{LIGHT_BG};color:#1a1a1a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;line-height:1.55;">
  <div class="ma-wrap" style="max-width:620px;margin:0 auto;padding:34px 28px 26px;">
    {inner}
    <hr>
    <p class="ma-foot" style="text-align:center;color:#9aa0a6;font-size:12px;margin:14px 0 0;">
      {title} · sent by Morning Agent
    </p>
  </div>
</body>
</html>"""


def build_email(cfg: dict[str, Any], today: dt.date | None = None) -> tuple[str, str]:
    """Build (subject, html) for the briefing. Propagates notes/llm errors."""
    today = today or dt.date.today()

    parts: list[str] = []
    notes_dir = (cfg.get("notes_dir") or "").strip()
    note_files = cfg.get("note_files", []) or []
    if notes_dir or note_files:
        note_context = notes.collect_notes(notes_dir, note_files)
        if note_context:
            parts.append(note_context)

    feed_context = feeds.collect_feeds(
        cfg.get("feeds", []),
        cfg.get("feed_items", 5),
        cfg.get("feed_max_age_days", 3),
    )
    if feed_context:
        parts.append("##### RECENT FEED ITEMS (blogs / newsletters) #####\n" + feed_context)

    if not parts:
        raise ValueError(
            "No content source configured — set a notes folder and/or RSS feeds in Settings."
        )

    dated = (
        f"Today's date is {_human_date(today)} ({today.isoformat()}). "
        "Use exactly this date in the greeting; do not invent another date.\n\n"
        + "\n\n".join(parts)
    )
    raw = llm.generate(
        api_key=cfg["openrouter_api_key"],
        model=cfg["model"],
        system_prompt=cfg["prompt"],
        notes=dated,
    )
    inner = _strip_code_fences(raw)

    subject = f"{cfg['subject_prefix']} — {today.isoformat()}"
    html = wrap_html(inner, _human_date(today))
    return subject, html
