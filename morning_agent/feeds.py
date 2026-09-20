"""Fetch and parse RSS/Atom feeds using only the standard library + requests.

We deliberately avoid third-party parsers (feedparser) so the app keeps zero
extra dependencies — which also keeps the Homebrew formula simple.
"""

from __future__ import annotations

import datetime as dt
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

TIMEOUT = 20               # seconds per feed
DEFAULT_PER_FEED = 5       # max items taken from each feed
MAX_SUMMARY = 400          # chars of each item's summary
MAX_TOTAL_CHARS = 24_000   # overall cap for the feed context

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _local(tag: str) -> str:
    """Return an element's local name, dropping any XML namespace."""
    return tag.rsplit("}", 1)[-1]


def _children(parent: ET.Element, name: str) -> list[ET.Element]:
    return [c for c in list(parent) if _local(c.tag) == name]


def _child(parent: ET.Element, name: str) -> ET.Element | None:
    for c in list(parent):
        if _local(c.tag) == name:
            return c
    return None


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


def _clean(text: str) -> str:
    """Strip HTML tags and collapse whitespace to a short plain summary."""
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", text or "")).strip()


def _all_by_name(root: ET.Element, name: str) -> list[ET.Element]:
    return [e for e in root.iter() if _local(e.tag) == name]


def _parse_date(text: str) -> dt.datetime | None:
    """Parse an RSS (RFC 822) or Atom (ISO 8601) date into an aware datetime."""
    text = (text or "").strip()
    if not text:
        return None
    # RSS: "Mon, 21 Sep 2026 04:28:44 +0000"
    try:
        d = parsedate_to_datetime(text)
        if d is not None:
            return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except (TypeError, ValueError):
        pass
    # Atom: "2026-09-20T17:12:49-04:00" (also handle a trailing Z)
    try:
        d = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def parse_feed(xml_bytes: bytes) -> tuple[str, list[dict]]:
    """Parse RSS 2.0 / RSS 1.0 / Atom. Returns (feed_title, [entries])."""
    root = ET.fromstring(xml_bytes)

    # Feed title: <channel><title> (RSS) or <feed><title> (Atom).
    channel = _child(root, "channel")
    title_holder = channel if channel is not None else root
    feed_title = _text(_child(title_holder, "title"))

    items = _all_by_name(root, "item")          # RSS 2.0 / 1.0
    kind = "item"
    if not items:
        items = _all_by_name(root, "entry")     # Atom
        kind = "entry"

    entries: list[dict] = []
    for it in items:
        title = _text(_child(it, "title"))
        if kind == "entry":
            # Atom: prefer a rel="alternate" link, else the first <link href>.
            link = ""
            for link_el in _children(it, "link"):
                href = link_el.get("href", "")
                if link_el.get("rel", "alternate") == "alternate" and href:
                    link = href
                    break
                link = link or href
            date = _text(_child(it, "updated")) or _text(_child(it, "published"))
            summary = _text(_child(it, "summary")) or _text(_child(it, "content"))
        else:
            link_el = _child(it, "link")
            link = _text(link_el)
            date = _text(_child(it, "pubDate")) or _text(_child(it, "date"))
            summary = _text(_child(it, "description"))
        entries.append({
            "title": title,
            "link": link,
            "date": date,
            "when": _parse_date(date),
            "summary": _clean(summary)[:MAX_SUMMARY],
        })
    return feed_title, entries


def _recent_first(entries: list[dict], max_age_days: int | None) -> list[dict]:
    """Keep only items from the last `max_age_days` days, newest first.

    Items without a parseable date are kept (we can't tell their age) and sorted
    after the dated ones.
    """
    if max_age_days and max_age_days > 0:
        cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=max_age_days)
        entries = [e for e in entries if e["when"] is None or e["when"] >= cutoff]
    # Newest first; undated items go last.
    entries.sort(key=lambda e: e["when"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                 reverse=True)
    return entries


def collect_feeds(urls: list[str] | None, per_feed: int = DEFAULT_PER_FEED,
                  max_age_days: int | None = None) -> str:
    """Fetch every feed and return a single text block of recent items.

    Only items from the last `max_age_days` days are included (None = no limit).
    Never raises — a feed that fails to load is noted inline so the briefing can
    still go out.
    """
    if not urls:
        return ""

    blocks: list[str] = []
    total = 0
    for url in urls:
        url = (url or "").strip()
        if not url:
            continue
        try:
            resp = requests.get(url, timeout=TIMEOUT,
                                headers={"User-Agent": "MorningAgent/1.0"})
            resp.raise_for_status()
            title, entries = parse_feed(resp.content)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully per feed
            blocks.append(f"===== FEED: {url} (could not load: {exc}) =====")
            continue

        entries = _recent_first(entries, max_age_days)
        if not entries:
            continue  # nothing recent enough — skip this feed quietly

        lines = [f"===== FEED: {title or url} ====="]
        for e in entries[:per_feed]:
            date = f" ({e['date']})" if e["date"] else ""
            lines.append(f"- {e['title']}{date}")
            if e["summary"]:
                lines.append(f"  {e['summary']}")
            if e["link"]:
                lines.append(f"  {e['link']}")
        block = "\n".join(lines)
        if total + len(block) > MAX_TOTAL_CHARS:
            break
        blocks.append(block)
        total += len(block)

    return "\n\n".join(blocks)
