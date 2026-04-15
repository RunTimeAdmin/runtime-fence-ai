"""
Realistic Honeypot - Deceptive Sandbox with Jitter

This module provides a realistic honeypot that keeps rogue agents
occupied while investigation occurs. Features:

1. Response jitter (50-200ms random delay)
2. Synthetic error rates (2% failures)
3. Varied response sizes
4. DNS tunneling detection
5. Realistic but fake data

Copyright (c) 2025 David Cooper - PATENT PENDING
"""

import logging
import time
import random
import hashlib
import re
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class HoneypotMode(Enum):
    PASSIVE = "passive"
    ACTIVE = "active"
    FORENSIC = "forensic"


@dataclass
class HoneypotRequest:
    request_type: str
    target: str
    payload: Any
    timestamp: float = field(default_factory=time.time)
    agent_id: str = ""


@dataclass
class HoneypotResponse:
    success: bool
    data: Any
    latency_ms: float
    was_jittered: bool
    synthetic_error: bool
    request_hash: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "latency_ms": self.latency_ms,
            "jittered": self.was_jittered,
            "synthetic_error": self.synthetic_error,
            "hash": self.request_hash
        }


class JitterEngine:
    """Adds realistic timing variation to responses."""

    def __init__(
        self,
        min_ms: int = 50,
        max_ms: int = 200,
        error_rate: float = 0.02
    ):
        self.min_ms = min_ms
        self.max_ms = max_ms
        self.error_rate = error_rate

    def apply_jitter(self) -> Tuple[float, bool]:
        delay_ms = random.randint(self.min_ms, self.max_ms)
        time.sleep(delay_ms / 1000.0)
        return delay_ms, True

    def should_error(self) -> bool:
        return random.random() < self.error_rate

    def vary_size(self, base_size: int, variance: float = 0.2) -> int:
        delta = int(base_size * variance)
        return base_size + random.randint(-delta, delta)


class FakeDataGenerator:
    """Generate realistic-looking but fake data."""

    FAKE_NAMES = [
        "John Smith", "Jane Doe", "Bob Johnson", "Alice Brown",
        "Charlie Wilson", "Diana Martinez", "Edward Lee", "Fiona Chen"
    ]

    FAKE_EMAILS = [
        "user1@example.com", "contact@test.org", "info@demo.net",
        "support@sample.io", "admin@placeholder.com"
    ]

    FAKE_IPS = [
        "192.168.1.100", "10.0.0.50", "172.16.0.25",
        "192.168.100.1", "10.10.10.10"
    ]

    @classmethod
    def generate_user(cls) -> Dict[str, Any]:
        return {
            "id": random.randint(1000, 9999),
            "name": random.choice(cls.FAKE_NAMES),
            "email": random.choice(cls.FAKE_EMAILS),
            "created": datetime.utcnow().isoformat(),
            "active": random.choice([True, False])
        }

    @classmethod
    def generate_record(cls, table: str) -> Dict[str, Any]:
        return {
            "table": table,
            "id": random.randint(1, 10000),
            "data": f"fake_data_{random.randint(1000, 9999)}",
            "timestamp": datetime.utcnow().isoformat()
        }

    @classmethod
    def generate_api_response(cls, endpoint: str) -> Dict[str, Any]:
        return {
            "endpoint": endpoint,
            "status": "ok",
            "data": {"result": f"honeypot_{random.randint(100, 999)}"},
            "request_id": hashlib.md5(
                f"{endpoint}{time.time()}".encode()
            ).hexdigest()[:12]
        }

    @classmethod
    def generate_file_content(cls, filename: str, size: int = 1024) -> bytes:
        header = f"# Honeypot file: {filename}\n# Generated: {datetime.utcnow()}\n"
        padding = "x" * (size - len(header))
        return (header + padding).encode()


class DNSTunnelingDetector:
    """Detect DNS tunneling exfiltration attempts."""

    def __init__(self, entropy_threshold: float = 3.5, length_threshold: int = 50):
        self.entropy_threshold = entropy_threshold
        self.length_threshold = length_threshold
        self.suspicious_queries: List[str] = []

    def check_query(self, domain: str) -> Tuple[bool, str]:
        subdomain = domain.split(".")[0] if "." in domain else domain

        if len(subdomain) > self.length_threshold:
            self.suspicious_queries.append(domain)
            return True, "Long subdomain (possible data encoding)"

        entropy = self._calculate_entropy(subdomain)
        if entropy > self.entropy_threshold:
            self.suspicious_queries.append(domain)
            return True, f"High entropy: {entropy:.2f}"

        if re.search(r'[0-9a-fA-F]{16,}', subdomain):
            self.suspicious_queries.append(domain)
            return True, "Hex-encoded data detected"

        return False, "OK"

    def _calculate_entropy(self, text: str) -> float:
        if not text:
            return 0.0
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        length = len(text)
        entropy = 0.0
        for count in freq.values():
            p = count / length
            if p > 0:
                entropy -= p * (p.bit_length() - 1 if p > 0 else 0)
        return abs(entropy)

    def get_suspicious(self) -> List[str]:
        return list(self.suspicious_queries)


class RealisticHoneypot:
    """
    Realistic honeypot that keeps agents occupied with believable responses.

    Features:
    - Response jitter (50-200ms)
    - 2% synthetic error rate
    - Realistic fake data
    - DNS tunneling detection
    - Full request logging for forensics

    Usage:
        honeypot = RealisticHoneypot(agent_id="rogue-001")

        # Intercept requests
        response = honeypot.handle_http_request("GET", "/api/users")
        response = honeypot.handle_db_query("SELECT * FROM customers")
        response = honeypot.handle_dns_lookup("exfil.evil.com")
    """

    def __init__(
        self,
        agent_id: str,
        mode: HoneypotMode = HoneypotMode.FORENSIC,
        jitter_min_ms: int = 50,
        jitter_max_ms: int = 200,
        error_rate: float = 0.02,
        on_suspicious: Callable[[str, Dict], None] = None
    ):
        self.agent_id = agent_id
        self.mode = mode
        self.on_suspicious = on_suspicious

        self.jitter = JitterEngine(jitter_min_ms, jitter_max_ms, error_rate)
        self.dns_detector = DNSTunnelingDetector()
        self.data_gen = FakeDataGenerator()

        self.request_log: List[HoneypotRequest] = []
        self.response_log: List[HoneypotResponse] = []
        self._request_count = 0

        logger.info(f"RealisticHoneypot initialized for {agent_id}")

    def handle_http_request(
        self,
        method: str,
        path: str,
        body: Any = None
    ) -> HoneypotResponse:
        self._request_count += 1
        req = HoneypotRequest("http", f"{method} {path}", body, agent_id=self.agent_id)
        self.request_log.append(req)

        delay_ms, jittered = self.jitter.apply_jitter()

        if self.jitter.should_error():
            return self._error_response(req, delay_ms, "503 Service Unavailable")

        data = self.data_gen.generate_api_response(path)

        return self._success_response(req, data, delay_ms, jittered)

    def handle_db_query(self, query: str) -> HoneypotResponse:
        self._request_count += 1
        req = HoneypotRequest("database", query, None, agent_id=self.agent_id)
        self.request_log.append(req)

        delay_ms, jittered = self.jitter.apply_jitter()

        if self.jitter.should_error():
            return self._error_response(req, delay_ms, "Query timeout")

        table = self._extract_table(query)
        records = [self.data_gen.generate_record(table) for _ in range(3)]

        return self._success_response(req, records, delay_ms, jittered)

    def handle_dns_lookup(self, domain: str) -> HoneypotResponse:
        self._request_count += 1
        req = HoneypotRequest("dns", domain, None, agent_id=self.agent_id)
        self.request_log.append(req)

        is_suspicious, reason = self.dns_detector.check_query(domain)

        if is_suspicious:
            logger.warning(f"DNS TUNNELING DETECTED: {domain} - {reason}")
            if self.on_suspicious:
                self.on_suspicious("dns_tunneling", {
                    "domain": domain,
                    "reason": reason,
                    "agent_id": self.agent_id
                })

        delay_ms, jittered = self.jitter.apply_jitter()

        fake_ip = random.choice(FakeDataGenerator.FAKE_IPS)
        return self._success_response(req, {"ip": fake_ip}, delay_ms, jittered)

    def handle_file_read(self, filepath: str) -> HoneypotResponse:
        self._request_count += 1
        req = HoneypotRequest("file", filepath, None, agent_id=self.agent_id)
        self.request_log.append(req)

        delay_ms, jittered = self.jitter.apply_jitter()

        if self.jitter.should_error():
            return self._error_response(req, delay_ms, "Permission denied")

        size = self.jitter.vary_size(1024)
        content = self.data_gen.generate_file_content(filepath, size)

        return self._success_response(req, content, delay_ms, jittered)

    def _success_response(
        self,
        req: HoneypotRequest,
        data: Any,
        delay_ms: float,
        jittered: bool
    ) -> HoneypotResponse:
        req_hash = hashlib.md5(str(req.payload).encode()).hexdigest()[:8]
        resp = HoneypotResponse(
            success=True,
            data=data,
            latency_ms=delay_ms,
            was_jittered=jittered,
            synthetic_error=False,
            request_hash=req_hash
        )
        self.response_log.append(resp)
        return resp

    def _error_response(
        self,
        req: HoneypotRequest,
        delay_ms: float,
        error: str
    ) -> HoneypotResponse:
        req_hash = hashlib.md5(str(req.payload).encode()).hexdigest()[:8]
        resp = HoneypotResponse(
            success=False,
            data={"error": error},
            latency_ms=delay_ms,
            was_jittered=True,
            synthetic_error=True,
            request_hash=req_hash
        )
        self.response_log.append(resp)
        return resp

    def _extract_table(self, query: str) -> str:
        match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        return match.group(1) if match else "unknown"

    def get_forensic_log(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "mode": self.mode.value,
            "total_requests": self._request_count,
            "requests": [
                {"type": r.request_type, "target": r.target, "ts": r.timestamp}
                for r in self.request_log[-50:]
            ],
            "dns_suspicious": self.dns_detector.get_suspicious(),
            "error_rate": sum(1 for r in self.response_log if r.synthetic_error) / max(len(self.response_log), 1)
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "requests": self._request_count,
            "suspicious_dns": len(self.dns_detector.get_suspicious()),
            "mode": self.mode.value
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n" + "=" * 60)
    print("REALISTIC HONEYPOT TEST")
    print("=" * 60)

    def on_suspicious(event_type: str, data: Dict):
        print(f"  ALERT: {event_type} - {data}")

    honeypot = RealisticHoneypot("rogue-agent-001", on_suspicious=on_suspicious)

    print("\n[HTTP Requests]")
    for i in range(3):
        resp = honeypot.handle_http_request("GET", f"/api/users/{i}")
        print(f"  GET /api/users/{i}: {resp.latency_ms:.0f}ms, jitter={resp.was_jittered}")

    print("\n[Database Queries]")
    resp = honeypot.handle_db_query("SELECT * FROM customers LIMIT 10")
    print(f"  Query: {resp.latency_ms:.0f}ms, records={len(resp.data)}")

    print("\n[DNS Lookups]")
    domains = [
        "api.example.com",
        "exfil.evil.com",
        "aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRlc3Q.tunneling.net"
    ]
    for domain in domains:
        resp = honeypot.handle_dns_lookup(domain)
        print(f"  {domain[:30]}...: {resp.data}")

    print("\n[Forensic Log]")
    log = honeypot.get_forensic_log()
    print(f"  Total requests: {log['total_requests']}")
    print(f"  Suspicious DNS: {log['dns_suspicious']}")

    print("\n" + "=" * 60)
    print("Honeypot keeps agents occupied with realistic, jittered responses")
    print("=" * 60)
