"""Read notes and merge them into context for the model.

Two ways to provide notes (both optional, can be combined):
  * a curated list of specific files (recommended — precise and cheap), and/or
  * a folder that is scanned recursively (newest files first, with caps).
"""

from __future__ import annotations

import os
from pathlib import Path

# Extensions treated as text notes when scanning a folder.
NOTE_EXTENSIONS = {".md", ".markdown", ".txt", ".mdx"}

# Limits so we never send a huge prompt to the model.
MAX_FOLDER_FILES = 40
MAX_CHARS_PER_FILE = 8_000
MAX_TOTAL_CHARS = 60_000

# Folders skipped while scanning.
SKIP_DIRS = {".git", ".obsidian", ".trash", "node_modules", ".DS_Store"}


def _read_block(path: Path, label: str) -> str | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not text:
        return None
    if len(text) > MAX_CHARS_PER_FILE:
        text = text[:MAX_CHARS_PER_FILE] + "\n…(truncated)…"
    return f"===== FILE: {label} =====\n{text}\n"


def collect_notes(notes_dir: str = "", files: list[str] | None = None) -> str:
    """Return merged notes content as a single string (or "" if nothing).

    `files` — explicit paths chosen by the user; always included first.
    `notes_dir` — optional folder scanned recursively (newest first).
    Never raises: missing files/folders are simply skipped.
    """
    blocks: list[str] = []
    total = 0
    seen: set[str] = set()

    def add(path: Path, label: str) -> bool:
        """Append a file's block; return False when the total cap is reached."""
        nonlocal total
        key = str(path.resolve())
        if key in seen:
            return True
        block = _read_block(path, label)
        if block is None:
            return True
        if total + len(block) > MAX_TOTAL_CHARS:
            return False
        seen.add(key)
        blocks.append(block)
        total += len(block)
        return True

    # 1) Curated files first — the user chose exactly these.
    for f in files or []:
        p = Path(f).expanduser()
        if p.is_file():
            if not add(p, p.name):
                break

    # 2) Optional folder scan (newest modified first).
    root = Path(notes_dir).expanduser() if notes_dir else None
    if root and root.is_dir():
        found: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
            for name in filenames:
                if Path(name).suffix.lower() in NOTE_EXTENSIONS:
                    found.append(Path(dirpath) / name)
        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for p in found[:MAX_FOLDER_FILES]:
            if not add(p, str(p.relative_to(root))):
                break

    return "\n".join(blocks)
