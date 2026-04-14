#!/bin/bash
#
# Runtime Fence - Mac/Linux Uninstaller
#

echo ""
echo "========================================"
echo "  RUNTIME FENCE - UNINSTALLER"
echo "========================================"
echo ""

INSTALL_DIR="$HOME/.runtime-fence"

# Remove launchd plist (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Stopping auto-start service..."
    launchctl unload "$HOME/Library/LaunchAgents/com.runtimefence.agent.plist" 2>/dev/null || true
    rm -f "$HOME/Library/LaunchAgents/com.runtimefence.agent.plist"
fi

# Remove desktop entry (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Removing desktop entry..."
    rm -f "$HOME/.local/share/applications/runtime-fence.desktop"
fi

# Remove symlink
echo "Removing from PATH..."
sudo rm -f /usr/local/bin/fence 2>/dev/null || true

# Remove install directory
echo "Removing installation..."
rm -rf "$INSTALL_DIR"

echo ""
echo "========================================"
echo "  UNINSTALL COMPLETE"
echo "========================================"
echo ""
echo "Runtime Fence has been removed from your system."
echo ""
