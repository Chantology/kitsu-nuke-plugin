#!/bin/bash
# Installs the Kitsu Nuke Plugin into Nuke's user plugin folder on macOS.
#
# Usage: ./install_mac.command [custom .nuke folder]
#   Double-click to run with no arguments, installing to the standard
#   location (~/.nuke), which every Nuke version scans at startup. If you
#   keep your Nuke setup elsewhere (a folder on NUKE_PATH), pass that
#   folder as an argument to this script instead.
#
# Two things are installed: the kitsu_nuke_plugin folder itself, and a
# two-line entry in that folder's init.py telling Nuke to load it. Nuke
# only auto-runs init.py/menu.py for folders that are ON its plugin path,
# and it does not look inside sub-folders on its own, so the
# pluginAddPath line below is what actually activates the plugin.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE="$SCRIPT_DIR/kitsu_nuke_plugin"

if [ "${1:-}" != "" ]; then
    TARGET="$1"
else
    TARGET="$HOME/.nuke"
fi

echo "Installing Kitsu Nuke Plugin"
echo "  From: $SOURCE"
echo "  To:   $TARGET/kitsu_nuke_plugin"
echo

if [ ! -f "$SOURCE/menu.py" ]; then
    echo "ERROR: $SOURCE not found or incomplete."
    echo "Run this script from the repository root, or check your checkout."
    read -r -p "Press Enter to close this window..." _
    exit 1
fi

mkdir -p "$TARGET"

# Remove any previous install of this plugin's own folder first, for a
# clean, idempotent install that never leaves stale files from an older
# version behind.
rm -rf "$TARGET/kitsu_nuke_plugin"

cp -R "$SOURCE" "$TARGET/kitsu_nuke_plugin"
find "$TARGET/kitsu_nuke_plugin" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true

INIT="$TARGET/init.py"
if [ -f "$INIT" ] && grep -q "kitsu-nuke-plugin" "$INIT"; then
    echo "  $INIT already registers the plugin - left as is."
else
    # Appended, never rewritten: this init.py is the user's own file and
    # may well already have other studio setup in it.
    {
        echo
        echo "# kitsu-nuke-plugin: added by its installer"
        echo "import nuke"
        echo 'nuke.pluginAddPath("./kitsu_nuke_plugin")'
    } >> "$INIT"
    echo "  Registered the plugin in $INIT"
fi

echo
echo "Done. Restart Nuke - a \"Kitsu\" menu appears in the menu bar,"
echo "with \"Open Kitsu Panel\" and \"Publish Capture\". The panel is also"
echo "in the pane menu of any pane, listed as \"Kitsu\"."
read -r -p "Press Enter to close this window..." _
