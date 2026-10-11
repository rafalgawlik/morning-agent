#!/bin/bash
# Remove Morning Agent.app, its Login Item and the old launchd agent.
set -uo pipefail

APP_NAME="Morning Agent"
BUNDLE_ID="com.morning-agent"

osascript -e "tell application \"$APP_NAME\" to quit" 2>/dev/null || true
pkill -9 -if 'morning_agent' 2>/dev/null || true
osascript -e "tell application \"System Events\" to delete (every login item whose name is \"$APP_NAME\")" 2>/dev/null || true
launchctl bootout "gui/$(id -u)/$BUNDLE_ID" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/$BUNDLE_ID.plist"
rm -rf "/Applications/$APP_NAME.app" "$HOME/Applications/$APP_NAME.app"

printf '> Morning Agent uninstalled (app, Login Item, autostart). The repo stays intact.\n'
