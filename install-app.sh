#!/bin/bash
# Build and install "Morning Agent.app" (via py2app) so it is launchable from
# the Dock, Launchpad, Spotlight and /Applications. Registers a Login Item
# (autostart + single instance) and removes the old launchd agent.
set -uo pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
ICON_PNG="$ROOT/morning_agent/assets/app_icon.png"
APP_NAME="Morning Agent"
BUNDLE_ID="com.morning-agent"
PY="/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
[ -x "$PY" ] || PY="$(command -v python3)"

say() { printf '%s\n' "$1"; }
ok()  { printf '> %s\n' "$1"; }
err() { printf 'x %s\n' "$1" >&2; }

[ -f "$ICON_PNG" ] || { err "Missing icon: $ICON_PNG"; exit 1; }
if [ -w /Applications ]; then DEST="/Applications"; else DEST="$HOME/Applications"; mkdir -p "$DEST"; fi
APP="$DEST/$APP_NAME.app"

launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"
pkill -9 -if 'morning_agent' 2>/dev/null || true
pkill -9 -if "$APP_NAME.app" 2>/dev/null || true

if [ ! -d "$ROOT/.venv" ]; then
    "$PY" -m venv "$ROOT/.venv"
    "$ROOT/.venv/bin/pip" install -q --upgrade pip
    "$ROOT/.venv/bin/pip" install -q -r "$ROOT/requirements.txt"
fi
"$ROOT/.venv/bin/pip" show py2app >/dev/null 2>&1 || "$ROOT/.venv/bin/pip" install -q py2app
ok "Environment ready"

TMP=$(mktemp -d); ISET="$TMP/i.iconset"; mkdir -p "$ISET"
for s in 16 32 128 256 512; do
    sips -z "$s" "$s"             "$ICON_PNG" --out "$ISET/icon_${s}x${s}.png"    >/dev/null 2>&1
    sips -z "$((s*2))" "$((s*2))" "$ICON_PNG" --out "$ISET/icon_${s}x${s}@2x.png" >/dev/null 2>&1
done
iconutil -c icns "$ISET" -o "$ROOT/morning_agent/assets/app_icon.icns" 2>/dev/null
rm -rf "$TMP"

( cd "$ROOT" && rm -rf build dist && "$ROOT/.venv/bin/python" setup_app.py py2app -A ) >/dev/null 2>&1 \
    || { err "py2app build failed - run: .venv/bin/python setup_app.py py2app -A"; exit 1; }
[ -d "$ROOT/dist/$APP_NAME.app" ] || { err "Build produced no app"; exit 1; }
ok "Built $APP_NAME.app"

rm -rf "$APP"
cp -R "$ROOT/dist/$APP_NAME.app" "$DEST/"
LSREG="/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
"$LSREG" -u "$ROOT/dist/$APP_NAME.app" 2>/dev/null || true
"$LSREG" -f "$APP" 2>/dev/null || true
rm -rf "$ROOT/build" "$ROOT/dist"
ok "Installed $APP"

osascript -e "tell application \"System Events\" to delete (every login item whose name is \"$APP_NAME\")" 2>/dev/null || true
if osascript -e "tell application \"System Events\" to make login item at end with properties {path:\"$APP\", hidden:false}" >/dev/null 2>&1; then
    ok "Added Login Item (starts on login)"
else
    say "Could not add Login Item automatically - add $APP in System Settings > General > Login Items."
fi

open "$APP" && ok "Launched $APP_NAME"
say ""
ok "Done. Launch Morning Agent from the Dock, Launchpad, Spotlight or $DEST."
say "- Uninstall: ./uninstall-app.sh"
