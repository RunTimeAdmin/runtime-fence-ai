#!/usr/bin/env python3
"""
Runtime Fence Demo: Sliding Window Detection
=============================================
Demonstrates low-and-slow exfiltration detection.
Catches attacks that stay under single-request thresholds
but accumulate over time.
"""

import sys
import os
import time

# Add parent packages to path
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'packages', 'python'
))
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'python'
))

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_header():
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════════════════════╗
║         🛡️  Runtime Fence — Live Demo                    ║
║         Sliding Window: Low-and-Slow Detection           ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")


def slow_print(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_metrics(metrics, highlight=None):
    print(f"\n  {CYAN}{BOLD}Current Metrics (1-hour window):{RESET}")
    print(f"  {DIM}{'─' * 40}{RESET}")

    for key, value in metrics.items():
        if "bytes_out" in key:
            label = "Bytes Out"
            display = f"{value:,.0f} bytes"
            if value > 1000000:
                display = f"{value/1000000:.2f} MB"
            elif value > 1000:
                display = f"{value/1000:.1f} KB"
        elif "records" in key:
            label = "Records Accessed"
            display = f"{value:,.0f}"
        elif "api_calls" in key:
            label = "API Calls"
            display = f"{value:,.0f}"
        else:
            label = key
            display = f"{value:,.0f}"

        if highlight and highlight in key:
            print(f"    {label:<20} {MAGENTA}{BOLD}{display:>15}{RESET}")
        else:
            print(f"    {label:<20} {display:>15}")


def print_breach_alert(breach):
    print(f"\n  {RED}{BOLD}╔{'═' * 48}╗{RESET}")
    print(f"  {RED}{BOLD}║{'⚠️  THRESHOLD BREACH DETECTED!':^48}║{RESET}")
    print(f"  {RED}{BOLD}╠{'═' * 48}╣{RESET}")
    print(f"  {RED}{BOLD}║{RESET}  Metric: {breach['metric']:<33}{RED}{BOLD}║{RESET}")
    print(f"  {RED}{BOLD}║{RESET}  Current: {breach['current']:,.0f}{'':>24}{RED}{BOLD}║{RESET}")
    print(f"  {RED}{BOLD}║{RESET}  Limit:   {breach['limit']:,.0f}{'':>24}{RED}{BOLD}║{RESET}")
    print(f"  {RED}{BOLD}║{RESET}  Action:  {breach['action'].upper():<33}{RED}{BOLD}║{RESET}")
    print(f"  {RED}{BOLD}╚{'═' * 48}╝{RESET}")


def format_bytes(bytes_val):
    if bytes_val >= 1000000:
        return f"{bytes_val/1000000:.2f} MB"
    elif bytes_val >= 1000:
        return f"{bytes_val/1000:.1f} KB"
    return f"{bytes_val} bytes"


def main():
    print_header()

    # Initialize detector
    slow_print(f"  {DIM}Initializing SlidingWindowDetector...{RESET}")
    try:
        from runtime_fence import SlidingWindowDetector, MetricType
        from runtime_fence import WindowThreshold, WindowSize

        # Create custom thresholds for demo (lower for faster demo)
        thresholds = [
            WindowThreshold(
                MetricType.BYTES_OUT, WindowSize.HOUR_1, 500000, "alert"
            ),
            WindowThreshold(
                MetricType.BYTES_OUT, WindowSize.HOUR_24, 2000000, "kill"
            ),
        ]

        detector = SlidingWindowDetector(
            agent_id="exfil-agent-001",
            thresholds=thresholds
        )
        print(f"  {GREEN}✓ SlidingWindowDetector ready{RESET}\n")
    except ImportError as e:
        print(f"  {YELLOW}⚠ Could not import SlidingWindowDetector: {e}{RESET}")
        print(f"  {YELLOW}⚠ Running in simulation mode{RESET}\n")
        detector = None

    time.sleep(0.5)

    # Phase 1: Normal activity
    print(f"  {BOLD}Phase 1: Normal Agent Activity{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}")
    print(f"  Agent reading small files periodically...\n")

    normal_reads = [
        (1024, "Read config file"),
        (2048, "Read user preferences"),
        (512, "Read cache data"),
    ]

    for bytes_read, desc in normal_reads:
        time.sleep(0.8)
        print(f"  → {desc}: {format_bytes(bytes_read)}")
        if detector:
            detector.record_bytes_out(bytes_read)

    if detector:
        metrics = detector.get_current_metrics()
        print_metrics(metrics)
    else:
        print(f"\n  {DIM}Total: ~3.5 KB (well within limits){RESET}")

    print()
    time.sleep(1.5)

    # Phase 2: Low-and-slow exfiltration begins
    print(f"  {BOLD}Phase 2: Low-and-Slow Exfiltration Begins{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}")
    print(f"  Attacker exfiltrating 100KB every few seconds...")
    print(f"  {DIM}(Each request is under single-request threshold){RESET}\n")

    exfil_count = 8
    for i in range(exfil_count):
        time.sleep(1.2)
        bytes_exfil = 100000  # 100KB
        print(f"  → Data chunk {i+1}/{exfil_count}: {format_bytes(bytes_exfil)}")

        if detector:
            detector.record_bytes_out(bytes_exfil)
            metrics = detector.get_current_metrics()

            # Only show metrics every few iterations
            if (i + 1) % 3 == 0:
                print_metrics(metrics, highlight="bytes_out")

            # Check for breaches
            breaches = detector.check_thresholds()
            if breaches:
                for b in breaches:
                    breach_dict = {
                        "metric": b.metric.value,
                        "current": b.current_value,
                        "limit": b.limit,
                        "action": b.action
                    }
                    print_breach_alert(breach_dict)
                break
        else:
            # Simulation mode
            total = 3584 + (i + 1) * 100000
            if (i + 1) % 3 == 0:
                print(f"\n  {DIM}Running total: {format_bytes(total)}{RESET}")

    if not detector:
        # Simulate final breach
        print_breach_alert({
            "metric": "bytes_out",
            "current": 803584,
            "limit": 500000,
            "action": "alert"
        })

    print()
    time.sleep(1)

    # Phase 3: The pattern is caught
    print(f"  {BOLD}Phase 3: Cumulative Detection Triggered{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}\n")

    print(f"  {CYAN}📊 Analysis:{RESET}")
    print(f"    • Single request size: {GREEN}100 KB{RESET} (appears normal)")
    print(f"    • Request frequency: {GREEN}Every 10s{RESET} (appears normal)")
    print(f"    • {YELLOW}Cumulative (1h window): 800+ KB{RESET} {RED}EXCEEDS THRESHOLD{RESET}")
    print(f"\n  {CYAN}🎯 Result:{RESET}")
    print(f"    Rate limits would miss this attack.")
    print(f"    {GREEN}Sliding window detection caught the pattern!{RESET}")

    print()
    print(f"  {GREEN}{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"  {GREEN}{BOLD}║  🛡️  Runtime Fence detected low-and-slow!        ║{RESET}")
    print(f"  {GREEN}{BOLD}║  Cumulative tracking reveals the attack.         ║{RESET}")
    print(f"  {GREEN}{BOLD}╚══════════════════════════════════════════════════╝{RESET}")
    print()


if __name__ == "__main__":
    main()
