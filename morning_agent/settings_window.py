"""A single tabbed Settings window, built with PyObjC (AppKit).

rumps only offers one-field dialogs, so we build a native NSWindow with an
NSTabView here: Email · Model · Content · Schedule · Prompt.
"""

from __future__ import annotations

import datetime as dt

import objc
from AppKit import (
    NSApplication,
    NSBackingStoreBuffered,
    NSBezelBorder,
    NSButton,
    NSEventModifierFlagCommand,
    NSEventTypeKeyDown,
    NSFont,
    NSMakeRect,
    NSMenu,
    NSMenuItem,
    NSOpenPanel,
    NSPopUpButton,
    NSScrollView,
    NSSecureTextField,
    NSSwitchButton,
    NSTabView,
    NSTabViewItem,
    NSTextField,
    NSTextView,
    NSView,
    NSWindow,
    NSWindowStyleMaskClosable,
    NSWindowStyleMaskTitled,
)
from Foundation import NSObject

# Standard editing shortcuts → responder-chain selectors.
_EDIT_SELECTORS = {"x": "cut:", "c": "copy:", "v": "paste:", "a": "selectAll:", "z": "undo:"}


class _EditWindow(NSWindow):
    """Window that handles ⌘X/C/V/A/Z itself, so paste works without a menu."""

    def performKeyEquivalent_(self, event):
        if event.type() == NSEventTypeKeyDown and (
            event.modifierFlags() & NSEventModifierFlagCommand
        ):
            key = (event.charactersIgnoringModifiers() or "").lower()
            sel = _EDIT_SELECTORS.get(key)
            if sel and NSApplication.sharedApplication().sendAction_to_from_(sel, None, self):
                return True
        return objc.super(_EditWindow, self).performKeyEquivalent_(event)

from . import config

# Delivery popup order — index maps to the stored value.
_DELIVERY_ORDER = ["email", "screen", "both"]

# Tab content area (points). Origin is bottom-left in Cocoa.
_W, _H = 540, 340
_LABEL_W = 150
_FIELD_X = 175
_FIELD_W = 345


def _label(text: str, x: float, y: float, w: float = _LABEL_W) -> NSTextField:
    lbl = NSTextField.alloc().initWithFrame_(NSMakeRect(x, y, w, 18))
    lbl.setStringValue_(text)
    lbl.setBezeled_(False)
    lbl.setDrawsBackground_(False)
    lbl.setEditable_(False)
    lbl.setSelectable_(False)
    lbl.setFont_(NSFont.systemFontOfSize_(12))
    return lbl


def _field(value: str, x: float, y: float, w: float = _FIELD_W, secure: bool = False):
    cls = NSSecureTextField if secure else NSTextField
    f = cls.alloc().initWithFrame_(NSMakeRect(x, y, w, 24))
    f.setStringValue_(value or "")
    f.setFont_(NSFont.systemFontOfSize_(12))
    return f


def _textview(value: str, x: float, y: float, w: float, h: float):
    scroll = NSScrollView.alloc().initWithFrame_(NSMakeRect(x, y, w, h))
    scroll.setHasVerticalScroller_(True)
    scroll.setBorderType_(NSBezelBorder)
    tv = NSTextView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
    tv.setString_(value or "")
    tv.setFont_(NSFont.systemFontOfSize_(12))
    tv.setRichText_(False)
    tv.setAutomaticQuoteSubstitutionEnabled_(False)
    scroll.setDocumentView_(tv)
    return scroll, tv


def _tab(title: str) -> tuple[NSTabViewItem, NSView]:
    item = NSTabViewItem.alloc().initWithIdentifier_(title)
    item.setLabel_(title)
    view = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, _W, _H))
    item.setView_(view)
    return item, view


class _SettingsController(NSObject):
    def initWithApp_(self, app):
        self = objc.super(_SettingsController, self).init()
        if self is None:
            return None
        self.app = app
        self.fields = {}      # key -> NSTextField
        self.textviews = {}   # key -> NSTextView
        self.autosend_btn = None
        self.window = None
        return self

    # -- actions ---------------------------------------------------------

    def browse_(self, _sender):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseDirectories_(True)
        panel.setCanChooseFiles_(False)
        panel.setAllowsMultipleSelection_(False)
        panel.setPrompt_("Choose")
        if panel.runModal() == 1 and panel.URLs():
            self.fields["notes_dir"].setStringValue_(panel.URLs()[0].path())

    def addFiles_(self, _sender):
        panel = NSOpenPanel.openPanel()
        panel.setCanChooseDirectories_(False)
        panel.setCanChooseFiles_(True)
        panel.setAllowsMultipleSelection_(True)
        panel.setPrompt_("Add")
        if panel.runModal() != 1:
            return
        tv = self.textviews["note_files"]
        existing = [ln.strip() for ln in tv.string().splitlines() if ln.strip()]
        for url in panel.URLs():
            path = url.path()
            if path not in existing:
                existing.append(path)
        tv.setString_("\n".join(existing))

    def cancel_(self, _sender):
        if self.window is not None:
            self.window.close()

    def save_(self, _sender):
        cfg = config.load_config()

        for key in ("resend_api_key", "sender", "recipient", "subject_prefix",
                    "openrouter_api_key", "model", "notes_dir"):
            cfg[key] = self.fields[key].stringValue().strip()

        # Send time is validated; if wrong, keep the window open.
        send_time = self.fields["send_time"].stringValue().strip()
        try:
            dt.datetime.strptime(send_time, "%H:%M")
        except ValueError:
            _show_alert("Invalid send time. Use HH:MM, e.g. 07:00.")
            return
        cfg["send_time"] = send_time

        cfg["note_files"] = [ln.strip() for ln in self.textviews["note_files"].string().splitlines()
                             if ln.strip()]
        cfg["feeds"] = [ln.strip() for ln in self.textviews["feeds"].string().splitlines()
                        if ln.strip()]
        try:
            cfg["feed_max_age_days"] = max(0, int(self.fields["feed_max_age_days"].stringValue().strip() or "0"))
        except ValueError:
            cfg["feed_max_age_days"] = 0
        cfg["prompt"] = self.textviews["prompt"].string().strip() or config.DEFAULT_PROMPT
        cfg["autosend"] = bool(self.autosend_btn.state())

        idx = self.delivery_popup.indexOfSelectedItem()
        cfg["delivery_mode"] = _DELIVERY_ORDER[idx] if 0 <= idx < len(_DELIVERY_ORDER) else "email"

        config.save_config(cfg)
        self.app.on_config_changed()
        if self.window is not None:
            self.window.close()


def _show_alert(message: str) -> None:
    import rumps
    rumps.alert("Morning Agent — Settings", message)


def _ensure_edit_menu() -> None:
    """Install a minimal main menu with an Edit menu so ⌘C/⌘V/⌘X/⌘A work.

    A status-bar app has no main menu by default, so the standard copy/paste key
    equivalents have nothing to trigger — text fields then ignore ⌘V.
    """
    from AppKit import NSApplication
    app = NSApplication.sharedApplication()
    if app.mainMenu() is not None:
        return
    main = NSMenu.alloc().init()

    app_item = NSMenuItem.alloc().init()
    main.addItem_(app_item)
    app_item.setSubmenu_(NSMenu.alloc().init())

    edit_item = NSMenuItem.alloc().init()
    main.addItem_(edit_item)
    edit_menu = NSMenu.alloc().initWithTitle_("Edit")
    edit_item.setSubmenu_(edit_menu)

    def add(title, action, key):
        edit_menu.addItem_(
            NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, action, key))

    add("Undo", "undo:", "z")
    add("Redo", "redo:", "Z")
    edit_menu.addItem_(NSMenuItem.separatorItem())
    add("Cut", "cut:", "x")
    add("Copy", "copy:", "c")
    add("Paste", "paste:", "v")
    add("Select All", "selectAll:", "a")

    app.setMainMenu_(main)


def open_settings(app) -> None:
    """Build (or re-focus) and show the tabbed Settings window for `app`."""
    _ensure_edit_menu()  # so ⌘V works in the text fields
    # Reuse an existing window if still open.
    existing = getattr(app, "_settings_ctrl", None)
    if existing is not None and existing.window is not None and existing.window.isVisible():
        existing.window.makeKeyAndOrderFront_(None)
        _activate()
        return

    cfg = config.load_config()
    ctrl = _SettingsController.alloc().initWithApp_(app)

    win = _EditWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        NSMakeRect(0, 0, 570, 470),
        NSWindowStyleMaskTitled | NSWindowStyleMaskClosable,
        NSBackingStoreBuffered,
        False,
    )
    win.setTitle_("Morning Agent — Settings")
    win.setReleasedWhenClosed_(False)
    content = win.contentView()

    tabs = NSTabView.alloc().initWithFrame_(NSMakeRect(15, 60, 540, 395))
    content.addSubview_(tabs)

    # --- Email tab ---
    email_item, email = _tab("Email")
    _add_row(ctrl, email, "Resend API key", "resend_api_key", cfg, 300, secure=True)
    _add_row(ctrl, email, "Sender address", "sender", cfg, 260)
    _add_row(ctrl, email, "Recipient address", "recipient", cfg, 220)
    _add_row(ctrl, email, "Email subject prefix", "subject_prefix", cfg, 180)
    tabs.addTabViewItem_(email_item)

    # --- Model tab ---
    model_item, model = _tab("Model")
    _add_row(ctrl, model, "OpenRouter API key", "openrouter_api_key", cfg, 300, secure=True)
    _add_row(ctrl, model, "Model (OpenRouter slug)", "model", cfg, 260)
    model.addSubview_(_label("e.g. anthropic/claude-3.5-sonnet, openai/gpt-4o-mini",
                             _FIELD_X, 236, _FIELD_W))
    tabs.addTabViewItem_(model_item)

    # --- Notes tab ---
    notes_item, nview = _tab("Notes")
    nview.addSubview_(_label("Note files — the exact files fed into the prompt", 20, 305, _W - 40))
    add_btn = NSButton.alloc().initWithFrame_(NSMakeRect(_W - 130, 268, 110, 28))
    add_btn.setTitle_("Add files…")
    add_btn.setBezelStyle_(1)
    add_btn.setTarget_(ctrl)
    add_btn.setAction_(objc.selector(ctrl.addFiles_, signature=b"v@:@"))
    nview.addSubview_(add_btn)
    nview.addSubview_(_label("Selected files (one path per line)", 20, 272, 320))
    files_scroll, files_tv = _textview("\n".join(cfg.get("note_files", []) or []),
                                       20, 120, _W - 40, 145)
    ctrl.textviews["note_files"] = files_tv
    nview.addSubview_(files_scroll)

    nview.addSubview_(_label("…or a whole folder (optional)", 20, 88, 250))
    nf = _field(cfg.get("notes_dir", ""), 20, 58, _W - 150)
    ctrl.fields["notes_dir"] = nf
    nview.addSubview_(nf)
    browse = NSButton.alloc().initWithFrame_(NSMakeRect(_W - 120, 56, 100, 28))
    browse.setTitle_("Browse…")
    browse.setBezelStyle_(1)
    browse.setTarget_(ctrl)
    browse.setAction_(objc.selector(ctrl.browse_, signature=b"v@:@"))
    nview.addSubview_(browse)
    tabs.addTabViewItem_(notes_item)

    # --- Feeds tab ---
    feeds_item, fview = _tab("Feeds")
    fview.addSubview_(_label("RSS/Atom feeds (one URL per line)", 20, 305, 320))
    feeds_scroll, feeds_tv = _textview("\n".join(cfg.get("feeds", []) or []),
                                       20, 90, _W - 40, 205)
    ctrl.textviews["feeds"] = feeds_tv
    fview.addSubview_(feeds_scroll)
    fview.addSubview_(_label("Only items from the last (days)", 20, 57, 220))
    age = _field(str(cfg.get("feed_max_age_days", 3)), 250, 55, 60)
    ctrl.fields["feed_max_age_days"] = age
    fview.addSubview_(age)
    fview.addSubview_(_label("(0 = no limit)", 325, 57, 140))
    tabs.addTabViewItem_(feeds_item)

    # --- Schedule tab ---
    sched_item, sched = _tab("Schedule")

    sched.addSubview_(_label("Deliver as", 20, 302))
    delivery = NSPopUpButton.alloc().initWithFrame_pullsDown_(
        NSMakeRect(_FIELD_X, 298, 260, 26), False)
    delivery.addItemsWithTitles_(["Email", "Screen (window)", "Both"])
    delivery.selectItemAtIndex_(_DELIVERY_ORDER.index(cfg.get("delivery_mode", "email"))
                                if cfg.get("delivery_mode", "email") in _DELIVERY_ORDER else 0)
    ctrl.delivery_popup = delivery
    sched.addSubview_(delivery)

    _add_row(ctrl, sched, "Send time (HH:MM)", "send_time", cfg, 258)

    autosend = NSButton.alloc().initWithFrame_(NSMakeRect(_FIELD_X, 216, 320, 24))
    autosend.setButtonType_(NSSwitchButton)
    autosend.setTitle_("Deliver automatically at the time above")
    autosend.setState_(1 if cfg.get("autosend") else 0)
    ctrl.autosend_btn = autosend
    sched.addSubview_(_label("Auto-deliver", 20, 218))
    sched.addSubview_(autosend)
    tabs.addTabViewItem_(sched_item)

    # --- Prompt tab ---
    prompt_item, pview = _tab("Prompt")
    pview.addSubview_(_label("Morning instruction sent to the model (empty = default)",
                             20, 305, _W - 40))
    prompt_scroll, prompt_tv = _textview(cfg.get("prompt", ""), 20, 20, _W - 40, 275)
    ctrl.textviews["prompt"] = prompt_tv
    pview.addSubview_(prompt_scroll)
    tabs.addTabViewItem_(prompt_item)

    # --- Save / Cancel buttons ---
    save = NSButton.alloc().initWithFrame_(NSMakeRect(455, 15, 100, 32))
    save.setTitle_("Save")
    save.setBezelStyle_(1)
    save.setKeyEquivalent_("\r")
    save.setTarget_(ctrl)
    save.setAction_(objc.selector(ctrl.save_, signature=b"v@:@"))
    content.addSubview_(save)

    cancel = NSButton.alloc().initWithFrame_(NSMakeRect(350, 15, 100, 32))
    cancel.setTitle_("Cancel")
    cancel.setBezelStyle_(1)
    cancel.setKeyEquivalent_("\x1b")
    cancel.setTarget_(ctrl)
    cancel.setAction_(objc.selector(ctrl.cancel_, signature=b"v@:@"))
    content.addSubview_(cancel)

    ctrl.window = win
    app._settings_ctrl = ctrl  # keep a strong reference so nothing is GC'd

    win.center()
    win.makeKeyAndOrderFront_(None)
    _activate()


def _add_row(ctrl, view, label_text, key, cfg, y, secure=False):
    view.addSubview_(_label(label_text, 20, y + 2))
    f = _field(cfg.get(key, ""), _FIELD_X, y, secure=secure)
    ctrl.fields[key] = f
    view.addSubview_(f)


def _activate():
    from AppKit import NSApplication
    NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
