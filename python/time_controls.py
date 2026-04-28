"""
Time-Bound Access Controls for Runtime Fence.

Enforces scheduling restrictions on agent actions:
- Active hours (e.g., 9am-5pm only)
- Active days (e.g., weekdays only)
- Timezone-aware evaluation
- Per-action cooldown enforcement
"""

import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Optional timezone support
try:
    from zoneinfo import ZoneInfo
    ZONEINFO_AVAILABLE = True
except ImportError:
    try:
        from backports.zoneinfo import ZoneInfo
        ZONEINFO_AVAILABLE = True
    except ImportError:
        ZONEINFO_AVAILABLE = False


DAY_MAP = {
    "mon": 0, "monday": 0,
    "tue": 1, "tuesday": 1,
    "wed": 2, "wednesday": 2,
    "thu": 3, "thursday": 3,
    "fri": 4, "friday": 4,
    "sat": 5, "saturday": 5,
    "sun": 6, "sunday": 6,
}


class TimeEnforcer:
    """Enforces time-based access controls on agent actions."""

    def __init__(self,
                 active_hours: Optional[List[int]] = None,
                 active_days: Optional[List[str]] = None,
                 tz: str = "UTC",
                 cooldown_seconds: float = 0.0):
        """
        Args:
            active_hours: [start, end] in 24h format,
                e.g. [9, 17] = 9am-5pm
            active_days: List of day names,
                e.g. ["mon", "tue", "wed", "thu", "fri"]
            tz: Timezone string,
                e.g. "America/New_York", "UTC"
            cooldown_seconds: Minimum seconds between
                actions per agent
        """
        self._active_hours = active_hours  # [start_hour, end_hour]
        self._active_days = None
        self._timezone_str = tz
        self._cooldown = cooldown_seconds
        self._last_action: Dict[str, float] = {}  # agent_id -> timestamp

        # Parse active days
        if active_days:
            self._active_days = set()
            for day in active_days:
                day_lower = day.lower().strip()
                if day_lower in DAY_MAP:
                    self._active_days.add(DAY_MAP[day_lower])
                else:
                    logger.warning(f"Unknown day: {day}")

        # Resolve timezone
        self._tz = None
        if ZONEINFO_AVAILABLE and tz and tz != "UTC":
            try:
                self._tz = ZoneInfo(tz)
            except Exception as e:
                logger.warning(
                    f"Unknown timezone '{tz}',"
                    f" falling back to UTC: {e}"
                )

    def _get_current_time(self) -> datetime:
        """Get current time in configured timezone."""
        now = datetime.now(timezone.utc)
        if self._tz:
            now = now.astimezone(self._tz)
        return now

    def check_allowed(self, agent_id: str = "default") -> Tuple[bool, str]:
        """
        Check if an action is allowed at the current time.

        Returns:
            (allowed, reason) tuple
        """
        now = self._get_current_time()

        # Check active hours
        if self._active_hours and len(self._active_hours) >= 2:
            start_hour, end_hour = self._active_hours[0], self._active_hours[1]
            current_hour = now.hour

            if start_hour <= end_hour:
                # Normal range: e.g., 9-17
                if not (start_hour <= current_hour < end_hour):
                    return False, (
                        f"Outside active hours "
                        f"({start_hour}:00-{end_hour}:00 "
                        f"{self._timezone_str}), "
                        f"current: {current_hour}:00"
                    )
            else:
                # Overnight range: e.g., 22-6
                if end_hour <= current_hour < start_hour:
                    return False, (
                        f"Outside active hours "
                        f"({start_hour}:00-{end_hour}:00 "
                        f"{self._timezone_str}), "
                        f"current: {current_hour}:00"
                    )

        # Check active days
        if self._active_days is not None:
            current_day = now.weekday()  # 0=Monday
            if current_day not in self._active_days:
                day_name = now.strftime("%A")
                return False, (
                    f"Not an active day ({day_name}), "
                    f"allowed: {self._format_days()}"
                )

        # Check cooldown
        if self._cooldown > 0:
            last = self._last_action.get(agent_id, 0)
            elapsed = time.time() - last
            if elapsed < self._cooldown:
                remaining = round(self._cooldown - elapsed, 2)
                return False, (
                    f"Cooldown active — {remaining}s remaining "
                    f"(min {self._cooldown}s between actions)"
                )

        # Update last action time
        if self._cooldown > 0:
            self._last_action[agent_id] = time.time()

        return True, ""

    def _format_days(self) -> str:
        """Format active days for display."""
        if not self._active_days:
            return "all"
        day_names = {
            0: "Mon", 1: "Tue", 2: "Wed",
            3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun",
        }
        return ", ".join(
            day_names.get(d, "?") for d in sorted(self._active_days)
        )

    @classmethod
    def from_policy(cls, time_policy) -> Optional['TimeEnforcer']:
        """Create TimeEnforcer from a TimePolicy dataclass."""
        if time_policy is None:
            return None
        return cls(
            active_hours=time_policy.active_hours,
            active_days=time_policy.active_days,
            tz=time_policy.timezone,
            cooldown_seconds=time_policy.cooldown_seconds,
        )
