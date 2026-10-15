"""Native notifications via the UserNotifications framework.

Shows the app's own icon (from the .app bundle) and prompts for permission the
first time — unlike the deprecated NSUserNotification path, which modern macOS
silently drops. Falls back to osascript if UserNotifications is unavailable.
"""
from __future__ import annotations

import uuid


def setup() -> None:
    """Ask for notification permission once (prompts the user the first time)."""
    try:
        from UserNotifications import (
            UNUserNotificationCenter,
            UNAuthorizationOptionAlert,
            UNAuthorizationOptionSound,
        )
        center = UNUserNotificationCenter.currentNotificationCenter()
        center.requestAuthorizationWithOptions_completionHandler_(
            UNAuthorizationOptionAlert | UNAuthorizationOptionSound,
            lambda granted, error: None)
    except Exception:
        pass


def notify(title: str, body: str = "") -> None:
    """Post a notification (title shown under the app name; body optional)."""
    try:
        from UserNotifications import (
            UNUserNotificationCenter,
            UNMutableNotificationContent,
            UNNotificationRequest,
        )
        center = UNUserNotificationCenter.currentNotificationCenter()
        content = UNMutableNotificationContent.alloc().init()
        content.setTitle_(title or "")
        if body:
            content.setBody_(body)
        req = UNNotificationRequest.requestWithIdentifier_content_trigger_(
            str(uuid.uuid4()), content, None)
        center.addNotificationRequest_withCompletionHandler_(req, None)
        return
    except Exception:
        pass
    try:
        import subprocess
        t = (title or "").replace("\\", "\\\\").replace('"', '\\"')
        b = (body or "").replace("\\", "\\\\").replace('"', '\\"')
        subprocess.run(["osascript", "-e",
                        f'display notification "{b}" with title "{t}"'], check=False)
    except Exception:
        pass
