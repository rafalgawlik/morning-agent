"""Morning Agent — menu bar app that emails you a morning briefing.

Flow:
    menu bar (rumps)  ->  notes (reads a folder)  ->  llm (OpenRouter)  ->  mailer (Resend)

Configuration lives in ~/.config/morning-agent/config.json.
"""

__version__ = "1.0.0"
