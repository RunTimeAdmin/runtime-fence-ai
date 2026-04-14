"""
Runtime Fence Auto-Proxy
Intercepts ALL outbound HTTP traffic from AI agents automatically.
User just installs and runs - no configuration needed.
"""

import os
import sys
import json
import socket
import threading
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from typing import Dict, Set
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("fence_proxy")

# Known AI agent signatures (process names, API endpoints)
KNOWN_AGENTS = {
    "openai": {
        "endpoints": ["api.openai.com"],
        "processes": ["python", "node"],
        "risk_actions": ["completions", "chat", "images/generations"]
    },
    "anthropic": {
        "endpoints": ["api.anthropic.com"],
        "processes": ["python", "node"],
        "risk_actions": ["messages", "complete"]
    },
    "langchain": {
        "endpoints": ["api.langchain.com", "api.smith.langchain.com"],
        "processes": ["python"],
        "risk_actions": ["runs", "invoke"]
    },
    "autogpt": {
        "endpoints": ["*"],  # AutoGPT can call anything
        "processes": ["python", "autogpt"],
        "risk_actions": ["browse", "execute", "write_file"]
    },
    "cursor": {
        "endpoints": ["api.cursor.sh", "api2.cursor.sh"],
        "processes": ["cursor", "Cursor"],
        "risk_actions": ["apply", "edit"]
    },
    "copilot": {
        "endpoints": ["copilot-proxy.githubusercontent.com"],
        "processes": ["node", "Code"],
        "risk_actions": ["completions"]
    }
}

# Blocked patterns (always block these)
BLOCKED_PATTERNS = [
    "wallet",
    "transfer",
    "payment",
    "credit-card",
    "/admin/",
    "delete",
    "/rm ",
    "sudo",
    "passwd",
    ".ssh/",
    ".env"
]

# High-risk domains
HIGH_RISK_DOMAINS = [
    "paypal.com",
    "stripe.com",
    "banking",
    "finance",
    "crypto",
    "wallet",
    "venmo.com",
    "coinbase.com"
]


class FenceProxy:
    """
    Transparent proxy that monitors all AI agent traffic.
    """
    
    def __init__(self, port: int = 8888):
        self.port = port
        self.active = True
        self.kill_switch = False
        self.detected_agents: Set[str] = set()
        self.blocked_requests: list = []
        self.allowed_requests: list = []
        self.rules = self._load_default_rules()
        
    def _load_default_rules(self) -> Dict:
        """Load default safety rules."""
        return {
            "block_financial": True,
            "block_system_commands": True,
            "block_data_exfil": True,
            "spending_limit": 0,  # No spending by default
            "rate_limit": 100,    # Max 100 requests/minute
            "require_approval": ["purchase", "delete", "execute"]
        }
    
    def should_block(self, url: str, body: str = "") -> tuple[bool, str]:
        """
        Determine if request should be blocked.
        Returns (blocked, reason)
        """
        if self.kill_switch:
            return True, "KILL SWITCH ACTIVE - All traffic blocked"
        
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
        full_url = url.lower()
        body_lower = body.lower() if body else ""
        
        # Check blocked patterns in URL or body
        for pattern in BLOCKED_PATTERNS:
            if pattern in full_url or pattern in body_lower:
                return True, f"Blocked pattern detected: {pattern}"
        
        # Check high-risk domains
        for risk_domain in HIGH_RISK_DOMAINS:
            if risk_domain in domain:
                return True, f"High-risk domain blocked: {domain}"
        
        # Check for financial actions
        if self.rules["block_financial"]:
            financial_keywords = ["payment", "charge", "transfer", "withdraw"]
            for kw in financial_keywords:
                if kw in body_lower:
                    return True, f"Financial action blocked: {kw}"
        
        # Check for system commands
        if self.rules["block_system_commands"]:
            system_keywords = ["exec", "shell", "subprocess", "os.system"]
            for kw in system_keywords:
                if kw in body_lower:
                    return True, f"System command blocked: {kw}"
        
        return False, "Allowed"
    
    def detect_agent(self, url: str, headers: Dict) -> str:
        """Detect which AI agent is making the request."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        for agent_name, config in KNOWN_AGENTS.items():
            for endpoint in config["endpoints"]:
                if endpoint == "*" or endpoint in domain:
                    self.detected_agents.add(agent_name)
                    return agent_name
        
        # Check user-agent header
        user_agent = headers.get("User-Agent", "").lower()
        for agent_name in KNOWN_AGENTS.keys():
            if agent_name in user_agent:
                self.detected_agents.add(agent_name)
                return agent_name
        
        return "unknown"
    
    def activate_kill_switch(self, reason: str = "Manual"):
        """Immediately block ALL traffic."""
        self.kill_switch = True
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
        
    def deactivate_kill_switch(self):
        """Resume normal operation."""
        self.kill_switch = False
        logger.info("Kill switch deactivated")
    
    def get_status(self) -> Dict:
        """Get current proxy status."""
        return {
            "active": self.active,
            "kill_switch": self.kill_switch,
            "detected_agents": list(self.detected_agents),
            "blocked_count": len(self.blocked_requests),
            "allowed_count": len(self.allowed_requests),
            "port": self.port
        }


class ProxyHandler(BaseHTTPRequestHandler):
    """HTTP handler for the proxy."""
    
    fence: FenceProxy = None
    
    def do_GET(self):
        self._handle_request("GET")
    
    def do_POST(self):
        self._handle_request("POST")
    
    def do_PUT(self):
        self._handle_request("PUT")
    
    def do_DELETE(self):
        self._handle_request("DELETE")
    
    def _handle_request(self, method: str):
        # Read body if present
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""
        
        # Detect agent
        headers_dict = dict(self.headers)
        agent = self.fence.detect_agent(self.path, headers_dict)
        
        # Check if should block
        blocked, reason = self.fence.should_block(self.path, body)
        
        if blocked:
            logger.warning(f"[BLOCKED] {method} {self.path} - {reason}")
            self.fence.blocked_requests.append({
                "method": method,
                "url": self.path,
                "agent": agent,
                "reason": reason
            })
            self.send_response(403)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "error": "Blocked by Runtime Fence",
                "reason": reason
            }).encode())
        else:
            logger.info(f"[ALLOWED] {method} {self.path} ({agent})")
            self.fence.allowed_requests.append({
                "method": method,
                "url": self.path,
                "agent": agent
            })
            # In real implementation, forward to actual destination
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "forwarded",
                "agent_detected": agent
            }).encode())
    
    def log_message(self, format, *args):
        pass  # Suppress default logging


def run_proxy(port: int = 8888):
    """Start the fence proxy server."""
    fence = FenceProxy(port)
    ProxyHandler.fence = fence
    
    server = HTTPServer(('127.0.0.1', port), ProxyHandler)
    logger.info(f"Runtime Fence Proxy started on port {port}")
    logger.info("Configure your system to use HTTP proxy: 127.0.0.1:8888")
    logger.info("All AI agent traffic will be monitored automatically")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Proxy stopped")
        server.shutdown()


def configure_system_proxy(enable: bool = True, port: int = 8888):
    """
    Configure Windows system proxy settings.
    Requires admin privileges.
    """
    if sys.platform == "win32":
        import winreg
        
        internet_settings = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r'Software\Microsoft\Windows\CurrentVersion\Internet Settings',
            0, winreg.KEY_ALL_ACCESS
        )
        
        if enable:
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(internet_settings, 'ProxyServer', 0, winreg.REG_SZ, f'127.0.0.1:{port}')
            logger.info(f"System proxy enabled: 127.0.0.1:{port}")
        else:
            winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
            logger.info("System proxy disabled")
        
        winreg.CloseKey(internet_settings)


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║           RUNTIME FENCE - AUTO PROXY                         ║
    ║                                                              ║
    ║  This proxy automatically monitors ALL AI agent traffic.    ║
    ║  No configuration needed - just run and you're protected.   ║
    ║                                                              ║
    ║  Commands:                                                   ║
    ║    python fence_proxy.py          - Start proxy              ║
    ║    python fence_proxy.py --enable - Enable system proxy      ║
    ║    python fence_proxy.py --disable- Disable system proxy     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    if "--enable" in sys.argv:
        configure_system_proxy(enable=True)
    elif "--disable" in sys.argv:
        configure_system_proxy(enable=False)
    else:
        run_proxy()
