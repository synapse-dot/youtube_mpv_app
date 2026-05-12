#!/bin/bash

# MpvTube Idempotent Installer
# This script sets up the venv, installs requirements, and creates desktop entries.

set -e

echo "--- MpvTube Installation / Update ---"

# Get absolute path of the project directory
INSTALL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_BIN="$INSTALL_DIR/.venv/bin/python3"

# 1. Ensure Virtual Environment exists
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$INSTALL_DIR/.venv"
fi

# 2. Install/Update requirements
echo "Checking dependencies..."
"$INSTALL_DIR/.venv/bin/pip" install --upgrade pip
"$INSTALL_DIR/.venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"

# 3. Create/Update wrapper executable
echo "Creating wrapper script..."
WRAPPER="$INSTALL_DIR/mpvtube"
cat <<EOF > "$WRAPPER"
#!/bin/bash
cd "$INSTALL_DIR"
exec "$INSTALL_DIR/.venv/bin/python3" main.py "\$@"
EOF
chmod +x "$WRAPPER"

# 4. Create/Update Desktop Entry
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
