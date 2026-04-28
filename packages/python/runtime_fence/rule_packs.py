"""
Preset Security Rule Packs for Runtime Fence.

Ready-made security profiles for common AI agent roles.
Select a preset to instantly configure appropriate safety rules
without writing custom YAML policies.

Usage:
    from runtime_fence import RuntimeFence, FenceConfig
    
    config = FenceConfig(preset="coding-assistant")
    fence = RuntimeFence(config)
"""

import logging
from typing import Dict, Optional
from .policy_loader import (
    FencePolicy, SpendingPolicy, TimePolicy
)

logger = logging.getLogger(__name__)


def _coding_assistant() -> FencePolicy:
    """
    Preset for coding assistants (Copilot, Cursor, Aider, etc.)
    
    Allows: file read/write, API calls, code execution in sandbox
    Blocks: system commands, network scanning, credential access
    """
    return FencePolicy(
        version="1.0",
        default_risk_threshold=60,
        blocked_actions=[
            "system_command", "network_scan", "credential_dump",
            "mass_data_export", "process_kill", "registry_edit",
        ],
        blocked_targets=[
            "/etc/shadow", "/etc/passwd", "~/.ssh/*",
            "*.pem", "*.key", "*.p12", "*.pfx",
            ".env", ".env.*",
            "~/.aws/*", "~/.config/gcloud/*",
        ],
        spending=SpendingPolicy(
            max_per_action=10.0,
            max_daily=100.0,
            max_weekly=500.0,
        ),
        time_controls=TimePolicy(
            cooldown_seconds=0.5,
        ),
        enable_behavioral=True,
        enable_intent_analysis=False,
        enable_sliding_window=True,
        enable_prompt_guard=True,
        prompt_rules_enabled=True,
    )


def _data_analyst() -> FencePolicy:
    """
    Preset for data analysis agents.
    
    Allows: file reads, API calls, write to output directories
    Blocks: system commands, writes outside output dirs, credential access
    """
    return FencePolicy(
        version="1.0",
        default_risk_threshold=55,
        blocked_actions=[
            "system_command", "code_execution", "network_scan",
            "credential_dump", "file_delete", "process_kill",
            "registry_edit", "mass_data_export",
        ],
        blocked_targets=[
            "/etc/*", "~/.ssh/*", "~/.aws/*",
            "*.exe", "*.sh", "*.bat", "*.cmd",
            "*.pem", "*.key", ".env",
            "C:\\Windows\\*",
        ],
        spending=SpendingPolicy(
            max_per_action=50.0,
            max_daily=500.0,
            max_weekly=2500.0,
        ),
        time_controls=TimePolicy(
            active_hours=[6, 22],
            cooldown_seconds=0.2,
        ),
        enable_behavioral=True,
        enable_intent_analysis=False,
        enable_sliding_window=True,
        enable_prompt_guard=True,
        prompt_rules_enabled=True,
    )


def _trading_bot() -> FencePolicy:
    """
    Preset for financial trading agents.
    
    Allows: API calls (exchanges), read market data
    Blocks: file system access, system commands, non-trading actions
    """
    return FencePolicy(
        version="1.0",
        default_risk_threshold=50,
        blocked_actions=[
            "file_delete", "system_command", "code_execution",
            "network_scan", "credential_dump", "mass_data_export",
            "process_kill", "registry_edit",
        ],
        blocked_targets=[
            "/etc/*", "~/.ssh/*", "~/.aws/*",
            "*.exe", "*.sh", "*.bat",
            "*.pem", "*.key", ".env",
        ],
        spending=SpendingPolicy(
            max_per_action=1000.0,
            max_daily=10000.0,
            max_weekly=50000.0,
            currency="USD",
        ),
        time_controls=TimePolicy(
            active_hours=[0, 24],  # 24/7 for markets
            active_days=["mon", "tue", "wed", "thu", "fri", "sat", "sun"],
            cooldown_seconds=0.1,
        ),
        enable_behavioral=True,
        enable_intent_analysis=True,
        enable_sliding_window=True,
        enable_prompt_guard=True,
        prompt_rules_enabled=True,
    )


def _devops_agent() -> FencePolicy:
    """
    Preset for DevOps/infrastructure agents.
    
    Allows: system commands (restricted), file operations, API calls
    Blocks: destructive commands, credential exfiltration
    Higher threshold since DevOps legitimately needs system access.
    """
    return FencePolicy(
        version="1.0",
        default_risk_threshold=75,
        blocked_actions=[
            "mass_data_export", "credential_dump", "network_scan",
        ],
        blocked_targets=[
            "~/.ssh/id_*", "~/.ssh/authorized_keys",
            "*.p12", "*.pfx",
            "/etc/shadow",
        ],
        spending=SpendingPolicy(
            max_per_action=100.0,
            max_daily=1000.0,
            max_weekly=5000.0,
        ),
        time_controls=TimePolicy(
            active_hours=[6, 23],
            active_days=["mon", "tue", "wed", "thu", "fri"],
            timezone="UTC",
            cooldown_seconds=1.0,
        ),
        enable_behavioral=True,
        enable_intent_analysis=False,
        enable_sliding_window=True,
        enable_prompt_guard=True,
        prompt_rules_enabled=True,
    )


def _research_agent() -> FencePolicy:
    """
    Preset for research/browsing agents.
    
    Allows: web browsing, API calls, file reads
    Blocks: file writes, system commands, code execution
    """
    return FencePolicy(
        version="1.0",
        default_risk_threshold=55,
        blocked_actions=[
            "write_file", "file_delete", "system_command",
            "code_execution", "network_scan", "credential_dump",
            "mass_data_export", "process_kill",
        ],
        blocked_targets=[
            "/etc/*", "~/.ssh/*", "~/.aws/*",
            "*.exe", "*.sh", "*.bat", "*.cmd",
            "*.pem", "*.key", ".env",
        ],
        spending=SpendingPolicy(
            max_per_action=5.0,
            max_daily=50.0,
            max_weekly=250.0,
        ),
        time_controls=TimePolicy(
            cooldown_seconds=1.0,
        ),
        enable_behavioral=True,
        enable_intent_analysis=False,
        enable_sliding_window=True,
        enable_prompt_guard=True,
        prompt_rules_enabled=True,
    )


def _customer_support() -> FencePolicy:
    """
    Preset for customer support/chat agents.
    
    Allows: API calls (CRM, ticketing), read knowledge base
    Blocks: file operations, system commands, code execution
    Strictest preset — minimal permissions.
    """
    return FencePolicy(
        version="1.0",
        default_risk_threshold=45,
        blocked_actions=[
            "read_file", "write_file", "file_delete",
            "system_command", "code_execution", "network_scan",
            "credential_dump", "mass_data_export", "process_kill",
            "network_access",
        ],
        blocked_targets=[
            "/etc/*", "~/*", "C:\\*",
            "*.exe", "*.sh", "*.bat",
        ],
        spending=SpendingPolicy(
            max_per_action=1.0,
            max_daily=10.0,
            max_weekly=50.0,
        ),
        time_controls=TimePolicy(
            active_hours=[7, 23],
            active_days=["mon", "tue", "wed", "thu", "fri", "sat"],
            cooldown_seconds=2.0,
        ),
        enable_behavioral=True,
        enable_intent_analysis=False,
        enable_sliding_window=True,
        enable_prompt_guard=True,
        prompt_rules_enabled=True,
    )


# Registry of all available presets
PRESETS: Dict[str, callable] = {
    "coding-assistant": _coding_assistant,
    "data-analyst": _data_analyst,
    "trading-bot": _trading_bot,
    "devops-agent": _devops_agent,
    "research-agent": _research_agent,
    "customer-support": _customer_support,
}


def get_preset(name: str) -> Optional[FencePolicy]:
    """
    Load a preset security profile by name.
    
    Available presets:
        - coding-assistant: For code editors and coding agents
        - data-analyst: For data analysis and reporting agents
        - trading-bot: For financial trading agents
        - devops-agent: For infrastructure and DevOps agents
        - research-agent: For web research and browsing agents
        - customer-support: For customer service chat agents
    
    Args:
        name: Preset name (case-insensitive, dashes or underscores)
        
    Returns:
        FencePolicy or None if preset not found
    """
    # Normalize name
    normalized = name.lower().strip().replace("_", "-")
    
    factory = PRESETS.get(normalized)
    if factory:
        logger.info(f"Loading security preset: {normalized}")
        return factory()
    
    available = ', '.join(PRESETS.keys())
    logger.warning(
        f"Unknown preset '{name}'. Available: {available}"
    )
    return None


def list_presets() -> Dict[str, str]:
    """List available presets with descriptions."""
    return {
        "coding-assistant": (
            "Code editors, Copilot, Cursor, Aider "
            "— blocks system commands, protects credentials"
        ),
        "data-analyst": (
            "Data pipelines, reporting "
            "— read-heavy, blocks writes outside output dirs"
        ),
        "trading-bot": (
            "Financial trading "
            "— strict spending limits, 24/7, intent analysis on"
        ),
        "devops-agent": (
            "Infrastructure automation "
            "— higher threshold, allows system commands"
        ),
        "research-agent": (
            "Web browsing, research "
            "— read-only, blocks file writes and code execution"
        ),
        "customer-support": (
            "Chat agents — minimal permissions, strictest preset"
        ),
    }
