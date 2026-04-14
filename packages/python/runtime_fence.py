"""
Runtime Fence - Local Agent Wrapper
Wraps any AI agent so all actions pass through the fence first.
"""

import os
import json
import time
import logging
import requests
from typing import Any, Callable, Dict, Optional
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runtime_fence")


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FenceConfig:
    """Configuration for the Runtime Fence wrapper."""
    agent_id: str
    api_url: str = "http://localhost:3001"
    api_key: Optional[str] = None
    spending_limit: float = 1000.0
    blocked_actions: list = field(default_factory=list)
    blocked_targets: list = field(default_factory=list)
    risk_threshold: RiskLevel = RiskLevel.HIGH
    auto_kill_on_critical: bool = True
    log_all_actions: bool = True
    offline_mode: bool = False  # Skip API calls, local validation only


@dataclass
class ActionResult:
    """Result of an action attempt."""
    allowed: bool
    action: str
    target: str
    risk_score: int
    risk_level: RiskLevel
    reasons: list
    timestamp: float


class RuntimeFence:
    """
    The fence that wraps around your AI agent.
    All actions must pass through here before reaching the outside world.
    """

    def __init__(self, config: FenceConfig):
        self.config = config
        self.killed = False
        self.action_log: list[ActionResult] = []
        self.total_spent = 0.0
        logger.info(f"Runtime Fence initialized for agent: {config.agent_id}")

    def validate(self, action: str, target: str, amount: float = 0.0, context: Dict = None) -> ActionResult:
        """
        Validate an action before allowing it through the fence.
        Returns ActionResult with allowed=True/False.
        """
        if self.killed:
            return ActionResult(
                allowed=False,
                action=action,
                target=target,
                risk_score=100,
                risk_level=RiskLevel.CRITICAL,
                reasons=["Agent has been killed - all actions blocked"],
                timestamp=time.time()
            )

        # Local checks first (fast)
        reasons = []
        risk_score = 0

        # Check blocked actions
        if action in self.config.blocked_actions:
            reasons.append(f"Action '{action}' is blocked")
            risk_score += 50

        # Check blocked targets
        if any(blocked in target for blocked in self.config.blocked_targets):
            reasons.append(f"Target '{target}' is blocked")
            risk_score += 50

        # Check spending limit
        if amount > 0:
            if self.total_spent + amount > self.config.spending_limit:
                reasons.append(f"Would exceed spending limit (${self.config.spending_limit})")
                risk_score += 40

        # Call remote API for deeper analysis (unless offline mode)
        if not self.config.offline_mode:
            try:
                api_result = self._call_api(action, target, amount, context)
                risk_score = max(risk_score, api_result.get("riskScore", 0))
                reasons.extend(api_result.get("reasons", []))
            except Exception as e:
                logger.warning(f"API validation failed, using local only: {e}")

        # Determine risk level
        if risk_score >= 90:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 70:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Decide if allowed
        allowed = risk_score < self._risk_threshold_value()

        # Auto-kill on critical
        if risk_level == RiskLevel.CRITICAL and self.config.auto_kill_on_critical:
            self.kill("Critical risk action attempted")
            allowed = False

        result = ActionResult(
            allowed=allowed,
            action=action,
            target=target,
            risk_score=risk_score,
            risk_level=risk_level,
            reasons=reasons,
            timestamp=time.time()
        )

        # Log action
        if self.config.log_all_actions:
            self.action_log.append(result)
            logger.info(f"[{'ALLOWED' if allowed else 'BLOCKED'}] {action} -> {target} (risk: {risk_score})")

        # Update spending if allowed
        if allowed and amount > 0:
            self.total_spent += amount

        return result

    def _risk_threshold_value(self) -> int:
        """Convert risk threshold to numeric value."""
        return {
            RiskLevel.LOW: 25,
            RiskLevel.MEDIUM: 50,
            RiskLevel.HIGH: 75,
            RiskLevel.CRITICAL: 90
        }[self.config.risk_threshold]

    def _call_api(self, action: str, target: str, amount: float, context: Dict) -> Dict:
        """Call the Runtime Fence API for validation."""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        response = requests.post(
            f"{self.config.api_url}/api/runtime/assess",
            headers=headers,
            json={
                "agentId": self.config.agent_id,
                "action": action,
                "context": {"target": target, "amount": amount, **(context or {})}
            },
            timeout=5
        )
        return response.json()

    def kill(self, reason: str = "Manual kill"):
        """Immediately stop all agent actions."""
        self.killed = True
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
        
        # Notify API
        try:
            requests.post(
                f"{self.config.api_url}/api/runtime/kill",
                json={"agentId": self.config.agent_id, "reason": reason},
                timeout=5
            )
        except Exception:
            pass

    def reset(self):
        """Reset the kill switch (requires confirmation)."""
        self.killed = False
        self.total_spent = 0.0
        logger.info("Kill switch reset - agent can resume actions")

    def wrap_function(self, action_name: str, target: str = "unknown"):
        """
        Decorator to wrap any function through the fence.
        
        Usage:
            @fence.wrap_function("api_call", "external_service")
            def call_api(url, data):
                return requests.post(url, json=data)
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Extract amount if present
                amount = kwargs.get("amount", 0.0)
                
                # Validate through fence
                result = self.validate(action_name, target, amount)
                
                if not result.allowed:
                    raise PermissionError(
                        f"Action blocked by Runtime Fence: {', '.join(result.reasons)}"
                    )
                
                return func(*args, **kwargs)
            return wrapper
        return decorator

    def get_status(self) -> Dict:
        """Get current fence status."""
        return {
            "agent_id": self.config.agent_id,
            "killed": self.killed,
            "total_spent": self.total_spent,
            "spending_limit": self.config.spending_limit,
            "actions_logged": len(self.action_log),
            "blocked_count": sum(1 for a in self.action_log if not a.allowed)
        }


class FencedAgent:
    """
    Base class for creating fenced AI agents.
    Inherit from this to build agents that automatically go through the fence.
    """

    def __init__(self, fence: RuntimeFence):
        self.fence = fence

    def execute(self, action: str, target: str, amount: float = 0.0, **kwargs) -> Any:
        """Execute an action through the fence."""
        result = self.fence.validate(action, target, amount, kwargs)
        
        if not result.allowed:
            raise PermissionError(
                f"Blocked: {', '.join(result.reasons)}"
            )
        
        # Override this in subclass to do actual work
        return self._do_action(action, target, amount, **kwargs)

    def _do_action(self, action: str, target: str, amount: float, **kwargs) -> Any:
        """Override this method to implement actual agent actions."""
        raise NotImplementedError("Subclass must implement _do_action")


# Convenience function for quick setup
def create_fence(
    agent_id: str,
    api_url: str = "http://localhost:3001",
    spending_limit: float = 1000.0
) -> RuntimeFence:
    """Quick way to create a Runtime Fence."""
    config = FenceConfig(
        agent_id=agent_id,
        api_url=api_url,
        spending_limit=spending_limit
    )
    return RuntimeFence(config)
