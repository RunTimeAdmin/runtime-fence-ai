"""
Runtime Fence CLI
Command-line interface with update support.
"""

import argparse
import sys
import subprocess
import json
import urllib.request
from importlib.metadata import version, PackageNotFoundError

__version__ = "1.0.0"
PYPI_URL = "https://pypi.org/pypi/runtime-fence/json"
GITHUB_RELEASES = "https://api.github.com/repos/Protocol14019/ai-agent-killswitch/releases/latest"


def get_installed_version() -> str:
    """Get currently installed version."""
    try:
        return version("runtime-fence")
    except PackageNotFoundError:
        return __version__


def get_latest_version() -> tuple:
    """
    Check PyPI for latest version.
    Returns (version, download_url) or (None, None) on error.
    """
    try:
        with urllib.request.urlopen(PYPI_URL, timeout=10) as response:
            data = json.loads(response.read().decode())
            latest = data["info"]["version"]
            return latest, None
    except Exception:
        pass
    
    # Fallback to GitHub releases
    try:
        req = urllib.request.Request(
            GITHUB_RELEASES,
            headers={"Accept": "application/vnd.github.v3+json"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            tag = data.get("tag_name", "").lstrip("v")
            return tag, data.get("html_url")
    except Exception:
        return None, None


def check_update() -> dict:
    """Check if an update is available."""
    current = get_installed_version()
    latest, url = get_latest_version()
    
    if not latest:
        return {
            "status": "error",
            "message": "Could not check for updates"
        }
    
    # Simple version comparison
    current_parts = [int(x) for x in current.split(".")]
    latest_parts = [int(x) for x in latest.split(".")]
    
    needs_update = latest_parts > current_parts
    
    return {
        "status": "update_available" if needs_update else "up_to_date",
        "current_version": current,
        "latest_version": latest,
        "needs_update": needs_update,
        "url": url
    }


def do_update(force: bool = False) -> bool:
    """
    Update runtime-fence via pip.
    Returns True on success.
    """
    print("Checking for updates...")
    result = check_update()
    
    if result["status"] == "error":
        print(f"Error: {result['message']}")
        return False
    
    if not result["needs_update"] and not force:
        print(f"Already up to date (v{result['current_version']})")
        return True
    
    print(f"Updating from v{result['current_version']} to v{result['latest_version']}...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--upgrade", "runtime-fence"
        ])
        print("Update successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Update failed: {e}")
        return False


def cmd_version(args):
    """Show version info."""
    current = get_installed_version()
    print(f"Runtime Fence v{current}")
    
    if args.check:
        result = check_update()
        if result["needs_update"]:
            print(f"Update available: v{result['latest_version']}")
            print("Run 'fence update' to upgrade")
        else:
            print("You have the latest version")


def cmd_update(args):
    """Update to latest version."""
    success = do_update(force=args.force)
    sys.exit(0 if success else 1)


def cmd_status(args):
    """Show fence status."""
    from runtime_fence import RuntimeFence, FenceConfig
    
    config = FenceConfig(agent_id="cli-check", offline_mode=True)
    fence = RuntimeFence(config)
    status = fence.get_status()
    
    print("Runtime Fence Status")
    print("=" * 40)
    for key, value in status.items():
        print(f"  {key}: {value}")


def cmd_start(args):
    """Start the fence tray app."""
    try:
        from fence_tray import main
        main()
    except ImportError:
        print("Tray app not available. Run: fence-tray")


def cmd_scan(args):
    """Scan for AI agents."""
    from agent_scanner import AgentScanner
    
    print("Scanning for AI agents...")
    scanner = AgentScanner()
    agents = scanner.scan_once()
    
    if not agents:
        print("No AI agents detected.")
    else:
        print(f"\nFound {len(agents)} agent(s):")
        for agent in agents:
            icon = "!" if agent.risk_level == "high" else "?"
            print(f"  [{icon}] {agent.name} (PID: {agent.pid}, Risk: {agent.risk_level})")


def cmd_test(args):
    """Run a quick test of the fence."""
    from runtime_fence import RuntimeFence, FenceConfig, RiskLevel
    
    print("Testing Runtime Fence...")
    print()
    
    config = FenceConfig(
        agent_id="test",
        offline_mode=True,
        blocked_actions=["delete", "exec"],
        blocked_targets=["production", ".env"],
        risk_threshold=RiskLevel.MEDIUM
    )
    fence = RuntimeFence(config)
    
    tests = [
        ("read", "file.txt", 0, True),
        ("delete", "data", 0, False),
        ("exec", "command", 0, False),
        ("write", "production", 0, False),
        ("read", ".env", 0, False),
    ]
    
    passed = 0
    for action, target, amount, expected in tests:
        result = fence.validate(action, target, amount)
        status = "PASS" if result.allowed == expected else "FAIL"
        if status == "PASS":
            passed += 1
        print(f"  [{status}] {action} -> {target}: {'allowed' if result.allowed else 'blocked'}")
    
    print()
    print(f"Tests: {passed}/{len(tests)} passed")
    sys.exit(0 if passed == len(tests) else 1)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="fence",
        description="Runtime Fence - AI Agent Safety Control"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"%(prog)s {get_installed_version()}"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # version command
    ver_parser = subparsers.add_parser("version", help="Show version info")
    ver_parser.add_argument("-c", "--check", action="store_true", help="Check for updates")
    ver_parser.set_defaults(func=cmd_version)
    
    # update command
    upd_parser = subparsers.add_parser("update", help="Update to latest version")
    upd_parser.add_argument("-f", "--force", action="store_true", help="Force reinstall")
    upd_parser.set_defaults(func=cmd_update)
    
    # status command
    stat_parser = subparsers.add_parser("status", help="Show fence status")
    stat_parser.set_defaults(func=cmd_status)
    
    # start command
    start_parser = subparsers.add_parser("start", help="Start the fence tray app")
    start_parser.set_defaults(func=cmd_start)
    
    # scan command
    scan_parser = subparsers.add_parser("scan", help="Scan for AI agents")
    scan_parser.set_defaults(func=cmd_scan)
    
    # test command
    test_parser = subparsers.add_parser("test", help="Run quick fence test")
    test_parser.set_defaults(func=cmd_test)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)


if __name__ == "__main__":
    main()
