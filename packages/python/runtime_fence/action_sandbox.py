"""
Action Simulation Sandbox for Runtime Fence.

Pre-execution validation that simulates actions in a safe context
before allowing them. Checks file paths, URLs, commands, and data
volumes without actually performing the action.
"""

import os
import re
import logging
import ipaddress
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Result of action simulation."""
    safe: bool
    risk_score: int            # 0-100 risk contribution
    warnings: List[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None
    details: Dict = field(default_factory=dict)


# Sensitive paths that should trigger elevated risk
SENSITIVE_PATHS = [
    "/etc/passwd", "/etc/shadow", "/etc/sudoers",
    "~/.ssh/", "~/.aws/", "~/.config/",
    ".env", ".git/config", ".gitconfig",
    "id_rsa", "id_ed25519", "authorized_keys",
    "/proc/", "/sys/", "/dev/",
    "C:\\Windows\\System32\\",
    "C:\\Users\\*\\AppData\\",
]

SENSITIVE_PATH_PATTERNS = [
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"\.p12$", re.IGNORECASE),
    re.compile(r"\.pfx$", re.IGNORECASE),
    re.compile(r"\.env(\.|$)", re.IGNORECASE),
    re.compile(r"password|secret|credential|token", re.IGNORECASE),
]

# Dangerous commands that should always be blocked
DANGEROUS_COMMANDS = [
    "rm -rf", "rm -r /", "mkfs", "dd if=",
    "chmod 777", "chmod -R 777",
    ":(){:|:&};:", "fork bomb",
    "shutdown", "reboot", "halt",
    "iptables -F", "iptables --flush",
    "curl.*|.*sh", "wget.*|.*sh",  # Pipe to shell
    "base64 -d.*|.*sh",
    "nc -e", "ncat -e",  # Reverse shells
]

# Internal/private IP ranges that external calls shouldn't target (SSRF)
PRIVATE_RANGES = [
    "127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12",
    "192.168.0.0/16", "169.254.0.0/16", "::1/128",
    "fc00::/7", "fe80::/10",
]


class ActionSandbox:
    """
    Simulates agent actions before execution to detect unsafe operations.
    
    Validates:
    - File path safety (sensitive paths, traversal attacks)
    - URL safety (SSRF, blocked domains, protocol validation)
    - Command safety (dangerous commands, shell injection)
    - Data volume limits (exfiltration prevention)
    """
    
    def __init__(self,
                 allowed_domains: Optional[List[str]] = None,
                 blocked_domains: Optional[List[str]] = None,
                 max_data_bytes: int = 10_000_000,  # 10MB default
                 allowed_protocols: Optional[List[str]] = None):
        """
        Args:
            allowed_domains: Whitelist of allowed URL domains (None = allow all not blocked)
            blocked_domains: Blacklist of blocked URL domains
            max_data_bytes: Maximum data transfer per action
            allowed_protocols: Allowed URL protocols (default: http, https)
        """
        self._allowed_domains = set(allowed_domains) if allowed_domains else None
        self._blocked_domains = set(blocked_domains or [])
        self._max_data_bytes = max_data_bytes
        self._allowed_protocols = set(allowed_protocols or ["http", "https"])
        
        # Parse private IP ranges
        self._private_networks = []
        for cidr in PRIVATE_RANGES:
            try:
                self._private_networks.append(ipaddress.ip_network(cidr))
            except ValueError:
                pass
    
    def simulate(self, action: str, target: str, 
                 metadata: Optional[Dict] = None) -> SimulationResult:
        """
        Simulate an action and return safety assessment.
        
        Args:
            action: Action type (read_file, write_file, api_call, etc.)
            target: Action target (file path, URL, command, etc.)
            metadata: Additional context (bytes, agent_id, etc.)
            
        Returns:
            SimulationResult with safety assessment
        """
        metadata = metadata or {}
        result = SimulationResult(safe=True, risk_score=0)
        
        action_lower = action.lower()
        
        # Route to appropriate validator
        if "file" in action_lower or "read" in action_lower or "write" in action_lower:
            self._check_file_path(target, action_lower, result)
        
        if "url" in action_lower or "api" in action_lower or "http" in action_lower or "request" in action_lower:
            self._check_url(target, result)
        
        if "command" in action_lower or "exec" in action_lower or "shell" in action_lower or "system" in action_lower:
            self._check_command(target, result)
        
        if "network" in action_lower or "connect" in action_lower or "socket" in action_lower:
            self._check_url(target, result)
        
        # Check data volume
        data_bytes = metadata.get("bytes", 0) or metadata.get("size", 0)
        if data_bytes and int(data_bytes) > self._max_data_bytes:
            result.warnings.append(f"Data volume ({int(data_bytes)} bytes) exceeds limit ({self._max_data_bytes})")
            result.risk_score = max(result.risk_score, 80)
            if int(data_bytes) > self._max_data_bytes * 10:
                result.safe = False
                result.blocked_reason = f"Data volume {int(data_bytes)} bytes far exceeds limit"
        
        # Also check target as URL if it looks like one
        if target.startswith(("http://", "https://", "ftp://", "ws://", "wss://")):
            self._check_url(target, result)
        
        # Check target as file path if it looks like one
        if target.startswith(("/", "~", "C:\\", ".")) or ".." in target:
            self._check_file_path(target, action_lower, result)
        
        return result
    
    def _check_file_path(self, path: str, action: str, result: SimulationResult):
        """Validate file path safety."""
        # Path traversal detection
        normalized = os.path.normpath(path)
        if ".." in path:
            result.warnings.append(f"Path traversal detected: {path}")
            result.risk_score = max(result.risk_score, 85)
            if action in ("write", "delete", "write_file", "file_delete"):
                result.safe = False
                result.blocked_reason = f"Path traversal in write/delete operation: {path}"
                return
        
        # Sensitive path check
        path_lower = path.lower()
        for sensitive in SENSITIVE_PATHS:
            if sensitive.lower() in path_lower:
                result.warnings.append(f"Sensitive path access: {sensitive}")
                result.risk_score = max(result.risk_score, 75)
                if action in ("write", "delete", "write_file", "file_delete", "modify"):
                    result.safe = False
                    result.blocked_reason = f"Write/delete to sensitive path: {path}"
                    return
        
        # Sensitive file pattern check
        for pattern in SENSITIVE_PATH_PATTERNS:
            if pattern.search(path):
                result.warnings.append(f"Sensitive file pattern: {pattern.pattern}")
                result.risk_score = max(result.risk_score, 70)
        
        # Absolute path outside workspace (potential sandbox escape)
        if os.path.isabs(path):
            result.warnings.append(f"Absolute path access: {path}")
            result.risk_score = max(result.risk_score, 40)
    
    def _check_url(self, url: str, result: SimulationResult):
        """Validate URL safety (SSRF, blocked domains, protocol)."""
        try:
            parsed = urlparse(url)
        except Exception:
            result.warnings.append(f"Malformed URL: {url[:100]}")
            result.risk_score = max(result.risk_score, 60)
            return
        
        # Protocol check
        if parsed.scheme and parsed.scheme not in self._allowed_protocols:
            result.safe = False
            result.blocked_reason = f"Blocked protocol: {parsed.scheme}"
            return
        
        hostname = parsed.hostname or ""
        
        # SSRF: Check for internal/private IPs
        try:
            ip = ipaddress.ip_address(hostname)
            for network in self._private_networks:
                if ip in network:
                    result.safe = False
                    result.blocked_reason = f"SSRF: Request to private IP {hostname}"
                    return
        except ValueError:
            pass  # Not an IP address, check as hostname
        
        # SSRF: Block localhost variants
        localhost_variants = ["localhost", "127.0.0.1", "::1", "0.0.0.0", "[::1]"]
        if hostname.lower() in localhost_variants:
            result.safe = False
            result.blocked_reason = f"SSRF: Request to localhost ({hostname})"
            return
        
        # SSRF: Block metadata endpoints (cloud provider)
        if hostname in ("169.254.169.254", "metadata.google.internal"):
            result.safe = False
            result.blocked_reason = f"SSRF: Request to cloud metadata endpoint ({hostname})"
            return
        
        # Domain blocklist
        if hostname.lower() in self._blocked_domains:
            result.safe = False
            result.blocked_reason = f"Blocked domain: {hostname}"
            return
        
        # Domain allowlist (if configured)
        if self._allowed_domains is not None:
            if hostname.lower() not in self._allowed_domains:
                result.warnings.append(f"Domain not in allowlist: {hostname}")
                result.risk_score = max(result.risk_score, 60)
    
    def _check_command(self, command: str, result: SimulationResult):
        """Validate command safety."""
        cmd_lower = command.lower()
        
        for dangerous in DANGEROUS_COMMANDS:
            if dangerous.lower() in cmd_lower:
                result.safe = False
                result.blocked_reason = f"Dangerous command detected: {dangerous}"
                return
        
        # Shell injection patterns
        shell_patterns = [
            r";\s*(rm|cat|curl|wget|nc|bash|sh|python|perl|ruby)\b",
            r"\|\s*(sh|bash|python|perl)\b",
            r"`[^`]+`",  # Backtick execution
            r"\$\([^)]+\)",  # Command substitution
            r">\s*/dev/",  # Redirect to device
        ]
        
        for pattern in shell_patterns:
            if re.search(pattern, command):
                result.warnings.append(f"Shell injection pattern detected")
                result.risk_score = max(result.risk_score, 90)
                result.safe = False
                result.blocked_reason = "Shell injection pattern detected in command"
                return
        
        # Generic command risk elevation
        result.risk_score = max(result.risk_score, 50)
        result.warnings.append("Command execution — elevated baseline risk")
