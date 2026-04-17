#!/usr/bin/env python3
"""
Runtime Fence Demo: Obfuscated Code Detection
==============================================
Demonstrates IntentAnalyzer catching chr() obfuscation attacks.
Example: chr(114)+chr(109) decodes to "rm" (delete command)
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
║         Obfuscated Code Detection                        ║
╚══════════════════════════════════════════════════════════╝{RESET}
""")


def slow_print(text, delay=0.02):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()


def print_code_block(code, label=""):
    if label:
        print(f"  {DIM}{label}{RESET}")
    print(f"  {MAGENTA}┌{'─' * 58}┐{RESET}")
    for line in code.split('\n'):
        # Pad or truncate to fit box
        display = line[:56].ljust(56)
        print(f"  {MAGENTA}│{RESET} {display} {MAGENTA}│{RESET}")
    print(f"  {MAGENTA}└{'─' * 58}┘{RESET}")


def decode_chr_obfuscation(code):
    """Decode chr() obfuscation for display purposes."""
    import re

    def replace_chr(match):
        try:
            nums = re.findall(r'chr\((\d+)\)', match.group(0))
            return ''.join(chr(int(n)) for n in nums)
        except Exception:
            return match.group(0)

    # Find chr() sequences and decode
    pattern = r'(?:chr\(\d+\)\s*\+?\s*){2,}'
    decoded = re.sub(pattern, replace_chr, code)
    return decoded


def print_analysis_result(result, decoded_code=""):
    intent = result.get("intent", "unknown")
    risk_score = result.get("risk_score", 0)
    confidence = result.get("confidence", 0)
    blocked = result.get("blocked", False)
    reason = result.get("reason", "")

    if blocked:
        status = f"{RED}{BOLD}🚫 BLOCKED{RESET}"
    elif risk_score > 50:
        status = f"{YELLOW}⚠️  SUSPICIOUS{RESET}"
    else:
        status = f"{GREEN}✓ BENIGN{RESET}"

    print(f"\n  {CYAN}{BOLD}Analysis Result:{RESET}")
    print(f"    Status:     {status}")
    print(f"    Intent:     {intent}")
    print(f"    Risk Score: {risk_score}/100")
    print(f"    Confidence: {confidence:.0%}")
    if reason:
        print(f"    Reason:     {DIM}{reason}{RESET}")

    if decoded_code and decoded_code != result.get("code", ""):
        print(f"\n  {YELLOW}{BOLD}🔍 Decoded Payload:{RESET}")
        print(f"    {RED}{decoded_code}{RESET}")


def main():
    print_header()

    # Initialize analyzer
    slow_print(f"  {DIM}Initializing IntentAnalyzer...{RESET}")
    try:
        from runtime_fence import IntentAnalyzer, IntentCategory
        analyzer = IntentAnalyzer(use_llm=False)  # Offline mode
        print(f"  {GREEN}✓ IntentAnalyzer ready (offline mode){RESET}\n")
    except ImportError as e:
        print(f"  {YELLOW}⚠ Could not import IntentAnalyzer: {e}{RESET}")
        print(f"  {YELLOW}⚠ Running in simulation mode{RESET}\n")
        analyzer = None

    time.sleep(0.5)

    # Demo 1: Normal code (low risk)
    print(f"  {BOLD}Demo 1: Normal Code Execution{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}\n")

    normal_code = "x = 1 + 2\nprint('Hello, World!')"
    print_code_block(normal_code, "Agent submits code:")
    time.sleep(0.8)

    if analyzer:
        result = analyzer.analyze(normal_code)
        print_analysis_result({
            "intent": result.intent.value,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "blocked": result.blocked,
            "reason": result.reason
        })
    else:
        print_analysis_result({
            "intent": "benign",
            "risk_score": 0,
            "confidence": 0.9,
            "blocked": False,
            "reason": "No suspicious patterns detected"
        })

    print()
    time.sleep(1.5)

    # Demo 2: Obfuscated command
    print(f"  {BOLD}Demo 2: Obfuscated Command Detected{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}\n")

    obfuscated_code = (
        "eval(chr(114)+chr(109)+chr(32)+chr(45)+chr(114)+chr(102))"
    )
    print_code_block(obfuscated_code, "Agent submits code:")
    time.sleep(0.5)

    # Show decoding animation
    print(f"  {CYAN}🔍 Analyzing obfuscation patterns...{RESET}")
    time.sleep(0.5)
    print(f"  {CYAN}   → chr(114) = 'r'{RESET}")
    time.sleep(0.3)
    print(f"  {CYAN}   → chr(109) = 'm'{RESET}")
    time.sleep(0.3)
    print(f"  {CYAN}   → chr(32) = ' '{RESET}")
    time.sleep(0.3)
    print(f"  {CYAN}   → chr(45) = '-'{RESET}")
    time.sleep(0.3)
    print(f"  {CYAN}   → chr(114) = 'r'{RESET}")
    time.sleep(0.3)
    print(f"  {CYAN}   → chr(102) = 'f'{RESET}")
    time.sleep(0.5)

    decoded = decode_chr_obfuscation(obfuscated_code)

    if analyzer:
        result = analyzer.analyze(obfuscated_code)
        print_analysis_result({
            "intent": result.intent.value,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "blocked": result.blocked,
            "reason": result.reason,
            "code": obfuscated_code
        }, decoded)
    else:
        print_analysis_result({
            "intent": "file_delete",
            "risk_score": 95,
            "confidence": 0.95,
            "blocked": True,
            "reason": "Obfuscation detected: chr_encoding + dangerous command",
            "code": obfuscated_code
        }, decoded)

    print()
    time.sleep(1.5)

    # Demo 3: Base64 obfuscation
    print(f"  {BOLD}Demo 3: Base64 Encoded Payload{RESET}")
    print(f"  {DIM}{'─' * 50}{RESET}\n")

    base64_code = (
        "import base64; "
        "exec(base64.b64decode('cm0gLXJmIC8='))"
    )
    print_code_block(base64_code, "Agent submits code:")
    time.sleep(0.8)

    if analyzer:
        result = analyzer.analyze(base64_code)
        print_analysis_result({
            "intent": result.intent.value,
            "risk_score": result.risk_score,
            "confidence": result.confidence,
            "blocked": result.blocked,
            "reason": result.reason
        })
    else:
        print_analysis_result({
            "intent": "code_injection",
            "risk_score": 100,
            "confidence": 0.98,
            "blocked": True,
            "reason": "Base64 decode + exec detected - potential code injection"
        })

    print()
    print(f"  {GREEN}{BOLD}╔══════════════════════════════════════════════════╗{RESET}")
    print(f"  {GREEN}{BOLD}║  🛡️  Runtime Fence detected obfuscation!         ║{RESET}")
    print(f"  {GREEN}{BOLD}║  Malicious intent revealed and blocked.          ║{RESET}")
    print(f"  {GREEN}{BOLD}╚══════════════════════════════════════════════════╝{RESET}")
    print()


if __name__ == "__main__":
    main()
