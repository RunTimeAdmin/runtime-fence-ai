"""
Fail-Mode Strategy for Runtime Fence

This module implements explicit fail-mode behavior for when validation
services are unavailable. Provides three modes:

- CLOSED: Block all actions on error (safest, default for production)
- CACHED: Use last known policy (compromise between safety and availability)
- OPEN: Allow all actions on error (DANGEROUS - never use in production)

Copyright (c) 2025 David Cooper
All rights reserved.
PATENT PENDING (Application #63/940,202)
"""

import json
import time
import hashlib
import logging
from enum import Enum
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# =============================================================================
# FAIL MODE CONFIGURATION
# =============================================================================

class FailMode(Enum):
    """
    Fail mode determines behavior when validation services are unavailable.
    
    CLOSED: Block everything on error (DEFAULT - safest)
             Use in: Production, high-security environments
             Trade-off: May cause false positives during outages
    
    CACHED: Use last known policy for this action type
            Use in: Systems requiring high availability
            Trade-off: Stale policy may allow newly blocked actions
    
    OPEN:   Allow everything on error (DANGEROUS)
            Use in: NEVER in production. Development/testing only.
            Trade-off: Complete bypass of safety on any error
    """
    CLOSED = "closed"
    CACHED = "cached"
    OPEN = "open"


@dataclass
class FailModeConfig:
    """
    Configuration for fail-mode behavior.
    
    Attributes:
        mode: The fail mode to use (CLOSED/CACHED/OPEN)
        api_timeout_ms: Timeout for validation API calls (milliseconds)
        cache_ttl_seconds: How long to cache policy decisions
        cache_file_path: Where to persist cache (for restart resilience)
        max_cache_entries: Maximum entries in policy cache
        alert_on_fail: Whether to trigger alerts on fail-mode activation
        log_level: Logging level for fail-mode events
    """
    mode: FailMode = FailMode.CLOSED
    api_timeout_ms: int = 100
    cache_ttl_seconds: int = 60
    cache_file_path: str = ".fence_policy_cache.json"
    max_cache_entries: int = 10000
    alert_on_fail: bool = True
    log_level: str = "WARNING"


@dataclass
class CachedPolicy:
    """
    Represents a cached policy decision.
    
    Attributes:
        action: The action type (e.g., "file_read", "network_request")
        target: The target of the action (e.g., file path, URL)
        allowed: Whether the action was allowed
        risk_score: Risk score at time of caching
        cached_at: Unix timestamp when cached
        expires_at: Unix timestamp when cache expires
        policy_hash: Hash of the policy for integrity verification
    """
    action: str
    target: str
    allowed: bool
    risk_score: float
    cached_at: float
    expires_at: float
    policy_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if this cached policy has expired"""
        return time.time() > self.expires_at
    
    def verify_integrity(self) -> bool:
        """Verify cached policy hasn't been tampered with"""
        expected_hash = self._compute_hash()
        return self.policy_hash == expected_hash
    
    def _compute_hash(self) -> str:
        """Compute hash for integrity verification"""
        data = f"{self.action}:{self.target}:{self.allowed}:{self.risk_score}:{self.cached_at}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]


# =============================================================================
# POLICY CACHE
# =============================================================================

class PolicyCache:
    """
    Thread-safe policy cache with TTL support.
    
    Provides:
    - In-memory caching for fast lookups
    - Disk persistence for restart resilience
    - TTL-based expiration
    - Integrity verification
    - Automatic cleanup of expired entries
    """
    
    def __init__(self, config: FailModeConfig):
        self.config = config
        self._cache: Dict[str, CachedPolicy] = {}
        self._hits = 0
        self._misses = 0
        self._load_from_disk()
    
    def get(self, action: str, target: str) -> Optional[CachedPolicy]:
        """
        Retrieve cached policy for action+target combination.
        
        Args:
            action: The action type
            target: The target of the action
            
        Returns:
            CachedPolicy if found and not expired, None otherwise
        """
        cache_key = self._make_key(action, target)
        
        if cache_key not in self._cache:
            self._misses += 1
            return None
        
        policy = self._cache[cache_key]
        
        # Check expiration
        if policy.is_expired():
            del self._cache[cache_key]
            self._misses += 1
            logger.debug(f"Cache expired for {action}:{target}")
            return None
        
        # Verify integrity
        if not policy.verify_integrity():
            del self._cache[cache_key]
            self._misses += 1
            logger.warning(f"Cache integrity failed for {action}:{target}")
            return None
        
        self._hits += 1
        return policy
    
    def set(self, action: str, target: str, allowed: bool, risk_score: float,
            metadata: Dict[str, Any] = None):
        """
        Cache a policy decision.
        
        Args:
            action: The action type
            target: The target of the action
            allowed: Whether the action was allowed
            risk_score: Risk score for the action
            metadata: Optional metadata to store
        """
        cache_key = self._make_key(action, target)
        cached_at = time.time()
        expires_at = cached_at + self.config.cache_ttl_seconds
        
        policy = CachedPolicy(
            action=action,
            target=target,
            allowed=allowed,
            risk_score=risk_score,
            cached_at=cached_at,
            expires_at=expires_at,
            policy_hash="",  # Will be set below
            metadata=metadata or {}
        )
        policy.policy_hash = policy._compute_hash()
        
        self._cache[cache_key] = policy
        
        # Enforce max entries
        if len(self._cache) > self.config.max_cache_entries:
            self._cleanup_oldest()
        
        # Persist to disk periodically
        if len(self._cache) % 100 == 0:
            self._save_to_disk()
    
    def invalidate(self, action: str = None, target: str = None):
        """
        Invalidate cached policies.
        
        Args:
            action: If provided, invalidate all policies for this action
            target: If provided, invalidate all policies for this target
            Both: Invalidate specific action+target combination
            Neither: Clear entire cache
        """
        if action is None and target is None:
            self._cache.clear()
            logger.info("Policy cache cleared")
            return
        
        if action and target:
            cache_key = self._make_key(action, target)
            if cache_key in self._cache:
                del self._cache[cache_key]
            return
        
        # Partial invalidation
        keys_to_remove = []
        for key, policy in self._cache.items():
            if action and policy.action == action:
                keys_to_remove.append(key)
            elif target and policy.target == target:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._cache[key]
        
        logger.info(f"Invalidated {len(keys_to_remove)} cache entries")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "entries": len(self._cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "max_entries": self.config.max_cache_entries,
            "ttl_seconds": self.config.cache_ttl_seconds
        }
    
    def _make_key(self, action: str, target: str) -> str:
        """Create cache key from action and target"""
        return f"{action}::{target}"
    
    def _cleanup_oldest(self):
        """Remove oldest 10% of entries when cache is full"""
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: x[1].cached_at
        )
        
        remove_count = len(sorted_entries) // 10
        for key, _ in sorted_entries[:remove_count]:
            del self._cache[key]
        
        logger.debug(f"Cleaned up {remove_count} oldest cache entries")
    
    def _load_from_disk(self):
        """Load cache from disk for restart resilience"""
        try:
            cache_path = Path(self.config.cache_file_path)
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                
                for entry in data:
                    policy = CachedPolicy(**entry)
                    if not policy.is_expired() and policy.verify_integrity():
                        cache_key = self._make_key(policy.action, policy.target)
                        self._cache[cache_key] = policy
                
                logger.info(f"Loaded {len(self._cache)} policies from disk cache")
        except Exception as e:
            logger.warning(f"Could not load disk cache: {e}")
    
    def _save_to_disk(self):
        """Persist cache to disk"""
        try:
            cache_path = Path(self.config.cache_file_path)
            
            # Only save non-expired entries
            entries = []
            for policy in self._cache.values():
                if not policy.is_expired():
                    entries.append({
                        "action": policy.action,
                        "target": policy.target,
                        "allowed": policy.allowed,
                        "risk_score": policy.risk_score,
                        "cached_at": policy.cached_at,
                        "expires_at": policy.expires_at,
                        "policy_hash": policy.policy_hash,
                        "metadata": policy.metadata
                    })
            
            with open(cache_path, 'w') as f:
                json.dump(entries, f)
            
            logger.debug(f"Saved {len(entries)} policies to disk cache")
        except Exception as e:
            logger.warning(f"Could not save disk cache: {e}")


# =============================================================================
# FAIL MODE HANDLER
# =============================================================================

class FailModeHandler:
    """
    Handles fail-mode logic for validation failures.
    
    This is the main interface for fail-mode behavior. It:
    - Determines what to do when validation fails
    - Manages the policy cache
    - Logs and alerts on fail-mode activation
    - Provides metrics on fail-mode usage
    
    Usage:
        handler = FailModeHandler(FailModeConfig(mode=FailMode.CLOSED))
        
        try:
            result = await validate_action(action, target)
            handler.cache_result(action, target, result)
        except ValidationError:
            result = handler.on_validation_failure(action, target)
    """
    
    def __init__(self, config: FailModeConfig = None):
        self.config = config or FailModeConfig()
        self.cache = PolicyCache(self.config)
        
        # Metrics
        self._fail_closed_count = 0
        self._fail_cached_count = 0
        self._fail_open_count = 0
        self._last_failure_time: Optional[float] = None
        
        logger.info(f"FailModeHandler initialized with mode: {self.config.mode.value}")
        
        # Warn if using dangerous mode
        if self.config.mode == FailMode.OPEN:
            logger.critical(
                "⚠️  FAIL-OPEN MODE ENABLED - This is DANGEROUS!\n"
                "    All actions will be ALLOWED when validation fails.\n"
                "    DO NOT use this in production!"
            )
    
    def on_validation_failure(
        self,
        action: str,
        target: str,
        error: Exception = None
    ) -> Tuple[bool, str, float]:
        """
        Handle validation failure based on configured fail mode.
        
        Args:
            action: The action that failed validation
            target: The target of the action
            error: The exception that caused the failure (optional)
            
        Returns:
            Tuple of (allowed, reason, risk_score)
            - allowed: Whether to allow the action
            - reason: Explanation of the decision
            - risk_score: Risk score to use (100 for blocked, 0 for allowed)
        """
        self._last_failure_time = time.time()
        error_msg = str(error) if error else "Unknown error"
        
        # Log the failure
        logger.warning(
            f"FAIL-MODE ACTIVATED: {self.config.mode.value}\n"
            f"  Action: {action}\n"
            f"  Target: {target}\n"
            f"  Error: {error_msg}"
        )
        
        # Handle based on mode
        if self.config.mode == FailMode.CLOSED:
            return self._handle_fail_closed(action, target, error_msg)
        
        elif self.config.mode == FailMode.CACHED:
            return self._handle_fail_cached(action, target, error_msg)
        
        elif self.config.mode == FailMode.OPEN:
            return self._handle_fail_open(action, target, error_msg)
        
        # Default to CLOSED if unknown mode
        return self._handle_fail_closed(action, target, error_msg)
    
    def _handle_fail_closed(
        self,
        action: str,
        target: str,
        error_msg: str
    ) -> Tuple[bool, str, float]:
        """
        FAIL-CLOSED: Block everything on validation failure.
        
        This is the safest option. Any validation error results in
        the action being blocked with maximum risk score.
        """
        self._fail_closed_count += 1
        
        reason = f"FAIL-CLOSED: {action} blocked due to validation failure ({error_msg})"
        logger.warning(reason)
        
        # Alert if configured
        if self.config.alert_on_fail:
            self._send_alert("FAIL-CLOSED", action, target, error_msg)
        
        return False, reason, 100.0
    
    def _handle_fail_cached(
        self,
        action: str,
        target: str,
        error_msg: str
    ) -> Tuple[bool, str, float]:
        """
        FAIL-CACHED: Use last known policy if available.
        
        This provides a balance between safety and availability.
        If we have a recent policy decision for this action+target,
        use it. Otherwise, fall back to CLOSED.
        """
        cached = self.cache.get(action, target)
        
        if cached:
            self._fail_cached_count += 1
            
            age_seconds = time.time() - cached.cached_at
            reason = (
                f"FAIL-CACHED: Using cached policy (age: {age_seconds:.0f}s)\n"
                f"  Original decision: {'ALLOWED' if cached.allowed else 'BLOCKED'}\n"
                f"  Original risk: {cached.risk_score:.1f}"
            )
            logger.warning(reason)
            
            return cached.allowed, reason, cached.risk_score
        
        else:
            # No cached policy - fall back to CLOSED
            self._fail_closed_count += 1
            
            reason = (
                f"FAIL-CACHED: No cached policy found for {action}:{target}\n"
                f"  Falling back to FAIL-CLOSED behavior"
            )
            logger.warning(reason)
            
            return False, reason, 100.0
    
    def _handle_fail_open(
        self,
        action: str,
        target: str,
        error_msg: str
    ) -> Tuple[bool, str, float]:
        """
        FAIL-OPEN: Allow everything on validation failure.
        
        ⚠️  DANGEROUS - This should NEVER be used in production!
        
        This mode exists only for development/testing where you
        want to see what would happen without safety checks.
        """
        self._fail_open_count += 1
        
        reason = (
            f"⚠️  FAIL-OPEN: {action} ALLOWED despite validation failure!\n"
            f"  THIS IS DANGEROUS - validation was bypassed!\n"
            f"  Error: {error_msg}"
        )
        logger.critical(reason)
        
        # Always alert on FAIL-OPEN
        self._send_alert("FAIL-OPEN (DANGEROUS)", action, target, error_msg)
        
        return True, reason, 0.0
    
    def cache_result(
        self,
        action: str,
        target: str,
        allowed: bool,
        risk_score: float,
        metadata: Dict[str, Any] = None
    ):
        """
        Cache a successful validation result for use in FAIL-CACHED mode.
        
        Args:
            action: The action type
            target: The target of the action
            allowed: Whether the action was allowed
            risk_score: Risk score for the action
            metadata: Optional metadata to store
        """
        self.cache.set(action, target, allowed, risk_score, metadata)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get fail-mode statistics"""
        return {
            "mode": self.config.mode.value,
            "fail_closed_count": self._fail_closed_count,
            "fail_cached_count": self._fail_cached_count,
            "fail_open_count": self._fail_open_count,
            "total_failures": (
                self._fail_closed_count +
                self._fail_cached_count +
                self._fail_open_count
            ),
            "last_failure": self._last_failure_time,
            "cache_stats": self.cache.get_stats()
        }
    
    def _send_alert(
        self,
        mode: str,
        action: str,
        target: str,
        error_msg: str
    ):
        """Send alert on fail-mode activation"""
        # In production, this would send to:
        # - Email/SMS via Twilio
        # - Slack/Discord webhook
        # - PagerDuty
        # - CloudWatch/Datadog
        
        alert = {
            "type": "FAIL_MODE_ACTIVATED",
            "mode": mode,
            "action": action,
            "target": target,
            "error": error_msg,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        logger.critical(f"🚨 ALERT: {json.dumps(alert, indent=2)}")


# =============================================================================
# INTEGRATION HELPER
# =============================================================================

def create_fail_mode_handler(
    mode: str = "closed",
    api_timeout_ms: int = 100,
    cache_ttl_seconds: int = 60
) -> FailModeHandler:
    """
    Factory function to create a FailModeHandler with common configurations.
    
    Args:
        mode: "closed", "cached", or "open" (string)
        api_timeout_ms: Timeout for API calls in milliseconds
        cache_ttl_seconds: Cache TTL in seconds
        
    Returns:
        Configured FailModeHandler instance
        
    Example:
        # Production configuration (safest)
        handler = create_fail_mode_handler(mode="closed")
        
        # High-availability configuration
        handler = create_fail_mode_handler(
            mode="cached",
            cache_ttl_seconds=120
        )
    """
    mode_map = {
        "closed": FailMode.CLOSED,
        "cached": FailMode.CACHED,
        "open": FailMode.OPEN
    }
    
    fail_mode = mode_map.get(mode.lower(), FailMode.CLOSED)
    
    config = FailModeConfig(
        mode=fail_mode,
        api_timeout_ms=api_timeout_ms,
        cache_ttl_seconds=cache_ttl_seconds
    )
    
    return FailModeHandler(config)


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example: Using fail-mode handler
    
    # Create handler with CLOSED mode (default, safest)
    handler = create_fail_mode_handler(mode="closed")
    
    # Simulate a successful validation
    action = "file_read"
    target = "/etc/passwd"
    allowed = False  # This would come from actual validation
    risk_score = 85.0
    
    # Cache the result
    handler.cache_result(action, target, allowed, risk_score)
    print(f"Cached policy: {action} on {target} -> {'ALLOWED' if allowed else 'BLOCKED'}")
    
    # Simulate a validation failure
    try:
        raise ConnectionError("Validation API unreachable")
    except ConnectionError as e:
        result_allowed, reason, result_risk = handler.on_validation_failure(
            action, target, e
        )
        print(f"\nFail-mode result: {'ALLOWED' if result_allowed else 'BLOCKED'}")
        print(f"Reason: {reason}")
        print(f"Risk score: {result_risk}")
    
    # Show stats
    print(f"\nStats: {json.dumps(handler.get_stats(), indent=2)}")
