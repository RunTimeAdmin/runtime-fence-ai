"""
Runtime Fence - System Tray Application
One-click control for non-technical users.
"""

import sys
import threading
import webbrowser
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

# Import our modules
from fence_proxy import FenceProxy, run_proxy
from agent_scanner import AgentScanner


class FenceTrayApp:
    """System tray application for Runtime Fence."""
    
    def __init__(self):
        self.fence = FenceProxy()
        self.scanner = AgentScanner()
        self.proxy_thread = None
        self.scanner_thread = None
        self.running = False
        self.icon = None
        
    def create_icon_image(self, color="green"):
        """Create a simple colored icon."""
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Shield shape
        colors = {
            "green": (76, 175, 80),    # Protected
            "red": (244, 67, 54),      # Kill switch active
            "yellow": (255, 193, 7),   # Warning
            "gray": (158, 158, 158)    # Disabled
        }
        fill = colors.get(color, colors["gray"])
        
        # Draw shield
        draw.polygon([
            (32, 4),   # Top
            (60, 16),  # Top right
            (56, 48),  # Bottom right
            (32, 60),  # Bottom
            (8, 48),   # Bottom left
            (4, 16)    # Top left
        ], fill=fill)
        
        # Draw "F" for Fence
        draw.text((22, 18), "F", fill="white")
        
        return image
    
    def start_protection(self, icon=None, item=None):
        """Start the fence proxy and scanner."""
        if self.running:
            return
            
        self.running = True
        
        # Start proxy in background
        self.proxy_thread = threading.Thread(target=run_proxy, daemon=True)
        self.proxy_thread.start()
        
        # Start scanner in background
        self.scanner_thread = threading.Thread(
            target=self.scanner.start_monitoring,
            daemon=True
        )
        self.scanner_thread.start()
        
        self.update_icon("green")
        self.show_notification("Protection Active", "Runtime Fence is now monitoring all AI agents.")
    
    def stop_protection(self, icon=None, item=None):
        """Stop protection (not recommended)."""
        self.running = False
        self.scanner.stop_monitoring()
        self.update_icon("gray")
        self.show_notification("Protection Disabled", "Warning: AI agents are not being monitored.")
    
    def activate_kill_switch(self, icon=None, item=None):
        """Emergency kill switch."""
        self.fence.activate_kill_switch("Manual activation from tray")
        self.update_icon("red")
        self.show_notification("KILL SWITCH ACTIVATED", "All AI agent traffic is now BLOCKED.")
    
    def deactivate_kill_switch(self, icon=None, item=None):
        """Resume normal operation."""
        self.fence.deactivate_kill_switch()
        self.update_icon("green")
        self.show_notification("Kill Switch Deactivated", "Normal monitoring resumed.")
    
    def show_dashboard(self, icon=None, item=None):
        """Open web dashboard."""
        webbrowser.open("http://localhost:3000")
    
    def show_status(self, icon=None, item=None):
        """Show current status."""
        summary = self.scanner.get_summary()
        status = self.fence.get_status()
        
        msg = f"""
Runtime Fence Status
--------------------
Protection: {'Active' if self.running else 'Disabled'}
Kill Switch: {'ACTIVE' if status['kill_switch'] else 'Off'}

Detected Agents: {summary['total_agents']}
  High Risk: {summary['high_risk']}
  Medium Risk: {summary['medium_risk']}
  Low Risk: {summary['low_risk']}

Blocked Requests: {status['blocked_count']}
Allowed Requests: {status['allowed_count']}
"""
        self.show_notification("Status", msg)
    
    def update_icon(self, color):
        """Update tray icon color."""
        if self.icon:
            self.icon.icon = self.create_icon_image(color)
    
    def show_notification(self, title, message):
        """Show system notification."""
        if self.icon:
            self.icon.notify(message, title)
    
    def quit_app(self, icon=None, item=None):
        """Exit application."""
        self.running = False
        if self.icon:
            self.icon.stop()
        sys.exit(0)
    
    def run(self):
        """Run the tray application."""
        menu = pystray.Menu(
            item('Start Protection', self.start_protection),
            item('Stop Protection', self.stop_protection),
            pystray.Menu.SEPARATOR,
            item('KILL SWITCH', self.activate_kill_switch),
            item('Resume Normal', self.deactivate_kill_switch),
            pystray.Menu.SEPARATOR,
            item('Show Status', self.show_status),
            item('Open Dashboard', self.show_dashboard),
            pystray.Menu.SEPARATOR,
            item('Quit', self.quit_app)
        )
        
        self.icon = pystray.Icon(
            "runtime_fence",
            self.create_icon_image("gray"),
            "Runtime Fence",
            menu
        )
        
        # Auto-start protection
        self.icon.run_detached()
        self.start_protection()
        
        # Keep running
        self.icon.run()


def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           RUNTIME FENCE - SYSTEM TRAY                        ║
    ║                                                              ║
    ║  Look for the shield icon in your system tray (bottom right) ║
    ║  Right-click for options:                                    ║
    ║    - Start/Stop Protection                                   ║
    ║    - KILL SWITCH (emergency stop all agents)                 ║
    ║    - View Status                                             ║
    ║    - Open Dashboard                                          ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    app = FenceTrayApp()
    app.run()


if __name__ == "__main__":
    main()
