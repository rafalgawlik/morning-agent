"""A native app window that renders the brief HTML with WKWebView (no browser)."""

from __future__ import annotations

import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSColor,
    NSMakeRect,
    NSWorkspace,
    NSViewHeightSizable,
    NSViewWidthSizable,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskMiniaturizable,
    NSWindowStyleMaskResizable,
    NSWindowStyleMaskTitled,
    NSWindow,
)
from Foundation import NSObject
from WebKit import WKWebView, WKWebViewConfiguration

from .composer import DARK_BG, LIGHT_BG

# Keep strong references so windows/delegates aren't garbage-collected on screen.
_open_windows: list = []
_delegates: list = []


class _LinkDelegate(NSObject):
    """Opens clicked links in the default browser instead of inside the window."""

    def webView_decidePolicyForNavigationAction_decisionHandler_(
        self, _webview, action, handler
    ):
        try:
            url = action.request().URL()
            scheme = (url.scheme() or "").lower() if url else ""
            # 0 == WKNavigationTypeLinkActivated (a real click)
            if action.navigationType() == 0 and scheme in ("http", "https"):
                NSWorkspace.sharedWorkspace().openURL_(url)
                handler(0)   # WKNavigationActionPolicyCancel — don't load in-window
                return
        except Exception:
            pass
        handler(1)           # WKNavigationActionPolicyAllow (initial content load)


def _hex_color(hexstr: str):
    h = hexstr.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, 1.0)


def _is_dark(win) -> bool:
    name = win.effectiveAppearance().bestMatchFromAppearancesWithNames_(
        ["NSAppearanceNameAqua", "NSAppearanceNameDarkAqua"])
    return bool(name) and "Dark" in name


def show_brief(html: str, title: str = "Morning brief") -> None:
    """Open a native window showing the rendered brief. Must run on the main thread."""
    w, h = 700, 820
    style = (
        NSWindowStyleMaskTitled
        | NSWindowStyleMaskClosable
        | NSWindowStyleMaskResizable
        | NSWindowStyleMaskMiniaturizable
    )
    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, w, h), style, NSBackingStoreBuffered, False
    )
    win.setTitle_(title)
    win.setReleasedWhenClosed_(False)
    win.setMinSize_((420, 400))

    # One uniform color: make the title bar blend into the page background.
    win.setTitlebarAppearsTransparent_(True)
    win.setBackgroundColor_(_hex_color(DARK_BG if _is_dark(win) else LIGHT_BG))
    try:
        win.setTitlebarSeparatorStyle_(1)  # NSTitlebarSeparatorStyleNone (macOS 11+)
    except Exception:
        pass

    config = WKWebViewConfiguration.alloc().init()
    web = WKWebView.alloc().initWithFrame_configuration_(NSMakeRect(0, 0, w, h), config)
    web.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
    delegate = _LinkDelegate.alloc().init()
    web.setNavigationDelegate_(delegate)
    _delegates.append(delegate)
    win.contentView().addSubview_(web)
    web.loadHTMLString_baseURL_(html, None)

    win.center()
    win.makeKeyAndOrderFront_(None)
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)

    # Track window; drop ones the user has closed (keep visible & minimized).
    _open_windows.append(win)
    _open_windows[:] = [x for x in _open_windows if x.isVisible() or x.isMiniaturized()]
