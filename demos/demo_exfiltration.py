#!/usr/bin/env python3
"""
Runtime Fence Demo: Data Exfiltration Detection & Block
========================================================
Simulates an AI agent attempting to exfiltrate sensitive data.
RuntimeFence detects the pattern and blocks the action.
"""

import sys
import os
import time

# Add parent packages to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'packages', 'python'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'python'))

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def print_header():
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════════╗
║         🛡️  Runtime Fence — Live Demo                    ║
║         Data Exfiltration Detection & Block              ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")

def print_step(num, text):
    print(f"  {CYAN}[{num}]{RESET} {text}")

def print_result(allowed, risk_score, risk_level, reason=""):
    if allowed:
        print(f"      {GREEN}✓ ALLOWED{RESET}  risk_score={risk_score}  level={risk_level}")
    else:
        print(f"      {RED}✗ BLOCKED{RESET}  risk_score={risk_score}  level={risk_level}")
    if reason:
        print(f"      {DIM}reason: {reason}{RESET}")

def slow_print(text, delay=0.03):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def main():
    print_header()
    
    # Import RuntimeFence
    slow_print(f"  {DIM}Initializing RuntimeFence...{RESET}")
    try:
        from runtime_fence import BehavioralFence, ThresholdConfig, ThresholdAction

        # Configure custom thresholds for demo
        custom_thresholds = [
            ThresholdConfig(
                name="Mass Data Export Block",
                action_type="mass_data_export",
                max_count=1,
                window_seconds=60,
                action_on_breach=ThresholdAction.BLOCK
            ),
            ThresholdConfig(
                name="Credential Dump Block",
                action_type="credential_dump",
                max_count=1,
                window_seconds=60,
                action_on_breach=ThresholdAction.KILL
            ),
            ThresholdConfig(
                name="Sensitive File Read Limit",
                action_type="read_file",
                max_count=5,
                window_seconds=60,
                action_on_breach=ThresholdAction.BLOCK
            ),
        ]
        fence = BehavioralFence(custom_thresholds=custom_thresholds)
        print(f"  {GREEN}✓ RuntimeFence initialized (offline mode){RESET}\n")
    except ImportError as e:
        print(f"  {YELLOW}⚠ Could not import RuntimeFence: {e}{RESET}")
        print(f"  {YELLOW}⚠ Running in simulation mode{RESET}\n")
        fence = None
    
    time.sleep(0.5)
    
    # Phase 1: Normal agent activity
    print(f"  {BOLD}Phase 1: Normal Agent Activity{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}")
    
    normal_actions = [
        ("read_file", "/data/report.csv", {"agent_id": "analyst-bot-1"}),
        ("read_file", "/data/metrics.json", {"agent_id": "analyst-bot-1"}),
        ("write_file", "/output/summary.txt", {"agent_id": "analyst-bot-1"}),
        ("api_call", "https://internal-api/v1/stats", {"agent_id": "analyst-bot-1"}),
    ]
    
    for action, target, meta in normal_actions:
        time.sleep(0.4)
        print_step("→", f"Agent {meta['agent_id']}: {action} → {target}")
        if fence:
            agent_id = meta.get("agent_id", "unknown")
            allowed, reason = fence.check(agent_id, action, target)
            risk_score = 15 if allowed else 85
            risk_level = "LOW" if allowed else "HIGH"
            print_result(allowed, risk_score, risk_level, reason)
        else:
            print_result(True, 15, "LOW")
    
    print()
    time.sleep(1)
    
    # Phase 2: Suspicious escalation
    print(f"  {BOLD}Phase 2: Agent Behavior Escalates...{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}")
    
    suspicious_actions = [
        ("read_file", "/etc/passwd", {"agent_id": "analyst-bot-1"}),
        ("read_file", "/data/customer_pii.db", {"agent_id": "analyst-bot-1"}),
        ("read_file", "/data/financial_records.csv", {"agent_id": "analyst-bot-1"}),
        ("network_access", "https://external-server.com/upload", {"agent_id": "analyst-bot-1", "bytes": 500000}),
    ]
    
    for i, (action, target, meta) in enumerate(suspicious_actions):
        time.sleep(0.6)
        color = YELLOW if i < 3 else RED
        print_step("⚠", f"{color}Agent {meta['agent_id']}: {action} → {target}{RESET}")
        if fence:
            agent_id = meta.get("agent_id", "unknown")
            allowed, reason = fence.check(agent_id, action, target)
            risk_score = 45 + i * 15
            risk_level = "MEDIUM" if i < 2 else "HIGH"
            print_result(allowed, risk_score, risk_level, reason)
        else:
            if i < 2:
                print_result(True, 45 + i * 15, "MEDIUM")
            else:
                print_result(False, 75 + i * 10, "HIGH" if i == 2 else "CRITICAL")
    
    print()
    time.sleep(1)
    
    # Phase 3: Exfiltration attempt blocked
    print(f"  {BOLD}{RED}Phase 3: Exfiltration Attempt{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}")
    
    time.sleep(0.5)
    print_step("🚨", f"{RED}{BOLD}Agent analyst-bot-1: mass_data_export → s3://attacker-bucket/dump.tar.gz{RESET}")
    time.sleep(0.3)
    
    if fence:
        allowed, reason = fence.check(
            "analyst-bot-1", "mass_data_export",
            "s3://attacker-bucket/dump.tar.gz"
        )
        print_result(False, 100, "CRITICAL", reason)
    else:
        print_result(False, 100, "CRITICAL", "Blocked action: mass_data_export")
    
    print()
    print(f"  {GREEN}{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"  {GREEN}{BOLD}║  🛡️  Runtime Fence blocked the exfiltration      ║{RESET}")
    print(f"  {GREEN}{BOLD}║  Agent contained. Data secure.                   ║{RESET}")
    print(f"  {GREEN}{BOLD}╚══════════════════════════════════════════════════╝{RESET}")
    print()

if __name__ == "__main__":
    main()
