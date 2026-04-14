#!/bin/bash
#
# Runtime Fence - Mac/Linux Installer
# One-click installation for macOS and Linux
#

set -e

echo ""
echo "========================================"
echo "  RUNTIME FENCE - INSTALLER"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python
echo -e "${YELLOW}[1/5] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python 3 not found.${NC}"
    echo "Install Python 3.10+ from: https://python.org/downloads"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}Found: $PYTHON_VERSION${NC}"

# Install dependencies
echo ""
echo -e "${YELLOW}[2/5] Installing dependencies...${NC}"
pip3 install --quiet requests psutil pystray pillow

# Determine install directory
INSTALL_DIR="$HOME/.runtime-fence"
echo ""
echo -e "${YELLOW}[3/5] Installing to $INSTALL_DIR...${NC}"
mkdir -p "$INSTALL_DIR"

# Copy files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/runtime_fence.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/fence_proxy.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/agent_scanner.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/fence_tray.py" "$INSTALL_DIR/"

# Create launcher script
echo ""
echo -e "${YELLOW}[4/5] Creating launcher...${NC}"
cat > "$INSTALL_DIR/fence" << 'EOF'
#!/bin/bash
cd "$HOME/.runtime-fence"
python3 fence_tray.py "$@"
EOF
chmod +x "$INSTALL_DIR/fence"

# Add to PATH (create symlink)
if [ -d "/usr/local/bin" ]; then
    sudo ln -sf "$INSTALL_DIR/fence" /usr/local/bin/fence 2>/dev/null || true
fi

# Create desktop entry for Linux
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo -e "${YELLOW}[5/5] Creating desktop entry...${NC}"
    mkdir -p "$HOME/.local/share/applications"
    cat > "$HOME/.local/share/applications/runtime-fence.desktop" << EOF
[Desktop Entry]
Name=Runtime Fence
Comment=AI Agent Safety Control
Exec=$INSTALL_DIR/fence
Icon=security-high
Terminal=false
Type=Application
Categories=Utility;Security;
EOF
fi

# Create launchd plist for macOS (auto-start)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo ""
    echo -e "${YELLOW}[5/5] Setting up auto-start...${NC}"
    mkdir -p "$HOME/Library/LaunchAgents"
    cat > "$HOME/Library/LaunchAgents/com.runtimefence.agent.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.runtimefence.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>$INSTALL_DIR/fence_tray.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
EOF
    launchctl load "$HOME/Library/LaunchAgents/com.runtimefence.agent.plist" 2>/dev/null || true
fi

echo ""
echo "========================================"
echo -e "${GREEN}  INSTALLATION COMPLETE${NC}"
echo "========================================"
echo ""
echo "To start Runtime Fence:"
echo "  fence"
echo ""
echo "Or run directly:"
echo "  python3 $INSTALL_DIR/fence_tray.py"
echo ""
echo "The fence will appear in your system tray."
echo ""
