"""Loading and saving the app configuration and state.

Config: ~/.config/morning-agent/config.json  (editable via the UI and by hand)
State:  ~/.config/morning-agent/state.json    (e.g. the date of the last send)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "morning-agent"
CONFIG_PATH = CONFIG_DIR / "config.json"
STATE_PATH = CONFIG_DIR / "state.json"

# Default instruction for the model. Can be overridden in config.json ("prompt").
DEFAULT_PROMPT = """You are an assistant that writes a short, warm morning briefing in English.
Using the user's notes ATTACHED BELOW (todos, projects, plans), generate the message.

Return a CLEAN HTML fragment to embed in an email body — no <html>, <head>, <body>,
no code blocks and no triple backticks. Use only: <h2>, <h3>, <p>, <ul>, <li>,
<strong>, <em>, <hr>, <a>.

LINKS — IMPORTANT: each RSS feed item below includes a line with its URL. Whenever you
mention an article/post/newsletter, turn its title into a clickable link:
<a href="EXACT_URL_FROM_THE_DATA">title</a>. Never invent URLs — use only the URLs given.

Structure:
1. A short, friendly greeting with today's date.
2. ✅ <strong>Today</strong> — 3–6 most important things to do, pulled from the notes
   (focus on unchecked "- [ ]" items and sections like "Next steps"). Skip if there are no notes.
3. 📰 <strong>Latest reads</strong> — the 4–6 most interesting recent feed items, each as a
   clickable <a href> with a one-line reason to read it. Skip this section only if there are
   no feed items.
4. 💡 <strong>Good news / motivation</strong> — one positive, uplifting sentence.
5. One closing sentence to set up a good day.

Be concise and concrete. If there are few notes, still produce a sensible, motivating
briefing. Output ONLY the HTML, nothing else."""

DEFAULTS: dict[str, Any] = {
    # --- Mail (Resend) ---
    "resend_api_key": "",
    "sender": "",
    "recipient": "",
    "subject_prefix": "☀️ Morning briefing",
    # --- Model (OpenRouter) ---
    "openrouter_api_key": "",
    "model": "anthropic/claude-haiku-4.5",
    # --- Content sources ---
    "note_files": [],       # curated list of specific note file paths
    "notes_dir": "",        # optional: a folder scanned recursively
    "feeds": [],            # list of RSS/Atom feed URLs
    "feed_items": 5,        # max items pulled per feed
    "feed_max_age_days": 3, # only include items from the last N days (0 = no limit)
    "prompt": DEFAULT_PROMPT,
    # --- Delivery & schedule ---
    "delivery_mode": "email",  # "email" | "screen" | "both"
    "send_time": "07:00",      # HH:MM, 24h
    "autosend": False,         # whether to deliver automatically at send_time
}


def load_config() -> dict[str, Any]:
    """Return the configuration (defaults + whatever is stored on disk)."""
    cfg = dict(DEFAULTS)
    try:
        if CONFIG_PATH.exists():
            with CONFIG_PATH.open(encoding="utf-8") as fh:
                stored = json.load(fh)
            if isinstance(stored, dict):
                cfg.update(stored)
    except (OSError, json.JSONDecodeError):
        # Corrupted file — fall back to defaults instead of crashing.
        pass
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)


def set_value(key: str, value: Any) -> dict[str, Any]:
    """Set a single config key and save. Returns the new configuration."""
    cfg = load_config()
    cfg[key] = value
    save_config(cfg)
    return cfg


def load_state() -> dict[str, Any]:
    try:
        if STATE_PATH.exists():
            with STATE_PATH.open(encoding="utf-8") as fh:
                return json.load(fh)
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def save_state(state: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with STATE_PATH.open("w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def ensure_config_file() -> Path:
    """Create the config file with default values if it does not exist."""
    if not CONFIG_PATH.exists():
        save_config(dict(DEFAULTS))
    return CONFIG_PATH
