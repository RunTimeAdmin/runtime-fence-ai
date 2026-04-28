"""
Policy-as-Code Configuration Engine for Runtime Fence.

Loads security policies from YAML files, enabling declarative
configuration of agent safety rules without code changes.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# PyYAML is optional
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class SpendingPolicy:
    """Spending limit configuration."""
    max_per_action: float = 0.0
    max_daily: float = 0.0
    max_weekly: float = 0.0
    currency: str = "USD"


@dataclass
class TimePolicy:
    """Time-bound access controls."""
    active_hours: Optional[List[int]] = None  # [9, 17] = 9am-5pm
    active_days: Optional[List[str]] = None   # ["mon","tue","wed","thu","fri"]
    timezone: str = "UTC"
    cooldown_seconds: float = 0.0  # Min seconds between actions


@dataclass
class AgentPolicy:
    """Per-agent policy overrides."""
    agent_id: str = ""
    allowed_actions: Optional[List[str]] = None
    blocked_actions: Optional[List[str]] = None
    allowed_targets: Optional[List[str]] = None
    blocked_targets: Optional[List[str]] = None
    max_risk_score: int = 100
    spending: Optional[SpendingPolicy] = None
    time_controls: Optional[TimePolicy] = None


@dataclass
class FencePolicy:
    """Complete security policy loaded from YAML."""
    version: str = "1.0"

    # Global defaults
    default_risk_threshold: int = 70
    blocked_actions: List[str] = field(default_factory=list)
    allowed_actions: Optional[List[str]] = None  # None = allow all not blocked
    blocked_targets: List[str] = field(default_factory=list)
    allowed_targets: Optional[List[str]] = None

    # Spending limits
    spending: Optional[SpendingPolicy] = None

    # Time controls
    time_controls: Optional[TimePolicy] = None

    # Per-agent overrides
    agents: Dict[str, AgentPolicy] = field(default_factory=dict)

    # Prompt injection rules
    prompt_rules_enabled: bool = True
    custom_prompt_patterns: List[str] = field(default_factory=list)

    # Module toggles
    enable_behavioral: bool = True
    enable_intent_analysis: bool = False
    enable_sliding_window: bool = True
    enable_prompt_guard: bool = True


def _parse_spending(data: dict) -> SpendingPolicy:
    """Parse spending policy from YAML dict."""
    return SpendingPolicy(
        max_per_action=float(data.get("max_per_action", 0)),
        max_daily=float(data.get("max_daily", 0)),
        max_weekly=float(data.get("max_weekly", 0)),
        currency=data.get("currency", "USD"),
    )


def _parse_time_policy(data: dict) -> TimePolicy:
    """Parse time-bound policy from YAML dict."""
    return TimePolicy(
        active_hours=data.get("active_hours"),
        active_days=data.get("active_days"),
        timezone=data.get("timezone", "UTC"),
        cooldown_seconds=float(data.get("cooldown_seconds", 0)),
    )


def _parse_agent_policy(agent_id: str, data: dict) -> AgentPolicy:
    """Parse per-agent policy overrides."""
    policy = AgentPolicy(agent_id=agent_id)
    policy.allowed_actions = data.get("allowed_actions")
    policy.blocked_actions = data.get("blocked_actions")
    policy.allowed_targets = data.get("allowed_targets")
    policy.blocked_targets = data.get("blocked_targets")
    policy.max_risk_score = int(data.get("max_risk_score", 100))

    if "spending" in data:
        policy.spending = _parse_spending(data["spending"])
    if "time_controls" in data:
        policy.time_controls = _parse_time_policy(data["time_controls"])

    return policy


def load_policy(path: str = None) -> FencePolicy:
    """
    Load security policy from YAML file.

    Search order:
    1. Explicit path argument
    2. FENCE_POLICY_PATH environment variable
    3. ./fence_policy.yaml
    4. ~/.runtime_fence/policy.yaml

    Returns default policy if no YAML found or PyYAML not installed.
    """
    if not YAML_AVAILABLE:
        logger.debug("PyYAML not installed — using default policy")
        return FencePolicy()

    # Search for policy file
    search_paths = []
    if path:
        search_paths.append(path)

    env_path = os.environ.get("FENCE_POLICY_PATH")
    if env_path:
        search_paths.append(env_path)

    search_paths.extend([
        os.path.join(os.getcwd(), "fence_policy.yaml"),
        os.path.join(os.getcwd(), "fence_policy.yml"),
        os.path.join(Path.home(), ".runtime_fence", "policy.yaml"),
    ])

    policy_path = None
    for p in search_paths:
        if os.path.isfile(p):
            policy_path = p
            break

    if not policy_path:
        logger.debug("No fence_policy.yaml found — using default policy")
        return FencePolicy()

    # Load and parse
    try:
        with open(policy_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        logger.info(f"Loaded security policy from {policy_path}")
        return _parse_policy(data)

    except Exception as e:
        logger.error(f"Failed to load policy from {policy_path}: {e}")
        return FencePolicy()


def _parse_policy(data: dict) -> FencePolicy:
    """Parse complete policy from YAML data."""
    policy = FencePolicy()

    policy.version = str(data.get("version", "1.0"))
    policy.default_risk_threshold = int(data.get("default_risk_threshold", 70))
    policy.blocked_actions = data.get("blocked_actions", [])
    policy.allowed_actions = data.get("allowed_actions")
    policy.blocked_targets = data.get("blocked_targets", [])
    policy.allowed_targets = data.get("allowed_targets")

    # Module toggles
    modules = data.get("modules", {})
    policy.enable_behavioral = modules.get("behavioral", True)
    policy.enable_intent_analysis = modules.get("intent_analysis", False)
    policy.enable_sliding_window = modules.get("sliding_window", True)
    policy.enable_prompt_guard = modules.get("prompt_guard", True)

    # Prompt rules
    prompt = data.get("prompt_guard", {})
    policy.prompt_rules_enabled = prompt.get("enabled", True)
    policy.custom_prompt_patterns = prompt.get("custom_patterns", [])

    # Spending
    if "spending" in data:
        policy.spending = _parse_spending(data["spending"])

    # Time controls
    if "time_controls" in data:
        policy.time_controls = _parse_time_policy(data["time_controls"])

    # Per-agent overrides
    agents_data = data.get("agents", {})
    for agent_id, agent_data in agents_data.items():
        policy.agents[agent_id] = _parse_agent_policy(agent_id, agent_data)

    return policy
