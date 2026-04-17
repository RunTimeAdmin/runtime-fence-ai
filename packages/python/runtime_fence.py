"""
Runtime Fence - Local Agent Wrapper
Wraps any AI agent so all actions pass through the fence first.
"""

import os
import json
import time
import logging
import inspect
import requests
from typing import Any, Callable, Dict, Optional
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum

# Fail-mode integration
try:
    from .fail_mode import FailModeHandler, FailModeConfig, FailMode
    FAIL_MODE_AVAILABLE = True
except ImportError:
    try:
        from fail_mode import FailModeHandler, FailModeConfig, FailMode
        FAIL_MODE_AVAILABLE = True
    except ImportError:
        FAIL_MODE_AVAILABLE = False

# Behavioral thresholds integration
try:
    from .behavioral_thresholds import (
        BehavioralThresholds, ExfiltrationDetector
    )
    BEHAVIORAL_AVAILABLE = True
except ImportError:
    try:
        from behavioral_thresholds import (
            BehavioralThresholds, ExfiltrationDetector
        )
        BEHAVIORAL_AVAILABLE = True
    except ImportError:
        BEHAVIORAL_AVAILABLE = False

# Intent analyzer integration
try:
    from .intent_analyzer import IntentAnalyzer
    INTENT_AVAILABLE = True
except ImportError:
    try:
        from intent_analyzer import IntentAnalyzer
        INTENT_AVAILABLE = True
    except ImportError:
        INTENT_AVAILABLE = False

# Sliding window detector integration
try:
    from .sliding_window import SlidingWindowDetector
    SLIDING_WINDOW_AVAILABLE = True
except ImportError:
    try:
        from sliding_window import SlidingWindowDetector
        SLIDING_WINDOW_AVAILABLE = True
    except ImportError:
        SLIDING_WINDOW_AVAILABLE = False

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
    reset_token: str = ""  # Optional token required for reset() authorization
    fail_mode: str = "closed"  # "closed", "cached", or "open"
    # Security module toggles
    enable_behavioral: bool = True
    # Off by default (requires LLM API key)
    enable_intent_analysis: bool = False
    enable_sliding_window: bool = True


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
        
        # Initialize fail-mode handler if available
        if FAIL_MODE_AVAILABLE:
            mode_map = {
                "closed": FailMode.CLOSED,
                "cached": FailMode.CACHED,
                "open": FailMode.OPEN
            }
            fm_config = FailModeConfig(
                mode=mode_map.get(config.fail_mode.lower(), FailMode.CLOSED),
                cache_ttl_seconds=300,
            )
            self._fail_handler = FailModeHandler(fm_config)
        else:
            self._fail_handler = None

        # Initialize security modules
        self._behavioral = None
        self._exfiltration = None
        self._intent_analyzer = None
        self._sliding_window = None

        if self.config.enable_behavioral and BEHAVIORAL_AVAILABLE:
            try:
                self._behavioral = BehavioralThresholds()
                self._exfiltration = ExfiltrationDetector()
                logger.info("Behavioral thresholds module loaded")
            except Exception as e:
                logger.warning(f"Behavioral thresholds unavailable: {e}")

        if self.config.enable_intent_analysis and INTENT_AVAILABLE:
            try:
                # Local-only by default
                self._intent_analyzer = IntentAnalyzer(use_llm=False)
                logger.info("Intent analyzer module loaded")
            except Exception as e:
                logger.warning(f"Intent analyzer unavailable: {e}")

        if self.config.enable_sliding_window and SLIDING_WINDOW_AVAILABLE:
            try:
                self._sliding_window = SlidingWindowDetector(
                    agent_id=self.config.agent_id
                )
                logger.info("Sliding window detector loaded")
            except Exception as e:
                logger.warning(f"Sliding window unavailable: {e}")

    def validate(
        self,
        action: str,
        target: str,
        amount: float = 0.0,
        context: Dict = None
    ) -> ActionResult:
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
                api_risk_score = api_result.get("riskScore", 0)
                risk_score = max(risk_score, api_risk_score)
                reasons.extend(api_result.get("reasons", []))
                
                # Cache successful result for fail_mode
                if self._fail_handler:
                    self._fail_handler.cache_result(
                        action, target, 
                        risk_score < self._risk_threshold_value(),
                        api_risk_score
                    )
            except Exception as e:
                logger.warning(f"API validation failed: {e}")
                
                if self._fail_handler:
                    # Use fail_mode strategy
                    result = self._fail_handler.on_validation_failure(
                        action, target, e
                    )
                    allowed_result, reason, fm_risk = result
                    if not allowed_result:
                        log_msg = "FAIL-CLOSED: API unavailable, blocking"
                        logger.critical(log_msg)
                        risk_score = 100  # Block the action
                        reasons.append(reason)
                    else:
                        # CACHED or OPEN mode
                        if fm_risk > 0:
                            logger.warning("FAIL-CACHED: Using cached policy")
                            risk_score = max(risk_score, int(fm_risk))
                        else:
                            log_msg = (
                                "FAIL-OPEN: API unavailable, "
                                "allowing with local-only validation"
                            )
                            logger.warning(log_msg)
                else:
                    # No fail_mode available — original behavior
                    log_msg = "Using local-only validation (no fail_mode)"
                    logger.warning(log_msg)

        # --- Security module checks ---
        agent_id = self.config.agent_id

        # Behavioral thresholds check
        if self._behavioral:
            try:
                allowed_bt, breach = self._behavioral.check_action(
                    agent_id=agent_id,
                    action_type=action,
                    target=target
                )
                if not allowed_bt and breach:
                    log_msg = f"Behavioral threshold breach: {breach}"
                    logger.warning(log_msg)
                    risk_score = max(risk_score, 90)
                    reasons.append(f"Behavioral: {breach.threshold_name}")
            except Exception as e:
                logger.warning(f"Behavioral check failed: {e}")

        # Exfiltration detection
        if self._exfiltration:
            try:
                # Estimate bytes from context or use 0
                est_bytes = 0
                if context and isinstance(context, dict):
                    est_bytes = context.get("bytes_accessed", 0)
                is_exfil, exfil_reason = self._exfiltration.record_data_access(
                    agent_id=agent_id,
                    target=target,
                    bytes_accessed=est_bytes
                )
                if is_exfil:
                    logger.warning(f"Exfiltration detected: {exfil_reason}")
                    risk_score = max(risk_score, 95)
                    reasons.append(f"Exfiltration: {exfil_reason}")
                else:
                    # Check unique target count
                    stats = self._exfiltration.get_agent_data_stats(
                        agent_id
                    )
                    if stats.get('unique_targets', 0) > 50:
                        n = stats['unique_targets']
                        msg = f"Potential exfil: {n} unique targets"
                        logger.warning(msg)
                        risk_score = max(risk_score, 85)
                        reasons.append(msg)
            except Exception as e:
                logger.warning(f"Exfiltration check failed: {e}")

        # Intent analysis (if enabled and available)
        if self._intent_analyzer:
            try:
                code_snippet = ""
                if context and isinstance(context, dict):
                    code_snippet = context.get("code", "")
                if code_snippet:
                    intent_result = self._intent_analyzer.analyze(code_snippet)
                    risk_score = max(risk_score, intent_result.risk_score)
                    if intent_result.risk_score >= 70:
                        reasons.append(
                            f"Intent: {intent_result.intent.value} "
                            f"({intent_result.risk_score})"
                        )
            except Exception as e:
                logger.warning(f"Intent analysis failed: {e}")

        # Sliding window (low-and-slow detection)
        if self._sliding_window:
            try:
                # Record this action
                self._sliding_window.record_api_call(1)
                if amount > 0:
                    self._sliding_window.record_bytes_out(int(amount))

                # Check for threshold breaches
                breaches = self._sliding_window.check_thresholds()
                if breaches:
                    for b in breaches:
                        logger.warning(
                            f"Sliding window breach: {b.metric.value} "
                            f"= {b.current_value:.0f}"
                        )
                        risk_score = max(risk_score, 80)
                        reasons.append(f"Window breach: {b.metric.value}")
            except Exception as e:
                logger.warning(f"Sliding window check failed: {e}")

        # Determine risk level (clamp AFTER security module checks)
        risk_score = min(risk_score, 100)  # Clamp to valid range
        if risk_score >= 90:
            risk_level = RiskLevel.CRITICAL
        elif risk_score >= 70:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 40:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        # Decide if allowed - block HIGH and CRITICAL risk actions
        allowed = risk_level not in (RiskLevel.HIGH, RiskLevel.CRITICAL)
        if allowed and risk_score >= self._risk_threshold_value():
            allowed = False

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
            RiskLevel.HIGH: 70,  # was 75, fixing threshold gap
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

    def reset(self, reason: str = None, auth_token: str = None):
        """Reset kill switch - requires reason for audit trail.
        
        Args:
            reason: Required explanation for why the agent is being reset.
            auth_token: Optional authorization token. If reset_token was configured,
                       this must match to allow reset.
        """
        if not reason:
            raise RuntimeError("reset() requires a reason parameter for audit trail")
        
        # Check authorization token if configured
        if hasattr(self.config, 'reset_token') and self.config.reset_token:
            if auth_token != self.config.reset_token:
                logger.warning(f"Unauthorized reset attempt for agent - reason given: {reason}")
                raise PermissionError("Invalid or missing auth_token for reset")
        
        self.killed = False
        self.total_spent = 0.0
        logger.info(f"Kill switch reset - reason: {reason}")

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
                # Check kwargs first, then inspect positional args for 'amount'
                amount = kwargs.get("amount", 0.0)
                if amount == 0.0 and args:
                    try:
                        sig = inspect.signature(func)
                        params = list(sig.parameters.keys())
                        if 'amount' in params:
                            idx = params.index('amount')
                            if idx < len(args):
                                amount = float(args[idx])
                    except (ValueError, TypeError):
                        pass
                
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
