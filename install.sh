#!/bin/bash

# MpvTube Installer
# This script creates a desktop entry for MpvTube

set -e

echo "Installing MpvTube..."

# Get absolute path of the project directory
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_BIN="$INSTALL_DIR/.venv/bin/python3"

# Check for virtual environment
if [ ! -f "$PYTHON_BIN" ]; then
    echo "Warning: .venv not found. Using system python3."
    PYTHON_BIN="python3"
else
    echo "Found virtual environment: $PYTHON_BIN"
fi

# Create a wrapper executable
WRAPPER="$INSTALL_DIR/mpvtube"
cat <<EOF > "$WRAPPER"
#!/bin/bash
cd "$INSTALL_DIR"
exec "$PYTHON_BIN" main.py "\$@"
EOF
chmod +x "$WRAPPER"

# Define Desktop Entry path
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
DESKTOP_FILE="$DESKTOP_DIR/mpvtube.desktop"

# Create Desktop Entry
cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=MpvTube
Comment=YouTube player for mpv (TUI)
Exec=$WRAPPER
Icon=youtube
Terminal=true
Type=Application
Categories=AudioVideo;Video;Player;
Keywords=youtube;mpv;tui;video;
EOF

echo "--------------------------------------------------"
echo "Success! MpvTube has been installed."
echo "Desktop Entry: $DESKTOP_FILE"
echo "Wrapper Script: $WRAPPER"
echo ""
echo "You can now launch MpvTube from your application menu"
echo "or by running: $WRAPPER"
echo "--------------------------------------------------"
