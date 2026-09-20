"""Menu bar app (rumps): icon, menu, settings and the send schedule."""

from __future__ import annotations

import datetime as dt
import os
import subprocess
import threading

import rumps

from . import __version__, config
from .composer import build_email
from .mailer import send_email

_ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
# Menu bar icon — a template PNG that macOS tints for light/dark bars.
ICON_PATH = os.path.join(_ASSETS, "sun.png")
# Dock / Cmd-Tab icon — a full-color sun tile.
APP_ICON_PATH = os.path.join(_ASSETS, "app_icon.png")
# Frames for the spinning-sun loading animation.
SPIN_FRAMES = [os.path.join(_ASSETS, f"sun_spin_{i:02d}.png") for i in range(12)]
SPIN_FRAMES = [p for p in SPIN_FRAMES if os.path.exists(p)]
# Fallback glyph if the icon file is missing for any reason.
FALLBACK_TITLE = "☀"

APP_NAME = "Morning Agent"

# Set in __init__ so the Dock-reopen handler can reach the running app.
_APP_INSTANCE: "MorningAgentApp | None" = None


def _set_app_name(name: str = APP_NAME) -> None:
    """Rename the process from 'Python' to Morning Agent in menus / switcher."""
    try:
        from Foundation import NSBundle
        bundle = NSBundle.mainBundle()
        for getter in ("localizedInfoDictionary", "infoDictionary"):
            info = getattr(bundle, getter)()
            if info is not None:
                info["CFBundleName"] = name
                info["CFBundleDisplayName"] = name
    except Exception:
        pass


def _install_reopen_handler() -> None:
    """Make a Dock-icon click open the Settings window (via rumps' delegate)."""
    try:
        import rumps.rumps as _rr
        if getattr(_rr.NSApp, "_ma_reopen", False):
            return

        class _MANSApp(_rr.NSApp):
            def applicationShouldHandleReopen_hasVisibleWindows_(self, _app, _flag):
                try:
                    if _APP_INSTANCE is not None:
                        _APP_INSTANCE.open_settings()
                except Exception:
                    pass
                return True

        _MANSApp._ma_reopen = True
        _rr.NSApp = _MANSApp
    except Exception:
        pass


@rumps.notifications
def _on_notification_clicked(_notification) -> None:
    """Clicking the 'brief ready' notification opens today's brief on screen."""
    try:
        if _APP_INSTANCE is not None:
            _APP_INSTANCE.show_today()
    except Exception:
        pass


class MorningAgentApp(rumps.App):
    def __init__(self) -> None:
        has_icon = os.path.exists(ICON_PATH)
        super().__init__(
            "Morning Agent",
            icon=ICON_PATH if has_icon else None,
            title=None if has_icon else FALLBACK_TITLE,
            template=True,
            quit_button="Quit",
        )
        global _APP_INSTANCE
        _APP_INSTANCE = self
        _set_app_name()
        self._set_dock_icon()
        config.ensure_config_file()
        self.cfg = config.load_config()
        self._sending = False
        self._anim_timer = None
        self._anim_i = 0
        self._last_msg = "nothing sent yet"
        self._today_date: str | None = None
        self._today_subject: str | None = None
        self._today_html: str | None = None

        # --- Menu items (kept as attributes so we can update their titles) ---
        self.status_item = rumps.MenuItem("Status: …")
        self.autosend_item = rumps.MenuItem("Auto-send", callback=self.toggle_autosend)

        self.menu = [
            self.status_item,
            None,
            rumps.MenuItem("🗒  Today note", callback=self.today_note),
            rumps.MenuItem("▶︎  Deliver now", callback=self.send_now),
            rumps.MenuItem("👀  Preview (screen only)", callback=self.preview),
            None,
            rumps.MenuItem("⚙️  Settings…", callback=self.open_settings),
            self.autosend_item,
            rumps.MenuItem("Open config file", callback=self.open_config),
            rumps.MenuItem("ℹ️  About Morning Agent", callback=self.about),
            None,
        ]

        self._refresh_status()

        # Timer that checks the schedule every 30 seconds.
        self.timer = rumps.Timer(self.tick, 30)
        self.timer.start()

    # ------------------------------------------------------------------ UI

    def _busy(self, on: bool) -> None:
        """Toggle the loading animation. Safe to call from any thread."""
        from PyObjCTools.AppHelper import callAfter
        callAfter(self._apply_busy, bool(on))

    def _apply_busy(self, on: bool) -> None:
        # Must run on the main thread (NSTimer needs the main run loop).
        if self._anim_timer is not None:
            self._anim_timer.stop()
            self._anim_timer = None
        if on and SPIN_FRAMES:
            self.title = None
            self._anim_i = 0
            self._anim_timer = rumps.Timer(self._anim_tick, 0.08)
            self._anim_timer.start()
        elif on:
            self.title = "…"  # fallback if frames are missing
        else:
            self.title = None
            self.icon = ICON_PATH  # restore the crisp static sun

    def _anim_tick(self, _timer) -> None:
        self.icon = SPIN_FRAMES[self._anim_i % len(SPIN_FRAMES)]
        self._anim_i += 1

    def _set_dock_icon(self) -> None:
        """Replace the generic Python icon in the Dock / Cmd-Tab with the sun."""
        try:
            from AppKit import NSApplication, NSImage
            if os.path.exists(APP_ICON_PATH):
                img = NSImage.alloc().initByReferencingFile_(APP_ICON_PATH)
                NSApplication.sharedApplication().setApplicationIconImage_(img)
        except Exception:
            pass

    def _notify(self, title: str, message: str) -> None:
        # Use osascript — it shows reliably even when we're not packaged as an .app
        # (rumps' NSUserNotification is often silently dropped without a bundle id).
        def esc(s: str) -> str:
            return (s or "").replace("\\", "\\\\").replace('"', '\\"')
        script = (f'display notification "{esc(message)}" '
                  f'with title "{esc(title)}" subtitle "Morning Agent"')
        try:
            subprocess.run(["osascript", "-e", script], check=False)
        except Exception:
            pass

    def _refresh_status(self) -> None:
        auto = "ON" if self.cfg.get("autosend") else "OFF"
        mode = self.cfg.get("delivery_mode", "email")
        self.autosend_item.title = f"Auto-deliver: {auto}  ({self.cfg.get('send_time','?')})"
        self.autosend_item.state = 1 if self.cfg.get("autosend") else 0
        state = config.load_state()
        last = state.get("last_sent_date", "—")
        self.status_item.title = f"Auto-deliver {auto} · {mode} · last: {last}"

    # ------------------------------------------------------------- actions

    def send_now(self, _=None) -> None:
        self._deliver(self.cfg.get("delivery_mode", "email"), mark_state=False)

    def preview(self, _=None) -> None:
        if self._sending:
            return
        self._sending = True
        self._busy(True)

        def work() -> None:
            try:
                _subject, html = build_email(self.cfg)
                self._show_on_screen(html, "Morning brief (preview)")
            except Exception as exc:  # noqa: BLE001 — we want to surface any error
                self._notify("Preview error ❌", str(exc))
            finally:
                self._sending = False
                self._busy(False)

        threading.Thread(target=work, daemon=True).start()

    def _show_on_screen(self, html: str, title: str = "Morning brief") -> None:
        """Render the brief in a native app window (WebKit), on the main thread."""
        from PyObjCTools.AppHelper import callAfter
        from . import brief_window
        callAfter(brief_window.show_brief, html, title)

    def _store_today(self, subject: str, html: str) -> None:
        self._today_date = dt.date.today().isoformat()
        self._today_subject = subject
        self._today_html = html

    def show_today(self, _=None) -> None:
        """Open today's brief on screen; build it first if we don't have it yet."""
        today = dt.date.today().isoformat()
        if self._today_html and self._today_date == today:
            self._show_on_screen(self._today_html, "Today's brief")
            return
        if self._sending:
            return
        self._sending = True
        self._busy(True)
        self.cfg = config.load_config()

        def work() -> None:
            try:
                subject, html = build_email(self.cfg)
                self._store_today(subject, html)
                self._show_on_screen(html, "Today's brief")
            except Exception as exc:  # noqa: BLE001
                self._notify("Brief error ❌", str(exc))
            finally:
                self._sending = False
                self._busy(False)

        threading.Thread(target=work, daemon=True).start()

    def today_note(self, _=None) -> None:
        self.show_today()

    def _deliver(self, mode: str, mark_state: bool) -> None:
        """Build the brief and deliver it by email, on screen, or both."""
        if self._sending:
            return
        self._sending = True
        self._busy(True)
        # Reload config (it may have been edited in the file).
        self.cfg = config.load_config()

        def work() -> None:
            try:
                subject, html = build_email(self.cfg)
                self._store_today(subject, html)
                done: list[str] = []
                errors: list[str] = []

                if mode in ("email", "both"):
                    try:
                        send_email(
                            api_key=self.cfg["resend_api_key"],
                            sender=self.cfg["sender"],
                            recipient=self.cfg["recipient"],
                            subject=subject,
                            html=html,
                        )
                        done.append("emailed")
                    except Exception as exc:  # noqa: BLE001
                        errors.append(f"email: {exc}")

                if mode in ("screen", "both"):
                    # Screen delivery = a notification; clicking it opens the window.
                    done.append("notified")

                if done and mark_state:
                    st = config.load_state()
                    st["last_sent_date"] = dt.date.today().isoformat()
                    st["last_result"] = "ok" if not errors else "; ".join(errors)
                    config.save_state(st)

                if errors and not done:
                    self._last_msg = "; ".join(errors)
                    self._notify("Delivery error ❌", "; ".join(errors))
                else:
                    self._last_msg = f"{subject} ({' + '.join(done)})"
                    hint = ("Click to read today's brief"
                            if mode in ("screen", "both") else "Emailed")
                    if errors:
                        hint += " (with issues)"
                    self._notify(subject, hint)
            except Exception as exc:  # noqa: BLE001
                self._last_msg = f"error: {exc}"
                self._notify("Brief error ❌", str(exc))
            finally:
                self._sending = False
                self._busy(False)
                self._refresh_status()

        threading.Thread(target=work, daemon=True).start()

    # ---------------------------------------------------------- settings

    def _save(self, key: str, value) -> None:
        self.cfg = config.set_value(key, value)
        self._refresh_status()

    def open_settings(self, _=None) -> None:
        """Open the single, tabbed Settings window."""
        from .settings_window import open_settings
        open_settings(self)

    def on_config_changed(self) -> None:
        """Called by the Settings window after it saves — reload and refresh."""
        self.cfg = config.load_config()
        self._refresh_status()

    def toggle_autosend(self, _=None) -> None:
        self._save("autosend", not self.cfg.get("autosend"))

    def open_config(self, _=None) -> None:
        config.ensure_config_file()
        subprocess.run(["open", str(config.CONFIG_PATH)], check=False)

    def about(self, _=None) -> None:
        """Show an About window with author and copyright info."""
        from .composer import wrap_html
        inner = f"""<h2>☀︎ Morning Agent</h2>
<p>Version {__version__}</p>
<p>Your morning assistant in the macOS menu bar — a daily briefing built from your
notes and RSS feeds, delivered by email or shown on screen.</p>
<hr>
<p><strong>Author:</strong> Rafał Gawlik<br>
<strong>Website:</strong> <a href="https://rafalgawlik.com">rafalgawlik.com</a><br>
<strong>GitHub:</strong> <a href="https://github.com/rafalgawlik">@rafalgawlik</a>
 · <a href="https://github.com/rafalgawlik/morning-agent">morning-agent</a></p>
<p><em>© 2026 Rafał Gawlik · MIT License</em></p>"""
        self._show_on_screen(wrap_html(inner, f"Morning Agent {__version__}"),
                             "About Morning Agent")

    # ---------------------------------------------------------- schedule

    def tick(self, _timer) -> None:
        self.cfg = config.load_config()
        self._refresh_status()

        if not self.cfg.get("autosend") or self._sending:
            return

        now = dt.datetime.now()
        today = dt.date.today().isoformat()
        state = config.load_state()
        if state.get("last_attempt_date") == today:
            return  # already attempted today (success or not) — never retry-spam

        if now.strftime("%H:%M") >= self.cfg.get("send_time", "07:00"):
            # Mark the attempt immediately so a failure can't retry every 30s.
            state["last_attempt_date"] = today
            config.save_state(state)
            self._deliver(self.cfg.get("delivery_mode", "email"), mark_state=True)


def main() -> None:
    # Lightweight argument handling so the version can be checked without the GUI
    # (useful e.g. for `brew test`).
    import sys

    if len(sys.argv) > 1 and sys.argv[1] in ("-v", "--version"):
        print(f"morning-agent {__version__}")
        return
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print(
            "Morning Agent — menu bar app that emails you a morning briefing.\n"
            "Run with no arguments to show the ☀ icon in the menu bar.\n"
            "Config: ~/.config/morning-agent/config.json"
        )
        return

    _set_app_name()
    _install_reopen_handler()
    MorningAgentApp().run()
