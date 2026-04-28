"""
Runtime Fence - Local Agent Wrapper
Wraps any AI agent so all actions pass through the fence first.
"""

import os
import json
import time
import logging
import inspect
import threading
import requests
from typing import Any, Callable, Dict, Optional
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class _RateLimiter:
    """Simple token-bucket rate limiter for validate() calls."""
    def __init__(self, max_per_second: int = 100):
        self._max = max_per_second
        self._counts: dict = defaultdict(list)  # agent_id -> [timestamps]

    def allow(self, agent_id: str) -> bool:
        now = time.time()
        # Prune old entries
        self._counts[agent_id] = [
            t for t in self._counts[agent_id] if now - t < 1.0
        ]
        if len(self._counts[agent_id]) >= self._max:
            return False
        self._counts[agent_id].append(now)
        return True


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

# Policy-as-code integration
try:
    from .policy_loader import load_policy
    POLICY_AVAILABLE = True
except ImportError:
    try:
        from policy_loader import load_policy
        POLICY_AVAILABLE = True
    except ImportError:
        POLICY_AVAILABLE = False

# Time-bound access controls
try:
    from .time_controls import TimeEnforcer
    TIME_CONTROLS_AVAILABLE = True
except ImportError:
    try:
        from time_controls import TimeEnforcer
        TIME_CONTROLS_AVAILABLE = True
    except ImportError:
        TIME_CONTROLS_AVAILABLE = False

# Prompt injection detection
try:
    from .prompt_guard import PromptGuard
    PROMPT_GUARD_AVAILABLE = True
except ImportError:
    try:
        from prompt_guard import PromptGuard
        PROMPT_GUARD_AVAILABLE = True
    except ImportError:
        PROMPT_GUARD_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runtime_fence")


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class KillPropagationClient:
    """WebSocket client for receiving distributed kill signals."""

    def __init__(
        self,
        api_url: str,
        agent_id: str,
        on_kill_callback: Callable[[str], None]
    ):
        """
        Initialize the kill propagation client.

        Args:
            api_url: Base URL of the Runtime Fence API
            agent_id: Unique identifier for this agent instance
            on_kill_callback: Function called when kill signal received
        """
        self._ws_url = api_url.replace(
            'http://', 'ws://'
        ).replace('https://', 'wss://')
        self._agent_id = agent_id
        self._on_kill = on_kill_callback
        self._ws = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Start the WebSocket listener in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def _listen_loop(self) -> None:
        """Reconnecting WebSocket listener with exponential backoff."""
        try:
            import websocket  # websocket-client package
        except ImportError:
            logger.warning(
                "websocket-client not installed — kill propagation disabled. "
                "Install with: pip install websocket-client"
            )
            return

        reconnect_delay = 5  # Start with 5 seconds
        max_reconnect_delay = 60  # Cap at 60 seconds

        while self._running:
            try:
                self._ws = websocket.WebSocketApp(
                    self._ws_url,
                    on_open=self._on_open,
                    on_message=self._on_message,
                    on_error=self._on_error,
                    on_close=self._on_close,
                )
                self._ws.run_forever(ping_interval=30, ping_timeout=10)
            except Exception as e:
                logger.warning(f"WebSocket connection failed: {e}")

            if self._running:
                logger.info(f"Reconnecting in {reconnect_delay} seconds...")
                time.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)

    def _on_open(self, ws) -> None:
        """Register this agent instance with the server."""
        ws.send(json.dumps({
            'type': 'register',
            'agent_id': self._agent_id,
        }))
        logger.info(
            f"WebSocket: Registered agent {self._agent_id}"
        )

    def _on_message(self, ws, message: str) -> None:
        """Handle incoming WebSocket messages."""
        try:
            msg = json.loads(message)
            if msg.get('type') == 'kill':
                target = msg.get('agent_id')
                # Accept if global kill (target=None) or targeted at this agent
                if target is None or target == self._agent_id:
                    reason = msg.get('reason', 'Remote kill')
                    logger.critical(f"REMOTE KILL RECEIVED: {reason}")
                    self._on_kill(reason)
                    # Acknowledge receipt
                    ws.send(json.dumps({
                        'type': 'ack_kill',
                        'agent_id': self._agent_id,
                    }))
            elif msg.get('type') == 'registered':
                logger.info("WebSocket: Server confirmed registration")
        except json.JSONDecodeError:
            logger.warning(f"WebSocket: Received invalid JSON: {message}")
        except Exception as e:
            logger.warning(f"WebSocket: Error handling message: {e}")

    def _on_error(self, ws, error) -> None:
        """Handle WebSocket errors."""
        logger.debug(f"WebSocket error: {error}")

    def _on_close(self, ws, close_status_code: int, close_msg: str) -> None:
        """Handle WebSocket connection close."""
        logger.debug(f"WebSocket closed: {close_status_code} - {close_msg}")

    def stop(self) -> None:
        """Stop the WebSocket listener."""
        self._running = False
        if self._ws:
            self._ws.close()


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
    # Prompt injection detection
    enable_prompt_guard: bool = True
    # SPIFFE/SPIRE identity configuration
    spiffe_enabled: bool = False
    spiffe_workload_api: str = ""
    spiffe_trust_domain: str = "runtime-fence.local"
    # Policy-as-code YAML path
    policy_path: str = ""
    # Time-bound access controls (direct config, no YAML needed)
    active_hours: list = None  # [start_hour, end_hour]
    active_days: list = None   # ["mon", "tue", ...]
    timezone: str = "UTC"
    cooldown_seconds: float = 0.0


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

        # Initialize prompt injection detection
        self._prompt_guard = None
        if PROMPT_GUARD_AVAILABLE:
            should_enable = self.config.enable_prompt_guard
            custom_patterns = []

            if self._policy:
                should_enable = (
                    should_enable
                    and self._policy.prompt_rules_enabled
                )
                custom_patterns = (
                    self._policy.custom_prompt_patterns or []
                )

            if should_enable:
                self._prompt_guard = PromptGuard(
                    custom_patterns=custom_patterns
                )
                logger.info(
                    f"Prompt injection guard enabled "
                    f"({len(custom_patterns)} custom patterns)"
                )

        # Initialize SPIFFE identity manager if enabled
        self._spiffe = None
        if self.config.spiffe_enabled:
            try:
                from .spiffe import SpiffeIdentityManager, SpiffeConfig
                spiffe_config = SpiffeConfig(
                    enabled=True,
                    workload_api_addr=self.config.spiffe_workload_api,
                    trust_domain=self.config.spiffe_trust_domain,
                )
                self._spiffe = SpiffeIdentityManager(spiffe_config)
                logger.info("SPIFFE identity manager loaded")
            except Exception as e:
                logger.warning(f"SPIFFE integration unavailable: {e}")
                self._spiffe = None

        # Pre-load sentence-transformers model asynchronously
        if self.config.enable_sliding_window or self.config.enable_behavioral:
            try:
                from .task_adherence import (
                    _get_sentence_model, SENTENCE_TRANSFORMERS_AVAILABLE
                )
                if SENTENCE_TRANSFORMERS_AVAILABLE:
                    import threading
                    threading.Thread(
                        target=_get_sentence_model,
                        daemon=True,
                        name="sentence-model-preload"
                    ).start()
                    logger.debug(
                        "Sentence-transformers model preloading in background"
                    )
            except ImportError:
                pass

        # Load YAML policy if available
        self._policy = None
        if POLICY_AVAILABLE:
            self._policy = load_policy(
                self.config.policy_path or None
            )
            # Apply policy to config where applicable
            if self._policy:
                p = self._policy
                if p.blocked_actions and not self.config.blocked_actions:
                    self.config.blocked_actions = p.blocked_actions
                # Module toggles from policy
                if hasattr(self.config, 'enable_behavioral'):
                    self.config.enable_behavioral = p.enable_behavioral
                if hasattr(self.config, 'enable_intent_analysis'):
                    self.config.enable_intent_analysis = (
                        p.enable_intent_analysis
                    )
                if hasattr(self.config, 'enable_sliding_window'):
                    self.config.enable_sliding_window = (
                        p.enable_sliding_window
                    )

        # Time-bound access controls
        self._time_enforcer = None
        self._agent_time_enforcers: dict = {}  # agent_id -> TimeEnforcer

        if TIME_CONTROLS_AVAILABLE and self._policy:
            # Global time controls from YAML policy
            if self._policy.time_controls:
                self._time_enforcer = TimeEnforcer.from_policy(
                    self._policy.time_controls
                )
                if self._time_enforcer:
                    logger.info("Global time controls enabled")

            # Per-agent time controls from YAML policy
            for agent_id, agent_policy in self._policy.agents.items():
                if agent_policy.time_controls:
                    enforcer = TimeEnforcer.from_policy(
                        agent_policy.time_controls
                    )
                    if enforcer:
                        self._agent_time_enforcers[agent_id] = enforcer
                        logger.info(
                            f"Time controls enabled for"
                            f" agent: {agent_id}"
                        )

        # Fallback: direct FenceConfig time controls (no YAML)
        if TIME_CONTROLS_AVAILABLE and not self._time_enforcer:
            if (
                self.config.active_hours
                or self.config.active_days
                or self.config.cooldown_seconds > 0
            ):
                self._time_enforcer = TimeEnforcer(
                    active_hours=self.config.active_hours,
                    active_days=self.config.active_days,
                    tz=self.config.timezone,
                    cooldown_seconds=self.config.cooldown_seconds,
                )
                logger.info(
                    "Time controls enabled from FenceConfig"
                )

        # Initialize rate limiter
        self._rate_limiter = _RateLimiter(max_per_second=100)

        # Start kill propagation listener for distributed kills
        self._kill_propagation: Optional[KillPropagationClient] = None
        if self.config.api_url and not self.config.offline_mode:
            try:
                self._kill_propagation = KillPropagationClient(
                    api_url=self.config.api_url,
                    agent_id=self.config.agent_id,
                    on_kill_callback=self._remote_kill_received,
                )
                self._kill_propagation.start()
            except Exception as e:
                logger.warning(f"Failed to start kill propagation: {e}")

    def _remote_kill_received(self, reason: str) -> None:
        """Handle kill signal received from remote server."""
        logger.critical(f"REMOTE KILL APPLIED: {reason}")
        self.killed = True

    def validate(
        self,
        action: str,
        target: str,
        amount: float = 0.0,
        context: Dict = None,
        metadata: Dict = None
    ) -> ActionResult:
        """
        Validate an action before allowing it through the fence.
        Returns ActionResult with allowed=True/False.
        """
        # Rate limiting check
        agent_id = (metadata or {}).get("agent_id", self.config.agent_id)
        if not self._rate_limiter.allow(agent_id):
            logger.warning(f"Rate limit exceeded for agent {agent_id}")
            return ActionResult(
                allowed=False,
                action=action,
                target=target,
                risk_score=100,
                risk_level=RiskLevel.CRITICAL,
                reasons=["Rate limit exceeded"],
                timestamp=time.time()
            )

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

        # Time-bound access check
        agent_id_tc = (metadata or {}).get(
            "agent_id", self.config.agent_id
        )
        time_enforcer = self._agent_time_enforcers.get(
            agent_id_tc, self._time_enforcer
        )
        if time_enforcer:
            allowed_time, reason = time_enforcer.check_allowed(
                agent_id_tc
            )
            if not allowed_time:
                logger.warning(f"Time control blocked: {reason}")
                return ActionResult(
                    allowed=False,
                    action=action,
                    target=target,
                    risk_score=100,
                    risk_level=RiskLevel.CRITICAL,
                    reasons=[
                        f"Time restriction: {reason}"
                    ],
                    timestamp=time.time()
                )

        # Initialize risk score before prompt scan
        reasons = []
        risk_score = 0

        # Prompt injection scan
        if self._prompt_guard:
            scan_text = f"{action} {target}"
            if metadata and isinstance(metadata, dict):
                if "code" in metadata:
                    scan_text += f" {metadata['code']}"
                if "prompt" in metadata:
                    scan_text += f" {metadata['prompt']}"
                if "input" in metadata:
                    scan_text += f" {metadata['input']}"

            prompt_threats = self._prompt_guard.scan(scan_text)
            if prompt_threats:
                max_threat = prompt_threats[0]
                if max_threat.risk_score >= 80:
                    return ActionResult(
                        allowed=False,
                        action=action,
                        target=target,
                        risk_score=max_threat.risk_score,
                        risk_level=(
                            RiskLevel.CRITICAL
                            if max_threat.risk_score >= 90
                            else RiskLevel.HIGH
                        ),
                        reasons=[
                            f"Prompt injection detected: "
                            f"{max_threat.category}/"
                            f"{max_threat.pattern_name}"
                        ],
                        timestamp=time.time(),
                    )
                else:
                    # Below block threshold but elevate risk
                    risk_score = max(
                        risk_score, max_threat.risk_score
                    )

        # Local checks (fast)

        # Check blocked actions
        if action in self.config.blocked_actions:
            reasons.append(f"Action '{action}' is blocked")
            risk_score += 50

        # Check blocked targets
        if any(blocked in target for blocked in self.config.blocked_targets):
            reasons.append(f"Target '{target}' is blocked")
            risk_score += 50

        # Check policy-based target blocking
        if self._policy:
            import re
            agent_id_meta = (metadata or {}).get("agent_id", "default")
            agent_policy = self._policy.agents.get(agent_id_meta)

            # Check global blocked targets
            for pattern in self._policy.blocked_targets:
                if re.search(pattern, target):
                    reasons.append(f"Target blocked by policy: {pattern}")
            risk_score += 50

            # Check agent-specific overrides
            if agent_policy:
                # Allowed actions whitelist
                if (
                    agent_policy.allowed_actions
                    and action not in agent_policy.allowed_actions
                ):
                    reasons.append(
                        f"Action not in allowlist for "
                        f"agent {agent_id_meta}"
                    )
                    risk_score += 90

                # Agent blocked actions
                if (
                    agent_policy.blocked_actions
                    and action in agent_policy.blocked_actions
                ):
                    reasons.append(
                        f"Action blocked for agent "
                        f"{agent_id_meta} by policy"
                    )
                    risk_score += 50

                # Agent blocked targets
                if agent_policy.blocked_targets:
                    for pattern in agent_policy.blocked_targets:
                        if re.search(pattern, target):
                            reasons.append(
                                f"Target blocked for agent "
                                f"{agent_id_meta}: {pattern}"
                            )
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
