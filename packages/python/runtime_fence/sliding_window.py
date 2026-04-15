"""
Sliding Window Detector - Low and Slow Attack Detection

This module detects "low and slow" exfiltration attacks that stay
under rate limits but accumulate significant data over time.

Example: 1 record every 30 seconds = 2,880 records/day = data breach

Uses cumulative sliding windows (1h, 6h, 24h) to catch these patterns.

Copyright (c) 2025 David Cooper - PATENT PENDING
"""

import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class WindowSize(Enum):
    HOUR_1 = 3600
    HOUR_6 = 21600
    HOUR_24 = 86400


class MetricType(Enum):
    BYTES_OUT = "bytes_out"
    BYTES_IN = "bytes_in"
    RECORDS_ACCESSED = "records_accessed"
    API_CALLS = "api_calls"
    FILES_READ = "files_read"
    CONNECTIONS = "connections"


@dataclass
class WindowThreshold:
    metric: MetricType
    window: WindowSize
    limit: float
    action: str = "alert"

    def key(self) -> str:
        return f"{self.metric.value}_{self.window.value}"


DEFAULT_THRESHOLDS = [
    WindowThreshold(MetricType.BYTES_OUT, WindowSize.HOUR_1, 10_000_000, "alert"),
    WindowThreshold(MetricType.BYTES_OUT, WindowSize.HOUR_24, 50_000_000, "kill"),
    WindowThreshold(MetricType.RECORDS_ACCESSED, WindowSize.HOUR_1, 1000, "alert"),
    WindowThreshold(MetricType.RECORDS_ACCESSED, WindowSize.HOUR_24, 10000, "kill"),
    WindowThreshold(MetricType.API_CALLS, WindowSize.HOUR_1, 500, "alert"),
    WindowThreshold(MetricType.FILES_READ, WindowSize.HOUR_24, 1000, "alert"),
    WindowThreshold(MetricType.CONNECTIONS, WindowSize.HOUR_1, 100, "alert"),
]


@dataclass
class WindowEvent:
    timestamp: float
    value: float


@dataclass
class ThresholdBreach:
    metric: MetricType
    window: WindowSize
    current_value: float
    limit: float
    action: str
    agent_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric": self.metric.value,
            "window_seconds": self.window.value,
            "current": self.current_value,
            "limit": self.limit,
            "action": self.action,
            "agent_id": self.agent_id,
            "timestamp": self.timestamp.isoformat()
        }


class SlidingWindow:
    """Single sliding window for one metric."""

    def __init__(self, window_size: WindowSize):
        self.window_size = window_size
        self.events: deque = deque()
        self._total: float = 0

    def add(self, value: float, timestamp: float = None):
        ts = timestamp or time.time()
        self.events.append(WindowEvent(ts, value))
        self._total += value
        self._prune(ts)

    def _prune(self, current_time: float):
        cutoff = current_time - self.window_size.value
        while self.events and self.events[0].timestamp < cutoff:
            old = self.events.popleft()
            self._total -= old.value

    def get_total(self, current_time: float = None) -> float:
        ts = current_time or time.time()
        self._prune(ts)
        return self._total

    def get_rate(self, current_time: float = None) -> float:
        total = self.get_total(current_time)
        return total / self.window_size.value if self.window_size.value > 0 else 0


class MetricTracker:
    """Track multiple windows for one metric type."""

    def __init__(self, metric: MetricType):
        self.metric = metric
        self.windows: Dict[WindowSize, SlidingWindow] = {
            WindowSize.HOUR_1: SlidingWindow(WindowSize.HOUR_1),
            WindowSize.HOUR_6: SlidingWindow(WindowSize.HOUR_6),
            WindowSize.HOUR_24: SlidingWindow(WindowSize.HOUR_24),
        }

    def record(self, value: float, timestamp: float = None):
        ts = timestamp or time.time()
        for window in self.windows.values():
            window.add(value, ts)

    def get_total(self, window_size: WindowSize, ts: float = None) -> float:
        return self.windows[window_size].get_total(ts)

    def get_all_totals(self, ts: float = None) -> Dict[str, float]:
        return {
            f"{self.metric.value}_{w.value}": self.windows[w].get_total(ts)
            for w in WindowSize
        }


class SlidingWindowDetector:
    """
    Detect low-and-slow attacks using cumulative sliding windows.

    Monitors multiple metrics across multiple time windows to catch
    attacks that stay under per-request limits but accumulate over time.

    Usage:
        detector = SlidingWindowDetector(
            agent_id="agent-123",
            on_breach=lambda b: kill_agent(b.agent_id)
        )

        # Record metrics
        detector.record(MetricType.BYTES_OUT, 1024)
        detector.record(MetricType.RECORDS_ACCESSED, 1)

        # Check thresholds
        breaches = detector.check_thresholds()
    """

    def __init__(
        self,
        agent_id: str,
        thresholds: List[WindowThreshold] = None,
        on_breach: Callable[[ThresholdBreach], None] = None
    ):
        self.agent_id = agent_id
        self.thresholds = thresholds or DEFAULT_THRESHOLDS
        self.on_breach = on_breach

        self.trackers: Dict[MetricType, MetricTracker] = {}
        for metric in MetricType:
            self.trackers[metric] = MetricTracker(metric)

        self.breaches: List[ThresholdBreach] = []
        self._breach_count = 0

        logger.info(f"SlidingWindowDetector initialized for {agent_id}")

    def record(self, metric: MetricType, value: float, ts: float = None):
        self.trackers[metric].record(value, ts)

    def record_bytes_out(self, bytes_count: int):
        self.record(MetricType.BYTES_OUT, bytes_count)

    def record_bytes_in(self, bytes_count: int):
        self.record(MetricType.BYTES_IN, bytes_count)

    def record_record_access(self, count: int = 1):
        self.record(MetricType.RECORDS_ACCESSED, count)

    def record_api_call(self, count: int = 1):
        self.record(MetricType.API_CALLS, count)

    def record_file_read(self, count: int = 1):
        self.record(MetricType.FILES_READ, count)

    def record_connection(self, count: int = 1):
        self.record(MetricType.CONNECTIONS, count)

    def check_thresholds(self, ts: float = None) -> List[ThresholdBreach]:
        current_time = ts or time.time()
        breaches = []

        for threshold in self.thresholds:
            tracker = self.trackers[threshold.metric]
            current = tracker.get_total(threshold.window, current_time)

            if current > threshold.limit:
                breach = ThresholdBreach(
                    metric=threshold.metric,
                    window=threshold.window,
                    current_value=current,
                    limit=threshold.limit,
                    action=threshold.action,
                    agent_id=self.agent_id
                )
                breaches.append(breach)
                self.breaches.append(breach)
                self._breach_count += 1

                logger.warning(
                    f"THRESHOLD BREACH: {threshold.metric.value} "
                    f"({current:.0f} > {threshold.limit:.0f}) "
                    f"over {threshold.window.value}s - action: {threshold.action}"
                )

                if self.on_breach:
                    self.on_breach(breach)

        return breaches

    def get_current_metrics(self, ts: float = None) -> Dict[str, float]:
        result = {}
        for tracker in self.trackers.values():
            result.update(tracker.get_all_totals(ts))
        return result

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "breach_count": self._breach_count,
            "current_metrics": self.get_current_metrics(),
            "thresholds": len(self.thresholds)
        }

    def should_kill(self) -> bool:
        breaches = self.check_thresholds()
        return any(b.action == "kill" for b in breaches)


class MultiAgentWindowMonitor:
    """Monitor sliding windows across multiple agents."""

    def __init__(self, on_kill: Callable[[str, ThresholdBreach], None] = None):
        self.detectors: Dict[str, SlidingWindowDetector] = {}
        self.on_kill = on_kill

    def register(self, agent_id: str, thresholds: List[WindowThreshold] = None) -> SlidingWindowDetector:
        detector = SlidingWindowDetector(
            agent_id=agent_id,
            thresholds=thresholds,
            on_breach=lambda b: self._handle_breach(agent_id, b)
        )
        self.detectors[agent_id] = detector
        return detector

    def unregister(self, agent_id: str):
        if agent_id in self.detectors:
            del self.detectors[agent_id]

    def record(self, agent_id: str, metric: MetricType, value: float):
        if agent_id in self.detectors:
            self.detectors[agent_id].record(metric, value)

    def check_all(self) -> Dict[str, List[ThresholdBreach]]:
        return {
            agent_id: detector.check_thresholds()
            for agent_id, detector in self.detectors.items()
        }

    def _handle_breach(self, agent_id: str, breach: ThresholdBreach):
        if breach.action == "kill" and self.on_kill:
            self.on_kill(agent_id, breach)

    def get_fleet_status(self) -> Dict[str, Any]:
        return {
            "total_agents": len(self.detectors),
            "agents": {
                aid: d.get_status() for aid, d in self.detectors.items()
            }
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("\n" + "=" * 60)
    print("SLIDING WINDOW DETECTOR TEST")
    print("=" * 60)

    def on_breach(breach: ThresholdBreach):
        print(f"  BREACH: {breach.metric.value} -> {breach.action}")

    detector = SlidingWindowDetector("agent-001", on_breach=on_breach)

    print("\n[Simulating Low-and-Slow Attack]")
    print("  Sending 100KB every 10 seconds for 2 minutes...")

    for i in range(12):
        detector.record_bytes_out(100_000)
        time.sleep(0.01)

    print("\n[Current Metrics]")
    for metric, value in detector.get_current_metrics().items():
        if value > 0:
            print(f"  {metric}: {value:,.0f}")

    print("\n[Checking Thresholds]")
    breaches = detector.check_thresholds()
    if breaches:
        for b in breaches:
            print(f"  {b.metric.value}: {b.current_value:,.0f} > {b.limit:,.0f}")
    else:
        print("  No breaches (yet)")

    print("\n" + "=" * 60)
    print("Low-and-slow detection: cumulative windows catch what rate limits miss")
    print("=" * 60)
