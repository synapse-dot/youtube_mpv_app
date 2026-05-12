#!/bin/bash

# MpvTube Uninstaller
set -e

echo "--- MpvTube Uninstall ---"

INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WRAPPER="$INSTALL_DIR/mpvtube"
DESKTOP_FILE="$HOME/.local/share/applications/mpvtube.desktop"

if [ -f "$DESKTOP_FILE" ]; then
  rm -f "$DESKTOP_FILE"
  echo "Removed desktop entry: $DESKTOP_FILE"
else
  echo "Desktop entry not found: $DESKTOP_FILE"
fi

if [ -f "$WRAPPER" ]; then
  rm -f "$WRAPPER"
  echo "Removed wrapper: $WRAPPER"
else
  echo "Wrapper not found: $WRAPPER"
fi

echo "App files remain at: $INSTALL_DIR"
echo "Optional cleanup:"
echo "  rm -rf ~/.config/mpvTube"
echo "  rm -rf ~/.cache/mpvTube"
echo "  pip3 uninstall yt-dlp textual textual-dev PySide6"

echo "Done."
