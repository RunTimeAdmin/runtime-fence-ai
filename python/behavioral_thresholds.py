"""
Behavioral Thresholds - Rate Limiting and Exfiltration Detection

This module implements behavioral thresholds that detect:
- Data exfiltration (e.g., 10,000 file reads in 1 minute)
- Velocity attacks (rapid-fire transactions)
- Anomalous action patterns
- Auto-kill on threshold breach

Copyright (c) 2025 David Cooper
All rights reserved.
PATENT PENDING (Application #63/940,202)
"""

import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta
import threading

logger = logging.getLogger(__name__)


# =============================================================================
# THRESHOLD CONFIGURATION
# =============================================================================

class ThresholdAction(Enum):
    """Action to take when threshold is breached"""
    WARN = "warn"           # Log warning only
    BLOCK = "block"         # Block the action
    THROTTLE = "throttle"   # Rate limit (delay)
    KILL = "kill"           # Terminate the agent


@dataclass
class ThresholdConfig:
    """
    Configuration for a behavioral threshold.
    
    Attributes:
        name: Human-readable name for the threshold
        action_type: Type of action to monitor (e.g., "file_read")
        max_count: Maximum allowed actions in the window
        window_seconds: Time window for counting actions
        action_on_breach: What to do when threshold is exceeded
        cooldown_seconds: Time to wait before allowing actions again
        multiplier_for_kill: If count exceeds this multiple, force kill
    """
    name: str
    action_type: str
    max_count: int
    window_seconds: int
    action_on_breach: ThresholdAction = ThresholdAction.BLOCK
    cooldown_seconds: int = 60
    multiplier_for_kill: float = 2.0  # Auto-kill at 2x threshold


# Default thresholds based on security analysis
DEFAULT_THRESHOLDS = [
    # File operations
    ThresholdConfig(
        name="File Read Limit",
        action_type="file_read",
        max_count=100,
        window_seconds=60,
        action_on_breach=ThresholdAction.BLOCK,
        multiplier_for_kill=2.0
    ),
    ThresholdConfig(
        name="File Write Limit",
        action_type="file_write",
        max_count=50,
        window_seconds=60,
        action_on_breach=ThresholdAction.BLOCK,
        multiplier_for_kill=1.5
    ),
    ThresholdConfig(
        name="File Delete Limit",
        action_type="file_delete",
        max_count=10,
        window_seconds=60,
        action_on_breach=ThresholdAction.KILL,
        multiplier_for_kill=1.0  # Kill immediately at threshold
    ),
    
    # Network operations
    ThresholdConfig(
        name="Network Request Limit",
        action_type="network_request",
        max_count=50,
        window_seconds=60,
        action_on_breach=ThresholdAction.THROTTLE,
        multiplier_for_kill=3.0
    ),
    ThresholdConfig(
        name="External API Limit",
        action_type="external_api",
        max_count=30,
        window_seconds=60,
        action_on_breach=ThresholdAction.BLOCK,
        multiplier_for_kill=2.0
    ),
    ThresholdConfig(
        name="Data Upload Limit",
        action_type="data_upload",
        max_count=10,
        window_seconds=60,
        action_on_breach=ThresholdAction.KILL,
        multiplier_for_kill=1.0
    ),
    
    # Shell/System operations
    ThresholdConfig(
        name="Shell Exec Limit",
        action_type="shell_exec",
        max_count=10,
        window_seconds=300,  # 5 minutes
        action_on_breach=ThresholdAction.KILL,
        multiplier_for_kill=1.0
    ),
    ThresholdConfig(
        name="Process Spawn Limit",
        action_type="process_spawn",
        max_count=5,
        window_seconds=60,
        action_on_breach=ThresholdAction.BLOCK,
        multiplier_for_kill=1.5
    ),
    
    # Database operations
    ThresholdConfig(
        name="DB Query Limit",
        action_type="db_query",
        max_count=200,
        window_seconds=60,
        action_on_breach=ThresholdAction.THROTTLE,
        multiplier_for_kill=3.0
    ),
    ThresholdConfig(
        name="DB Write Limit",
        action_type="db_write",
        max_count=50,
        window_seconds=60,
        action_on_breach=ThresholdAction.BLOCK,
        multiplier_for_kill=2.0
    ),
    
    # Transaction operations (DeFi)
    ThresholdConfig(
        name="Transaction Limit",
        action_type="transaction",
        max_count=20,
        window_seconds=3600,  # 1 hour
        action_on_breach=ThresholdAction.BLOCK,
        multiplier_for_kill=2.0
    ),
    ThresholdConfig(
        name="High Value TX Limit",
        action_type="high_value_tx",
        max_count=5,
        window_seconds=3600,
        action_on_breach=ThresholdAction.KILL,
        multiplier_for_kill=1.0
    ),
]


# =============================================================================
# ACTION RECORD
# =============================================================================

@dataclass
class ActionRecord:
    """Record of a single action"""
    timestamp: float
    action_type: str
    target: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ThresholdBreach:
    """Details of a threshold breach"""
    agent_id: str
    threshold_name: str
    action_type: str
    count: int
    limit: int
    window_seconds: int
    breach_action: ThresholdAction
    should_kill: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "threshold_name": self.threshold_name,
            "action_type": self.action_type,
            "count": self.count,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "breach_action": self.breach_action.value,
            "should_kill": self.should_kill,
            "timestamp": self.timestamp.isoformat()
        }


# =============================================================================
# BEHAVIORAL THRESHOLD ENGINE
# =============================================================================

class BehavioralThresholds:
    """
    Behavioral threshold engine for detecting anomalous agent behavior.
    
    Tracks action counts per agent and action type, detecting when
    agents exceed configured thresholds. Supports:
    
    - Rate limiting per action type
    - Data exfiltration detection
    - Auto-kill on severe breaches
    - Custom threshold configurations
    - Cooldown periods after breaches
    
    Usage:
        thresholds = BehavioralThresholds()
        
        # Check before allowing action
        allowed, breach = thresholds.check_action(
            agent_id="agent-123",
            action_type="file_read",
            target="/etc/passwd"
        )
        
        if not allowed:
            print(f"Blocked: {breach.threshold_name}")
            if breach.should_kill:
                kill_agent(agent_id)
    """
    
    def __init__(
        self,
        thresholds: List[ThresholdConfig] = None,
        on_breach: Callable[[ThresholdBreach], None] = None,
        on_kill: Callable[[str, ThresholdBreach], None] = None
    ):
        """
        Initialize behavioral thresholds.
        
        Args:
            thresholds: Custom threshold configurations (uses defaults if None)
            on_breach: Callback when threshold is breached
            on_kill: Callback when agent should be killed
        """
        self.thresholds = {t.action_type: t for t in (thresholds or DEFAULT_THRESHOLDS)}
        self.on_breach = on_breach
        self.on_kill = on_kill
        
        # Action history per agent: agent_id -> action_type -> [timestamps]
        self._action_history: Dict[str, Dict[str, List[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Cooldown tracking: agent_id -> action_type -> cooldown_end_time
        self._cooldowns: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Breach history for auditing
        self._breach_history: List[ThresholdBreach] = []
        
        # Statistics
        self._stats = {
            "total_checks": 0,
            "total_allowed": 0,
            "total_blocked": 0,
            "total_kills": 0,
            "breaches_by_type": defaultdict(int)
        }
        
        # Thread lock for concurrent access
        self._lock = threading.RLock()
        
        logger.info(f"BehavioralThresholds initialized with {len(self.thresholds)} thresholds")
    
    def check_action(
        self,
        agent_id: str,
        action_type: str,
        target: str = "",
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, Optional[ThresholdBreach]]:
        """
        Check if an action is allowed under current thresholds.
        
        Args:
            agent_id: Unique identifier for the agent
            action_type: Type of action (e.g., "file_read", "network_request")
            target: Target of the action (e.g., file path, URL)
            metadata: Additional metadata about the action
            
        Returns:
            Tuple of (allowed, breach):
            - allowed: True if action is permitted
            - breach: ThresholdBreach details if blocked, None if allowed
        """
        with self._lock:
            self._stats["total_checks"] += 1
            now = time.time()
            
            # Check if in cooldown
            if self._is_in_cooldown(agent_id, action_type, now):
                breach = ThresholdBreach(
                    agent_id=agent_id,
                    threshold_name="Cooldown Active",
                    action_type=action_type,
                    count=0,
                    limit=0,
                    window_seconds=0,
                    breach_action=ThresholdAction.BLOCK,
                    should_kill=False
                )
                self._stats["total_blocked"] += 1
                return False, breach
            
            # Get threshold config
            threshold = self.thresholds.get(action_type)
            if not threshold:
                # No threshold for this action type - allow
                self._record_action(agent_id, action_type, target, now, metadata)
                self._stats["total_allowed"] += 1
                return True, None
            
            # Count recent actions
            count = self._count_recent_actions(
                agent_id,
                action_type,
                now,
                threshold.window_seconds
            )
            
            # Check if threshold exceeded
            if count >= threshold.max_count:
                breach = self._handle_breach(
                    agent_id, threshold, count, now
                )
                return False, breach
            
            # Action allowed - record it
            self._record_action(agent_id, action_type, target, now, metadata)
            self._stats["total_allowed"] += 1
            return True, None
    
    def _count_recent_actions(
        self,
        agent_id: str,
        action_type: str,
        now: float,
        window_seconds: int
    ) -> int:
        """Count actions within the time window"""
        cutoff = now - window_seconds
        
        history = self._action_history[agent_id][action_type]
        
        # Remove old entries
        self._action_history[agent_id][action_type] = [
            ts for ts in history if ts > cutoff
        ]
        
        return len(self._action_history[agent_id][action_type])
    
    def _record_action(
        self,
        agent_id: str,
        action_type: str,
        target: str,
        timestamp: float,
        metadata: Dict[str, Any] = None
    ):
        """Record an action for threshold tracking"""
        self._action_history[agent_id][action_type].append(timestamp)
    
    def _is_in_cooldown(
        self,
        agent_id: str,
        action_type: str,
        now: float
    ) -> bool:
        """Check if agent is in cooldown for this action type"""
        if agent_id not in self._cooldowns:
            return False
        
        cooldown_end = self._cooldowns[agent_id].get(action_type, 0)
        return now < cooldown_end
    
    def _handle_breach(
        self,
        agent_id: str,
        threshold: ThresholdConfig,
        count: int,
        now: float
    ) -> ThresholdBreach:
        """Handle a threshold breach"""
        # Determine if should kill (count exceeds multiplier)
        kill_threshold = threshold.max_count * threshold.multiplier_for_kill
        should_kill = count >= kill_threshold or threshold.action_on_breach == ThresholdAction.KILL
        
        breach = ThresholdBreach(
            agent_id=agent_id,
            threshold_name=threshold.name,
            action_type=threshold.action_type,
            count=count,
            limit=threshold.max_count,
            window_seconds=threshold.window_seconds,
            breach_action=threshold.action_on_breach,
            should_kill=should_kill
        )
        
        # Update statistics
        self._stats["total_blocked"] += 1
        self._stats["breaches_by_type"][threshold.action_type] += 1
        
        # Record breach
        self._breach_history.append(breach)
        
        # Set cooldown
        self._cooldowns[agent_id][threshold.action_type] = now + threshold.cooldown_seconds
        
        # Log breach
        if should_kill:
            logger.critical(
                f"🚨 KILL THRESHOLD EXCEEDED\n"
                f"   Agent: {agent_id}\n"
                f"   Action: {threshold.action_type}\n"
                f"   Count: {count}/{threshold.max_count}\n"
                f"   Kill threshold: {kill_threshold:.0f}"
            )
            self._stats["total_kills"] += 1
        else:
            logger.warning(
                f"⚠️  Threshold breached: {threshold.name}\n"
                f"   Agent: {agent_id}\n"
                f"   Count: {count}/{threshold.max_count}"
            )
        
        # Trigger callbacks
        if self.on_breach:
            self.on_breach(breach)
        
        if should_kill and self.on_kill:
            self.on_kill(agent_id, breach)
        
        return breach
    
    def get_agent_status(self, agent_id: str) -> Dict[str, Any]:
        """
        Get current status for an agent including action counts.
        
        Args:
            agent_id: Agent to get status for
            
        Returns:
            Dict with action counts and breach history
        """
        with self._lock:
            now = time.time()
            status = {
                "agent_id": agent_id,
                "action_counts": {},
                "cooldowns": {},
                "recent_breaches": [],
                "risk_level": "LOW"
            }
            
            # Count current actions per type
            for action_type, threshold in self.thresholds.items():
                count = self._count_recent_actions(
                    agent_id, action_type, now, threshold.window_seconds
                )
                percentage = (count / threshold.max_count) * 100 if threshold.max_count > 0 else 0
                
                status["action_counts"][action_type] = {
                    "count": count,
                    "limit": threshold.max_count,
                    "window_seconds": threshold.window_seconds,
                    "percentage": round(percentage, 1)
                }
            
            # Check cooldowns
            for action_type, end_time in self._cooldowns.get(agent_id, {}).items():
                if end_time > now:
                    status["cooldowns"][action_type] = {
                        "remaining_seconds": round(end_time - now, 1)
                    }
            
            # Recent breaches for this agent
            agent_breaches = [
                b.to_dict() for b in self._breach_history[-100:]
                if b.agent_id == agent_id
            ][-10:]  # Last 10 breaches
            status["recent_breaches"] = agent_breaches
            
            # Calculate risk level
            max_percentage = max(
                (ac["percentage"] for ac in status["action_counts"].values()),
                default=0
            )
            
            if len(agent_breaches) > 5:
                status["risk_level"] = "CRITICAL"
            elif len(agent_breaches) > 2 or max_percentage > 80:
                status["risk_level"] = "HIGH"
            elif len(agent_breaches) > 0 or max_percentage > 50:
                status["risk_level"] = "MEDIUM"
            
            return status
    
    def get_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        with self._lock:
            return {
                "total_checks": self._stats["total_checks"],
                "total_allowed": self._stats["total_allowed"],
                "total_blocked": self._stats["total_blocked"],
                "total_kills": self._stats["total_kills"],
                "block_rate": (
                    f"{(self._stats['total_blocked'] / self._stats['total_checks'] * 100):.1f}%"
                    if self._stats["total_checks"] > 0 else "0%"
                ),
                "breaches_by_type": dict(self._stats["breaches_by_type"]),
                "active_agents": len(self._action_history),
                "total_breaches": len(self._breach_history)
            }
    
    def reset_agent(self, agent_id: str):
        """Reset all history and cooldowns for an agent"""
        with self._lock:
            if agent_id in self._action_history:
                del self._action_history[agent_id]
            if agent_id in self._cooldowns:
                del self._cooldowns[agent_id]
            logger.info(f"Reset behavioral history for agent {agent_id}")
    
    def add_threshold(self, config: ThresholdConfig):
        """Add or update a threshold configuration"""
        with self._lock:
            self.thresholds[config.action_type] = config
            logger.info(f"Added threshold: {config.name} ({config.action_type})")
    
    def remove_threshold(self, action_type: str):
        """Remove a threshold configuration"""
        with self._lock:
            if action_type in self.thresholds:
                del self.thresholds[action_type]
                logger.info(f"Removed threshold for {action_type}")


# =============================================================================
# EXFILTRATION DETECTOR
# =============================================================================

class ExfiltrationDetector:
    """
    Specialized detector for data exfiltration patterns.
    
    Detects:
    - Mass file reads in short time
    - Large data transfers
    - Unusual network destinations
    - Database dump patterns
    """
    
    def __init__(self):
        self._data_volumes: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        self._unique_targets: Dict[str, set] = defaultdict(set)
        
        # Thresholds
        self.max_data_volume_mb = 100  # 100 MB in 5 minutes
        self.max_unique_files = 1000    # 1000 unique files in 5 minutes
        self.max_unique_ips = 20        # 20 unique external IPs
        self.window_seconds = 300       # 5 minute window
    
    def record_data_access(
        self,
        agent_id: str,
        target: str,
        bytes_accessed: int
    ) -> Tuple[bool, str]:
        """
        Record data access and check for exfiltration.
        
        Returns:
            Tuple of (is_exfiltration, reason)
        """
        now = time.time()
        cutoff = now - self.window_seconds
        
        # Record this access
        self._data_volumes[agent_id].append((now, bytes_accessed))
        self._unique_targets[agent_id].add(target)
        
        # Clean old entries
        self._data_volumes[agent_id] = [
            (ts, size) for ts, size in self._data_volumes[agent_id]
            if ts > cutoff
        ]
        
        # Check volume
        total_bytes = sum(size for _, size in self._data_volumes[agent_id])
        total_mb = total_bytes / (1024 * 1024)
        
        if total_mb > self.max_data_volume_mb:
            return True, f"Data volume exceeded: {total_mb:.1f}MB in {self.window_seconds}s"
        
        # Check unique targets (simplified - would track per window in production)
        if len(self._unique_targets[agent_id]) > self.max_unique_files:
            return True, f"Unique file access exceeded: {len(self._unique_targets[agent_id])} files"
        
        return False, ""
    
    def get_agent_data_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get data access statistics for an agent"""
        now = time.time()
        cutoff = now - self.window_seconds
        
        recent_accesses = [
            (ts, size) for ts, size in self._data_volumes.get(agent_id, [])
            if ts > cutoff
        ]
        
        total_bytes = sum(size for _, size in recent_accesses)
        
        return {
            "agent_id": agent_id,
            "access_count": len(recent_accesses),
            "total_bytes": total_bytes,
            "total_mb": round(total_bytes / (1024 * 1024), 2),
            "unique_targets": len(self._unique_targets.get(agent_id, set())),
            "window_seconds": self.window_seconds
        }


# =============================================================================
# INTEGRATED BEHAVIORAL FENCE
# =============================================================================

class BehavioralFence:
    """
    Complete behavioral fence integrating thresholds and exfiltration detection.
    
    Usage:
        fence = BehavioralFence(on_kill=my_kill_function)
        
        # Before every agent action:
        allowed, reason = fence.check(
            agent_id="agent-123",
            action_type="file_read",
            target="/etc/passwd",
            data_size=1024
        )
        
        if not allowed:
            raise SecurityError(reason)
    """
    
    def __init__(
        self,
        on_kill: Callable[[str, str], None] = None,
        custom_thresholds: List[ThresholdConfig] = None
    ):
        """
        Initialize behavioral fence.
        
        Args:
            on_kill: Callback(agent_id, reason) when agent should be killed
            custom_thresholds: Custom threshold configurations
        """
        self.thresholds = BehavioralThresholds(
            thresholds=custom_thresholds,
            on_kill=lambda aid, breach: self._handle_kill(aid, breach)
        )
        self.exfiltration = ExfiltrationDetector()
        self.on_kill = on_kill
        
        self._kill_count = 0
    
    def check(
        self,
        agent_id: str,
        action_type: str,
        target: str = "",
        data_size: int = 0,
        metadata: Dict[str, Any] = None
    ) -> Tuple[bool, str]:
        """
        Check if action is allowed.
        
        Args:
            agent_id: Agent identifier
            action_type: Type of action
            target: Target of action
            data_size: Bytes of data involved (for exfiltration detection)
            metadata: Additional metadata
            
        Returns:
            Tuple of (allowed, reason)
        """
        # Check rate thresholds
        allowed, breach = self.thresholds.check_action(
            agent_id, action_type, target, metadata
        )
        
        if not allowed:
            reason = f"Threshold breach: {breach.threshold_name}"
            if breach.should_kill:
                reason += " [KILL TRIGGERED]"
            return False, reason
        
        # Check exfiltration (for data-related actions)
        if action_type in ["file_read", "db_query", "network_request"] and data_size > 0:
            is_exfil, exfil_reason = self.exfiltration.record_data_access(
                agent_id, target, data_size
            )
            
            if is_exfil:
                logger.critical(f"🚨 EXFILTRATION DETECTED: {exfil_reason}")
                self._handle_kill(agent_id, None, exfil_reason)
                return False, f"Exfiltration detected: {exfil_reason}"
        
        return True, "Allowed"
    
    def _handle_kill(
        self,
        agent_id: str,
        breach: Optional[ThresholdBreach],
        reason: str = None
    ):
        """Handle kill trigger"""
        self._kill_count += 1
        
        kill_reason = reason or (
            f"Threshold {breach.threshold_name}: "
            f"{breach.count}/{breach.limit} in {breach.window_seconds}s"
            if breach else "Unknown"
        )
        
        logger.critical(f"🔪 KILL TRIGGERED for {agent_id}: {kill_reason}")
        
        if self.on_kill:
            self.on_kill(agent_id, kill_reason)
    
    def get_status(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive status for an agent"""
        threshold_status = self.thresholds.get_agent_status(agent_id)
        exfil_status = self.exfiltration.get_agent_data_stats(agent_id)
        
        return {
            "agent_id": agent_id,
            "thresholds": threshold_status,
            "exfiltration": exfil_status,
            "overall_risk": threshold_status["risk_level"]
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        stats = self.thresholds.get_stats()
        stats["kill_count"] = self._kill_count
        return stats


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import random
    
    logging.basicConfig(level=logging.INFO)
    
    def handle_kill(agent_id: str, reason: str):
        print(f"\n🔪 KILL CALLBACK: Agent {agent_id}")
        print(f"   Reason: {reason}\n")
    
    fence = BehavioralFence(on_kill=handle_kill)
    
    print("\n" + "=" * 60)
    print("BEHAVIORAL THRESHOLD TEST")
    print("=" * 60)
    
    agent = "test-agent-001"
    
    # Test 1: Normal file reads
    print("\n[Test 1] Normal file reads (50 reads)...")
    for i in range(50):
        allowed, reason = fence.check(
            agent_id=agent,
            action_type="file_read",
            target=f"/app/data/file_{i}.txt",
            data_size=1024
        )
    print(f"Status after 50 reads: {fence.get_status(agent)['thresholds']['action_counts'].get('file_read', {})}")
    
    # Test 2: Exceed threshold
    print("\n[Test 2] Exceeding file read threshold (60 more reads)...")
    for i in range(60):
        allowed, reason = fence.check(
            agent_id=agent,
            action_type="file_read",
            target=f"/app/data/file_{50+i}.txt",
            data_size=1024
        )
        if not allowed:
            print(f"   Blocked at read #{50+i+1}: {reason}")
            break
    
    # Test 3: Shell exec (should kill quickly)
    print("\n[Test 3] Shell exec attempts (kill threshold = 10)...")
    agent2 = "test-agent-002"
    for i in range(15):
        allowed, reason = fence.check(
            agent_id=agent2,
            action_type="shell_exec",
            target=f"ls -la"
        )
        if not allowed:
            print(f"   Blocked at attempt #{i+1}: {reason}")
    
    # Stats
    print("\n" + "=" * 60)
    print("FINAL STATISTICS")
    print("=" * 60)
    stats = fence.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
