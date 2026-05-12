#!/bin/bash

# MpvTube Idempotent Installer (System Python Version)
# This script installs requirements to the user space and creates desktop entries.

set -e

echo "--- MpvTube Installation / Update ---"

# Get absolute path of the project directory
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 1. Install/Update requirements using system pip (user space)
echo "Checking dependencies (user space)..."
# We use --break-system-packages for newer distros that enforce PEP 668, 
# or just regular pip install --user.
pip3 install --user -r "$INSTALL_DIR/requirements.txt" || \
pip3 install --user --break-system-packages -r "$INSTALL_DIR/requirements.txt"

# 2. Create/Update wrapper executable
echo "Creating wrapper script..."
WRAPPER="$INSTALL_DIR/mpvtube"
cat <<EOF > "$WRAPPER"
#!/bin/bash
cd "$INSTALL_DIR"
exec python3 main.py "\$@"
EOF
chmod +x "$WRAPPER"

# 3. Create/Update Desktop Entry
echo "Updating desktop entry..."
DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"
DESKTOP_FILE="$DESKTOP_DIR/mpvtube.desktop"

cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Name=MpvTube
Comment=YouTube player for mpv (Modern TUI)
Exec=$WRAPPER
Icon=youtube
Terminal=true
Type=Application
Categories=AudioVideo;Video;Player;
Keywords=youtube;mpv;tui;video;
EOF

echo "--------------------------------------------------"
echo "Done! MpvTube is ready."
echo "You can run it from your menu or via: $WRAPPER"
echo "--------------------------------------------------"
